# HTTP JSON API + static hosting for the React GUI. Stdlib only.
import hashlib
import glob
import importlib
import io
import json
import mimetypes
import os
import pkgutil
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from . import (
  _compatible_servers, _download_mega, _download_pdrain,
  _is_mega_link, _safe_name,
)
from . import discovery
from . import plugins
from .resolve import candidates as _resolve_candidates, resolve as _resolve_urls
from .ext import gdrive, megaNZ, pdrain
from .ext.megaNZ import _mega_fid
from .plugins._base import HEADERS, http_stream, resolve_url

_DL_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
# Embedded player (Kotlin/JavaFX) cache: file penuh di-download dulu karena MP4
# provider non-faststart (moov di akhir) — player streaming (range) gak bisa start,
# tapi file lokal bisa. nama = sha1(server_url) -> dedupe + resume.
_PLAY_CACHE = os.path.join(os.path.expanduser("~"), ".indonime", "play")
# Active mega streams for browser playback: id → {path, stop, thread, file_size, ts}
_mega_streams = {}
_mega_stream_seq = [0]
_mega_stream_lock = threading.Lock()
# ui/ (React web Vite) DIHAPUS — desktop GUI sekarang pakai RN web build dari `app/`
# (react-native-web via expo export --platform web). ui/dist lama di-replace app/dist.
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "dist")

_jobs = {}  # job_id → status dict (frontend polls /api/jobs)
_jobs_lock = threading.Lock()
_job_seq = [0]


def _providers():
  return [m.name for m in pkgutil.iter_modules(plugins.__path__)
          if not m.name.startswith('_')]


def _load_plugin(name):
  return importlib.import_module(f"indonime.plugins.{name}")


def _same_host(url, base):
  # SSRF guard: client-supplied URLs may only point at the provider's own host.
  try:
    return bool(base) and urlparse(url).hostname == urlparse(base).hostname
  except ValueError:
    return False


class _JobBar:
  # Tiny agg shim: per-job byte totals feed the jobs dict (frontend polls).
  def __init__(self, jid):
    self.jid = jid

  def add_total(self, key, n):
    with _jobs_lock:
      _jobs[self.jid]["total"] = n

  def add_done(self, n):
    with _jobs_lock:
      _jobs[self.jid]["done"] += n


def _dl_worker(jid, server_url, title):
  out = io.StringIO()
  agg = _JobBar(jid)
  try:
    if _is_mega_link(server_url):
      dest, size, reason = _download_mega(server_url, _safe_name(title), _DL_DIR,
                                          out=out, agg=agg)
    elif 'gdrive' in server_url.lower():
      dest, size, reason = _download_pdrain(server_url, _safe_name(title), _DL_DIR,
                                            out=out, agg=agg, scraper=gdrive.scrape)
    else:
      dest, size, reason = _download_pdrain(server_url, _safe_name(title), _DL_DIR,
                                            out=out, agg=agg)
  except Exception as e:
    dest, size, reason = None, 0, str(e)
  with _jobs_lock:
    j = _jobs[jid]
    j["status"] = "failed" if reason else "done"
    if reason:
      j["error"] = reason
    else:
      j["dest"], j["size"] = dest, size


def _play_cache_worker(jid, server_url, label):
  # Embedded player (JavaFX) butuh file utuh — mirror _play routing, tapi simpan ke
  # cache play (~/.indonime/play) biar gak nyampah di Downloads. Kalau file cache
  # udah ada (sha1 url) langsung done tanpa download ulang.
  h = hashlib.sha1(server_url.encode()).hexdigest()[:16]
  out = io.StringIO()
  agg = _JobBar(jid)
  try:
    import glob
    existing = glob.glob(os.path.join(_PLAY_CACHE, h + ".*"))
    if existing:
      dest, size, reason = existing[0], os.path.getsize(existing[0]), None
    elif 'mega' in label.lower() or _is_mega_link(server_url):
      dest, size, reason = _download_mega(server_url, h, _PLAY_CACHE, out=out, agg=agg)
    elif 'gdrive' in label.lower() or 'xtwap' in server_url.lower() or 'gdplayer' in server_url.lower():
      dest, size, reason = _download_pdrain(server_url, h, _PLAY_CACHE,
                                            out=out, agg=agg, scraper=gdrive.scrape)
    else:
      dest, size, reason = _download_pdrain(server_url, h, _PLAY_CACHE, out=out, agg=agg)
  except Exception as e:
    dest, size, reason = None, 0, str(e)
  with _jobs_lock:
    j = _jobs[jid]
    j["status"] = "failed" if reason else "done"
    if reason:
      j["error"] = reason
    else:
      j["dest"], j["size"] = dest, size


