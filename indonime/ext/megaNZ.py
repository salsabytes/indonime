# MEGA stream decrypt — moov-first faststart rebuild + prefetch thread.
import random
import sys
import time
import base64
import threading
import queue
import tempfile
import urllib.parse
import urllib.request

from tuiko import style
from ..ui import Palette
from ..plugins._base import HEADERS, http_post_json, http_stream

# AES via cryptography (hard dep)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def mega_base64_decode(data):
  data += '=' * (4 - len(data) % 4)
  return base64.urlsafe_b64decode(data)


# Extract the file ID from a MEGA URL. Handles the #! format. Returns (clean_url, f_id).
def _mega_fid(url):
  clean = url.replace("#!", "file/").replace("!", "#", 1) if "#!" in url else url
  try:
    return clean, clean.split("file/")[1].split("#")[0]
  except IndexError:
    return None, None


# moov before mdat → the MP4 header is up front → mpv can play a still-growing file.
# 4-byte scan over the first ~_EARLY_MB MB; a random 'moov' inside mdat data is a
# ~0.05% chance, and worst case mpv just fails cleanly → the user retries.
def _is_faststart(early):
  moov = early.find(b'moov')
  if moov == -1:
    return False
  mdat = early.find(b'mdat')
  return mdat == -1 or moov < mdat


# True once the MP4 moov box is fully inside buf (faststart header ready).
def _moov_complete(buf):
  i = buf.find(b'moov')
  if i < 4 or i + 4 > len(buf):
    return False
  size = int.from_bytes(buf[i - 4:i], 'big')
  return size >= 8 and i - 4 + size <= len(buf)


# moov-first: rebuild non-faststart MP4s as faststart via HTTP Range
_HEAD_SCAN = 64 * 1024         # decrypted head sniffed to locate ftyp/mdat
_TAIL_SCAN = 4 * 1024 * 1024   # decrypted tail scanned for moov
_MID_CHUNK = 4 * 1024 * 1024   # range-stream chunk size for the mdat body
_MIN_SIZE = 1024 * 1024        # below this, sequential full download is instant anyway
_EARLY_MB = 8                  # MP4 moov scan window cap for the sequential fallback


# Decrypt ciphertext starting at byte `offset` (16-aligned).
# Same keystream as the continuous whole-file decryptor (MEGA CTR is one
# continuous counter stream across its 128KB chunks), so any 16-aligned slice
# matches sequential play byte-for-byte.
def _decrypt_range(k, iv, cipher, offset):
  init = int.from_bytes(iv, 'big') + (offset // 16)
  d = Cipher(algorithms.AES(k), modes.CTR(init.to_bytes(16, 'big'))).decryptor()
  return d.update(cipher)


# Yield (box_type, start, end) for top-level MP4 boxes in buf.
# A box may extend past the buffer (e.g. mdat spans the whole file while buf
# is just the head) — its header is still yielded, then walking stops.
def _walk_boxes(buf):
  i, n = 0, len(buf)
  while i + 8 <= n:
    size = int.from_bytes(buf[i:i + 4], 'big')
    btype = buf[i + 4:i + 8]
    if size == 1 and i + 16 <= n:  # 64-bit size extension
      size = int.from_bytes(buf[i + 8:i + 16], 'big')
    if size < 8:
      break
    yield btype, i, i + size
    if i + size > n:
      break  # box extends past buffer — can't walk further
    i += size


# Plan a faststart rebuild of a non-faststart MP4.
# head: decrypted bytes from offset 0. tail: decrypted bytes from tail_off.
# Returns (mdat_start, moov_start, moov_end), or None when the file is already
# streamable (faststart MP4 / MKV / not MP4) or the layout is unexpected.
def _plan_moov_first(head, tail, file_size, tail_off):
  mdat_start = next((s for t, s, e in _walk_boxes(head) if t == b'mdat'), None)
  if mdat_start is None:
    return None
  moov_in_head = head.find(b'moov')
  if moov_in_head != -1 and moov_in_head < mdat_start:  # moov up front → faststart
    return None
  j = tail.rfind(b'moov')
  if j < 4:
    return None
  size = int.from_bytes(tail[j - 4:j], 'big')
  moov_start = tail_off + j - 4
  # moov must be the last box in the file — a random 'moov' inside mdat data
  # would fail this and fall back safely instead of writing garbage.
  if size < 8 or moov_start < tail_off or moov_start + size != file_size:
    return None
  return mdat_start, moov_start, moov_start + size


_PATCH_CONTAINERS = (b'trak', b'mdia', b'minf', b'stbl', b'dinf', b'edts', b'moov', b'udta')


# Add `delta` to every stco/co64 chunk offset inside moov bytes [a, n).
# Reordering boxes moves mdat; without rewriting these tables, players read
# sample data from the old offsets and die within a second. This is exactly
# what qt-faststart does when it moves moov to the front.
# 'meta' full boxes (children at +4) are not recursed — only matters for
# timed-metadata tracks, which anime MP4s essentially never have.
def _patch_moov(buf, a, n, delta):
  i = a
  while i + 8 <= n:
    size = int.from_bytes(buf[i:i + 4], 'big')
    btype = buf[i + 4:i + 8]
    if size == 1 and i + 16 <= n:  # 64-bit size extension
      size = int.from_bytes(buf[i + 8:i + 16], 'big')
    if size < 8 or i + size > n:
      break
    j = i + size
    if btype in (b'stco', b'co64'):
      e = 4 if btype == b'stco' else 8
      pos = i + 16  # version/flags(4) + entry_count(4) → entries
      cnt = int.from_bytes(buf[i + 12:i + 16], 'big')
      for _ in range(cnt):
        if pos + e > j:
          break
        val = int.from_bytes(buf[pos:pos + e], 'big')
        buf[pos:pos + e] = ((val + delta) & (2 ** (8 * e) - 1)).to_bytes(e, 'big')
        pos += e
    elif btype in _PATCH_CONTAINERS:
      _patch_moov(buf, i + 8, j, delta)
    i = j


# GET ciphertext bytes [start, end) → bytes, or None when Range is unsupported.
def _http_range(url, start, end, timeout=30):
  if urllib.parse.urlparse(url).scheme not in ('http', 'https'):
    return None  # Bandit B310: only http(s), never file:/ custom schemes
  try:
    req = urllib.request.Request(
      url, headers={**HEADERS, 'Range': f'bytes={start}-{end - 1}'})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310: scheme guarded above
      if r.status != 206:
        return None
      data = r.read()
      return data if len(data) == end - start else None
  except Exception:
    return None


# Rebuild a non-faststart MP4 as faststart, streaming via range fetches.
# get_range(start, end) → decrypted bytes [start, end), or None on failure.
# write(buf): append decrypted bytes to the output file.
# mark_ready(): called once the header (ftyp+moov) is written → mpv can open.
# Returns 'done' | 'fallback' (caller should use sequential download)
# | 'abort' (header already written but the stream broke — stop, don't retry).
def _write_moov_first(k, iv, file_size, get_range, write, mark_ready):
  if file_size < _MIN_SIZE:
    return 'fallback'
  head_len = min(_HEAD_SCAN, file_size)
  tail_off = max(0, file_size - _TAIL_SCAN) & ~15
  head = get_range(0, head_len)
  if head is None:
    return 'fallback'
  tail = get_range(tail_off, file_size)
  if tail is None:
    return 'fallback'
  plan = _plan_moov_first(head, tail, file_size, tail_off)
  if plan is None:
    return 'fallback'
  mdat_start, moov_start, moov_end = plan
  write(head[:mdat_start])  # ftyp & friends
  moov = bytearray(tail[moov_start - tail_off: moov_end - tail_off])
  _patch_moov(moov, 0, len(moov), moov_end - moov_start)  # stco/co64 → new offsets
  write(moov)  # moov up front
  # first mdat chunk before telling mpv to open — mirrors the faststart path
  # where moov + the data following it are both present when mpv starts.
  first_end = min(mdat_start + _MID_CHUNK, moov_start)
  if first_end > mdat_start:
    s16 = mdat_start & ~15
    chunk = get_range(s16, first_end)
    if chunk is None:
      return 'abort'
    write(chunk[mdat_start - s16:])
  mark_ready()  # mpv can open now: header + first mdat data
  pos = first_end
  while pos < moov_start:
    end = min(pos + _MID_CHUNK, moov_start)
    s16 = pos & ~15
    chunk = get_range(s16, end)
    if chunk is None:
      return 'abort'
    write(chunk[pos - s16:])
    pos = end
  return 'done'


# Extract the decryption key from the MEGA URL fragment.
def _mega_key(url):
  if "#" in url:
    frag = url.split("#")[-1]
    if "!" in frag:
      return frag.split("!")[-1]
    return frag
  return None


# Parse a MEGA URL → (key, iv).
def _parse_mega_url(url):
  try:
    encoded_key = _mega_key(url)
    full_key = mega_base64_decode(encoded_key)
    k = bytes(full_key[i] ^ full_key[i + 16] for i in range(16))
    iv = full_key[16:24] + b"\x00" * 8
    return k, iv
  except Exception:
    return None


# --- Anti IP-ban MEGA --------------------------------------------------------
# MEGA blokir IP yang terlalu sering memanggil g.api.mega.co.nz (err -4 /
# -14). Semua call dipaksa lewat satu pacer global (gap minimum antar-request)
# dan hasil a:g di-cache per file_id — replay episode yang sama tidak
# menyentuh API lagi.
_API_GAP = 1.2     # detik minimal antar panggilan API (ponytail: nilai statis, naikkan kalau masih kena blok)
_INFO_TTL = 600    # dl_link MEGA tetap valid berjam-jam; 10 menit aman untuk replay
_pace_lock = threading.Lock()
_next_ok = [0.0]
_info_cache = {}   # file_id -> (saved_monotonic, dl_link, file_size)

def _api_pace():
  # Serialisasi sengaja: pemegang kunci tidur sampai gilirannya, jadi N thread
  # sekalipun tetap berjarak >= _API_GAP dari panggilan sebelumnya.
  with _pace_lock:
    delay = _next_ok[0] - time.monotonic()
    if delay > 0:
      time.sleep(delay)
    _next_ok[0] = time.monotonic() + _API_GAP

_ERR_NAMES = {-1:"internal",-2:"invalid",-3:"retry",-4:"rate-limited",
              -5:"denied",-6:"not found",-7:"inaccessible",-8:"quota",
              -9:"bad key",-11:"logged out",-13:"expired",-14:"blocked"}

# MEGA API → (dl_link, file_size). Backoff saat -3/-4 (server minta pelan);
# cache hasil supaya pemutaran ulang file yang sama tidak memanggil API lagi.
# (ponytail: tanpa single-flight — dua tab buka episode sama secara bersamaan
# masih 2x call; jarang terjadi, tambahin kalau keluhan muncul.)
def _fetch_file_info(file_id):
  hit = _info_cache.get(file_id)
  if hit is not None and time.monotonic() - hit[0] < _INFO_TTL:
    return hit[1], hit[2]
  for attempt in range(3):
    _api_pace()
    try:
      seq = random.randint(0, 0xFFFFFFFF)
      res = http_post_json(
        f"https://g.api.mega.co.nz/cs?id={seq}",
        [{"a": "g", "g": 1, "p": file_id}],
        timeout=15,
      )
    except Exception as e:
      print(f"[mega] _fetch_file_info exception: {e}", file=sys.stderr)
      return None
    if isinstance(res[0], int):
      err = res[0]
      print(f"[mega] API err {err} ({_ERR_NAMES.get(err,'?')})", file=sys.stderr)
      if err in (-3, -4) and attempt < 2:
        time.sleep((attempt + 1) * 3)  # 3s lalu 6s — kasih napas ke rate limiter
        continue
      return None
    info = res[0]['g'], res[0]['s']
    _info_cache[file_id] = (time.monotonic(), info[0], info[1])
    return info
  return None


# Fill the chunk queue from the stream response (runs in a thread).
def _run_prefetch(resp, q, stop):
  try:
    while True:
      chunk = resp.read(1024 * 1024)
      if not chunk or stop.is_set():
        break
      q.put(chunk)
    q.put(None)
  except Exception as e:
    q.put(e)


# Download+decrypt a MEGA file in the background; return early once streamable.
# MP4 faststart (moov up front): returns the moment the moov box is fully
# buffered — mpv opens in ~1s, the rest streams behind it.
# Non-faststart MP4 (moov at the end): rebuilt as faststart on the fly via
# HTTP Range fetches (head + tail, then the mdat body) — same instant open.
# MKV: returns after ~2MB. Range unsupported / unusual layout → sequential
# full download (mpv opens when the file is complete).
# moov must sit inside the last _TAIL_SCAN bytes; an oversized moov (>4MB,
# rare) falls back to full-download-then-play.
# Sequential download+decrypt fallback (original flow): full file, then play.
def _download_sequential(dl_link, k, iv, f, ready, stop, bytes_counter,
                         early_bytes, mkv_floor, _fmt):
  f.seek(0)
  f.truncate()
  bytes_counter[0] = 0
  response = http_stream(dl_link, timeout=30)
  chunk_queue = queue.Queue(maxsize=2)
  t = threading.Thread(
    target=_run_prefetch, args=(response, chunk_queue, stop),
    daemon=True,
  )
  t.start()

  downloaded = 0
  _first_dec = None
  early_buf = b''  # decrypted bytes up to early_bytes → faststart MP4 check
  c = Cipher(algorithms.AES(k), modes.CTR(iv))
  d = c.decryptor()
  while True:
    chunk = chunk_queue.get()
    if chunk is None:
      break
    if isinstance(chunk, Exception):
      raise chunk
    dec = d.update(chunk)
    f.write(dec)
    if _first_dec is None:
      _first_dec = dec[:8]
      _fmt[0] = 'mp4' if b'\x66\x74\x79\x70' in _first_dec else 'mkv'
    if len(early_buf) < early_bytes:
      early_buf += dec[: early_bytes - len(early_buf)]
    downloaded += len(chunk)
    bytes_counter[0] = downloaded
    # MKV: tiny header → stream once a small floor is buffered.
    # MP4: launch as soon as the moov box is fully inside the buffer
    # (faststart) — a truncated moov is exactly why mpv can't open.
    if not ready.is_set():
      if _fmt[0] == 'mp4':
        if _is_faststart(early_buf) and _moov_complete(early_buf):
          ready.set()
      elif downloaded >= mkv_floor:
        ready.set()
    if stop.is_set():
      break
  d.finalize()

# After a full sequential download, move moov to front so Range playback works.
# If moov is already at front (faststart) or file isn't MP4, this is a no-op.
def _reorder_moov_to_front(path):
  try:
    with open(path, 'rb') as f:
      data = f.read()
  except OSError:
    return
  if len(data) < 16 or data[4:8] != b'ftyp':
    return  # not MP4
  # Walk top-level boxes to find mdat and moov positions.
  i, n = 0, len(data)
  mdat_start = moov_start = moov_size = 0
  while i + 8 <= n:
    sz = int.from_bytes(data[i:i + 4], 'big')
    btype = data[i + 4:i + 8]
    if sz == 1 and i + 16 <= n:
      sz = int.from_bytes(data[i + 8:i + 16], 'big')
    if sz < 8:
      break
    if btype == b'mdat':
      mdat_start = i
    if btype == b'moov':
      moov_start = i
      moov_size = sz
    if i + sz > n:
      break
    i += sz
  if not mdat_start or not moov_start or moov_size < 8:
    return
  moov_end = moov_start + moov_size
  # moov already at front → faststart, nothing to do.
  if moov_start < mdat_start:
    return
  # moov not at end of file → unexpected layout, skip reordering.
  if moov_end < len(data):
    return
  delta = moov_size
  # Build new file: pre-mdat boxes + moov (offsets patched) + mdat data.
  reorder = bytearray()
  reorder += data[:mdat_start]  # ftyp & friends
  moov = bytearray(data[moov_start:moov_end])
  _patch_moov(moov, 0, len(moov), delta)
  reorder += moov
  reorder += data[mdat_start:moov_start]  # original mdat data
  reorder += data[moov_end:]
  with open(path, 'wb') as f:
    f.write(reorder)


def resolve_mega_file_stream(url, file_id):
  parsed = _parse_mega_url(url)
  if parsed is None:
    print(style("✘ Gagal parse key MEGA", Palette.error))
    return None
  k, iv = parsed

  info = _fetch_file_info(file_id)
  if info is None:
    print(style("✘ Gagal ambil API MEGA", Palette.error))
    return None
  dl_link, file_size = info

  ready = threading.Event()
  stop = threading.Event()
  early_bytes = _EARLY_MB * 1024 * 1024  # MP4 moov scan window cap
  mkv_floor = 2 * 1024 * 1024           # MKV EBML header is tiny; stream after this
  _fmt = [None]  # mutable for closure: 'mp4' or 'mkv'
  bytes_counter = [0]  # shared counter for 0-100% progress

  with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as _tmp:
    temp_path = _tmp.name

  def _download():
    try:
      with open(temp_path, "wb") as f:
        def write(buf):
          f.write(buf)
          bytes_counter[0] += len(buf)  # progress = unique bytes written

        def get_range(start, end):
          if stop.is_set():
            return None
          cipher = _http_range(dl_link, start, end)
          if cipher is None:
            return None
          return _decrypt_range(k, iv, cipher, start)

        st = _write_moov_first(k, iv, file_size, get_range, write, ready.set)
        if st == 'done':
          return
        if st == 'abort':
          return  # header written, stream broke — mpv plays what's there; retry

        # Fallback: sequential download+decrypt (original flow).
        _download_sequential(dl_link, k, iv, f, ready, stop, bytes_counter,
                             early_bytes, mkv_floor, _fmt)
        if _fmt[0] == 'mp4':
          _reorder_moov_to_front(temp_path)  # moov to front for Range playback
    except Exception as e:
      print(style(f"✘ Mega Stream Error: {e}", Palette.error))
      ready.set()
      return

    ready.set()  # always signal when the download finishes (mpv waits for this)

  dl_thread = threading.Thread(target=_download, daemon=True)
  dl_thread.start()

  return temp_path, ready, stop, dl_thread, bytes_counter, file_size