class _Handler(BaseHTTPRequestHandler):
  def log_message(self, *a):
    pass

  def _json(self, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    try:
      self.send_response(code)
      self.send_header('Content-Type', 'application/json; charset=utf-8')
      self.send_header('Access-Control-Allow-Origin', '*')
      self.send_header('Content-Length', str(len(body)))
      self.end_headers()
      self.wfile.write(body)
    except OSError:
      pass  # client aborted connection (BrokenPipe/ConnectionAborted/Reset) — nothing to send to

  def _err(self, e):
    self._json(500, {'error': str(e)})

  def _body(self):
    n = int(self.headers.get('Content-Length', 0) or 0)
    return json.loads(self.rfile.read(n) or b'{}')

  def do_GET(self):
    p = urlparse(self.path)
    if p.path.startswith('/api/mega-stream/'):
      try:
        sid = int(p.path.split('/')[-1])
      except ValueError:
        return self._json(404, {'error': 'bad stream id'})
      return self._serve_mega_stream(sid)
    if p.path == '/api/stream':
      # Range proxy utk direct-URL resolver (pdrain/gdrive): pixeldrain dkk
      # nge-block fingerprint browser (403) → backend yang fetch (H1) terus
      # forward byte stream + Range ke browser. SSRF-safe via _base allowlist.
      url = (parse_qs(p.query).get('url') or [''])[0]
      if not url:
        return self._json(400, {'error': 'url required'})
      return self._proxy_stream(url)
    if p.path.startswith('/api/'):
      return self._api(p.path, parse_qs(p.query))
    self._static(p.path)

  def do_POST(self):
    p = urlparse(self.path)
    if p.path == '/api/play':
      return self._play(self._body())
    if p.path == '/api/play-cache':
      return self._play_cache(self._body())
    if p.path == '/api/download':
      return self._download(self._body())
    if p.path == '/api/resolve':
      return self._api_resolve(self._body())
    self._json(404, {'error': 'not found'})

  def do_OPTIONS(self):
    self.send_response(204)
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    self.end_headers()

  def _api(self, path, qs):
    def q(k, d=''):
      return (qs.get(k) or [d])[0]
    try:
      provider = q('provider', 'otakudesu')
      if provider not in _providers() or not re.fullmatch(r'[A-Za-z0-9_]+', provider):
        return self._json(400, {'error': 'unknown provider'})
      if path in ('/api/info', '/api/episodes', '/api/downloads'):
        if not _same_host(q('url'), getattr(_load_plugin(provider), 'BASE', '')):
          return self._json(400, {'error': 'URL di luar domain provider'})
      if path == '/api/discover':
        return self._discover(q)
      if path == '/api/info':
        return self._json(200, {'info': _load_plugin(provider).info(q('url'))})
      if path == '/api/episodes':
        return self._json(200, {'episodes': _load_plugin(provider).episodes(q('url'))})
      if path == '/api/downloads':
        dl = _load_plugin(provider).downloads(q('url'))
        options = [{'label': name, 'url': url} for name, url in _compatible_servers(dl)]
        return self._json(200, {'options': options})
      if path == '/api/jobs':
        with _jobs_lock:
          return self._json(200, {'jobs': sorted(_jobs.values(), key=lambda j: j['id'])})
      return self._json(404, {'error': 'not found'})
    except Exception as e:
      return self._err(e)

  @staticmethod
  def _pool():
    # Urutan fallback resolve: otakudesu dulu, anoboy cadangan.
    return [(n, _load_plugin(n)) for n in ('otakudesu', 'anoboy')]

  def _discover(self, q):
    # List layer (AniList) — item shape {id anilist-*, title, image, ...}.
    tab = q('tab', 'top')
    if tab == 'top':
      return self._json(200, {'items': discovery.top(24)})
    if tab == 'season':
      return self._json(200, {'items': discovery.seasonal(24)})
    if tab == 'genre':
      return self._json(200, {'items': discovery.by_genre(q('genre', 'Action'), 24)})
    if tab == 'search':
      return self._json(200, {'results': discovery.search(q('q', ''), 8)})
    if tab == 'latest':
      # Rail "Rilis Terbaru": scrape home; fallback provider kalau kosong.
      items = _load_plugin('otakudesu').latest()
      if not items:
        items = _load_plugin('anoboy').latest()
      return self._json(200, {'items': items})
    if tab == 'alpha':
      sort_map = {
        'alpha': 'TITLE_ROMAJI',
        'alpha_desc': 'TITLE_ROMAJI_DESC',
        'latest': 'START_DATE_DESC',
        'rating': 'SCORE_DESC',
        'popular': 'POPULARITY_DESC',
      }
      sort = sort_map.get(q('sort', 'popular'), 'POPULARITY_DESC')
      page = int(q('page', '1'))
      return self._json(200, {'items': discovery.browse(sort, 50, page)})
    if tab == 'genres':
      return self._json(200, {'genres': discovery.GENRES})
    return self._json(400, {'error': f'unknown tab: {tab}'})

  def _api_resolve(self, body):
    # {id, title} → {sources: {provider: url}, candidates: [...]}. candidates
    # cuma di-fetch kalau sources kosong (UI butuh list manual) — hemat req.
    title = (body.get('title') or '').strip()
    if not title:
      return self._json(400, {'error': 'title required'})
    sources = _resolve_urls(self._pool(), title)
    candidates = [] if sources else _resolve_candidates(self._pool(), title)
    return self._json(200, {'id': body.get('id'), 'sources': sources,
                            'candidates': candidates})

  def _play(self, body):
    try:
      url = body.get('server_url', '')
      label = body.get('label', '').lower()
      # Route by label (server name) + URL — mirrors TUI routing logic.
      if 'mega' in label or 'mega' in url.lower():
        return self._play_mega_stream(url)
      if 'gdrive' in label or 'xtwap' in url.lower() or 'gdplayer' in url.lower():
        target = gdrive.scrape(url)
        if target:
          return self._json(200, {'stream': '/api/stream?url=' + quote(target, safe='')})
      else:
        target = pdrain.scrape(url)
        if target:
          return self._json(200, {'stream': '/api/stream?url=' + quote(target, safe='')})
      # Last resort: try mega (intermediary may redirect there)
      return self._play_mega_stream(url)
    except Exception as e:
      return self._err(e)

  def _play_mega_stream(self, url):
    """Resolve mega URL → proxy stream for browser playback."""
    try:
      curr = resolve_url(url, timeout=15)
      if not (('mega.nz' in curr or 'mega.co.nz' in curr) and '#' in curr):
        return self._json(500, {'error': 'Redirect tidak mengarah ke Mega.'})
    except Exception as e:
      return self._json(500, {'error': f'Network Error: {e}'})
    try:
      mega_url, f_id = _mega_fid(curr)
      if f_id is None:
        return self._json(500, {'error': 'Gagal extract file ID MEGA.'})
      stream = megaNZ.resolve_mega_file_stream(mega_url, f_id)
      if stream is None:
        return self._json(500, {'error': 'Gagal resolve stream Mega.'})
      path, ready, stop, dl_thread, bytes_counter, file_size = stream
    except Exception as e:
      return self._json(500, {'error': f'Gagal Streaming: {e}'})
    # Wait until enough data is on disk for browser to start playing.
    t0 = time.time()
    while not ready.is_set():
      try:
        if os.path.getsize(path) >= 1024 * 1024:  # 1MB minimum
          break
      except OSError:
        pass
      if time.time() - t0 > 75:
        stop.set()
        return self._json(500, {'error': 'Timeout buffering Mega stream.'})
      time.sleep(0.3)
    with _mega_stream_lock:
      _mega_stream_seq[0] += 1
      sid = _mega_stream_seq[0]
      _mega_streams[sid] = {
        'path': path, 'stop': stop, 'thread': dl_thread,
        'file_size': file_size, 'ts': time.time(),
        'bytes_counter': bytes_counter,
      }
    return self._json(200, {'stream': f'/api/mega-stream/{sid}'})

  def _proxy_stream(self, url):
    # Range proxy: byte-exact forward dari upstream (sudah lolos SSRF allowlist
    # via _open di _base.http_stream). Status + Content-Type/Range di-forward;
    # kalau upstream 206 pasokan Range, browser bisa seek seperti sumber asli.
    # Forward client Range → upstream biar 206 + seek kerja (bukan full 200).
    range_header = self.headers.get('Range')
    # CDN stream-vid (gdplayer) gate requests without Referer — add it.
    proxy_headers = {'Range': range_header} if range_header else None
    if 'gdplayer' in url:
      proxy_headers = {**HEADERS, **(proxy_headers or {}),
                       'Referer': 'https://gdplayer.to/',
                       'Origin': 'https://gdplayer.to'}
    try:
      up = http_stream(url, timeout=45, headers=proxy_headers)
    except Exception as e:
      return self._json(502, {'error': f'Stream upstream error: {e}'})
    try:
      self.send_response(up.status)
      self.send_header('Content-Type', up.headers.get('Content-Type') or 'application/octet-stream')
      self.send_header('Accept-Ranges', 'bytes')
      self.send_header('Access-Control-Allow-Origin', '*')
      crange = up.headers.get('Content-Range')
      if crange:
        self.send_header('Content-Range', crange)
      elif up.headers.get('Content-Length'):
        self.send_header('Content-Length', up.headers['Content-Length'])
      self.end_headers()
      while True:
        chunk = up.read(256 * 1024)
        if not chunk:
          break
        self.wfile.write(chunk)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
      pass  # client aborted — nothing to send to
    finally:
      up.close()

  def _serve_mega_stream(self, sid):
    """Serve the decrypted mega temp file to the browser."""
    with _mega_stream_lock:
      info = _mega_streams.get(sid)
    if info is None:
      print(f"[mega:serve] sid={sid} not found (expired)", file=sys.stderr)
      return self._json(404, {'error': 'Stream expired.'})
    path, stop, dl_thread, file_size, _ = (
      info['path'], info['stop'], info['thread'], info['file_size'], info['ts'])
    done = not dl_thread.is_alive()
    # Downloader mati duluan + file belum penuh = terpotong. Serve file potong
    # → browser "file is corrupt" pas play nembus batas data. Tolak bersih:
    # user retry (MEGA sering -3/-8 transient), bukan corrupt.
    try:
      truncated = done and os.path.getsize(path) < file_size
    except OSError:
      truncated = True
    if truncated:
      return self._json(502, {'error': 'Download Mega terputus — coba lagi.'})
    range_header = self.headers.get('Range')
    if range_header and range_header.startswith('bytes='):
      parts = range_header[6:].split('-')
      start = int(parts[0]) if parts[0] else 0
      end = int(parts[1]) + 1 if parts[1] else file_size
    else:
      start = 0
      end = file_size
    # Wait for data at the requested offset — stall-based, generous. A 416
    # while the file is still growing kills Chromium's media pipeline (gray
    # video, no error) and makes mpv seek-fail → corrupt packets. Only 416
    # when the offset is genuinely past EOF; otherwise close the connection
    # silently on timeout so the client retries.
    avail = 0
    if start < file_size:
      t0 = time.time()
      while True:
        try:
          avail = os.path.getsize(path)
        except OSError:
          avail = 0
        done = not dl_thread.is_alive()
        if avail > start or done or (time.time() - t0 > 60):
          break
        time.sleep(0.3)
    if avail <= start:
      if start >= file_size:
        self.send_response(416)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
      # else: still growing and timed out — drop the connection; client retries
      return
    serve_end = min(end, avail)
    length = serve_end - start
    # 206 whenever the response is not the whole file. A 200 + partial
    # Content-Length makes the browser treat the truncated body as the full
    # resource, then moov sample offsets fall past EOF → decode error.
    self.send_response(206 if (start > 0 or length < file_size) else 200)
    self.send_header('Content-Type', 'video/mp4')
    self.send_header('Content-Length', str(length))
    # Always show total file size so browser knows to keep requesting
    self.send_header('Content-Range', f'bytes {start}-{serve_end - 1}/{file_size}')
    self.send_header('Accept-Ranges', 'bytes')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.end_headers()
    try:
      with open(path, 'rb') as f:
        f.seek(start)
        sent = 0
        while sent < length:
          chunk = f.read(min(256 * 1024, length - sent))
          if not chunk:
            if dl_thread.is_alive():
              time.sleep(0.2)
              continue
            break
          self.wfile.write(chunk)
          sent += len(chunk)
    except FileNotFoundError:
      return
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
      pass
    if done:
      stop.set()

  def _play_cache(self, body):
    # Embedded player (Kotlin/JavaFX): download file utuh ke cache play (~/.indonime/play),
    # balikin job_id buat polling progress. dest jadi file:// URI di client.
    try:
      url = body.get('server_url', '')
      label = body.get('label', '')
      os.makedirs(_PLAY_CACHE, exist_ok=True)
      with _jobs_lock:
        _job_seq[0] += 1
        jid = _job_seq[0]
        _jobs[jid] = {'id': jid, 'title': 'play-cache', 'status': 'running',
                      'done': 0, 'total': 0, 'dest': None, 'size': 0, 'error': None}
      threading.Thread(target=_play_cache_worker, args=(jid, url, label), daemon=True).start()
      return self._json(200, {'job_id': jid})
    except Exception as e:
      return self._err(e)

  def _download(self, body):
    try:
      url, title = body['server_url'], body['title']
      with _jobs_lock:
        _job_seq[0] += 1
        jid = _job_seq[0]
        _jobs[jid] = {'id': jid, 'title': title, 'status': 'running',
                      'done': 0, 'total': 0, 'dest': None, 'size': 0, 'error': None}
      threading.Thread(target=_dl_worker, args=(jid, url, title), daemon=True).start()
      return self._json(200, {'job_id': jid})
    except Exception as e:
      return self._err(e)

  def _static(self, path):
    root = os.path.realpath(_STATIC_DIR)
    if path == '/':
      path = '/index.html'
    fp = os.path.realpath(os.path.join(root, path.lstrip('/')))
    if not fp.startswith(root) or not os.path.isfile(fp):
      fp = os.path.join(root, 'index.html')
    if not os.path.isfile(fp):
      return self._json(404, {'error': 'app/dist belum di-build'})
    ctype, _ = mimetypes.guess_type(fp)
    if not ctype or '\r' in ctype or '\n' in ctype:
      ctype = 'application/octet-stream'
    with open(fp, 'rb') as f:
      data = f.read()
    self.send_response(200)
    self.send_header('Content-Type', ctype)
    self.send_header('Content-Length', str(len(data)))
    self.end_headers()
    self.wfile.write(data)


def start_server(port=0, static_dir=None):
  global _STATIC_DIR
  if static_dir:
    _STATIC_DIR = static_dir
  srv = ThreadingHTTPServer(('127.0.0.1', port), _Handler)
  threading.Thread(target=srv.serve_forever, daemon=True).start()
  return srv.server_address[1]