# search → select → play — tuiko-powered.
import argparse
import importlib
import io
import json
import os
import pkgutil
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import player
from .ui import (
  banner_header, print_banner, print_header, print_step,
  print_success, print_error, print_warning, print_separator,
  make_postplay_actions, make_footer, progress,
)

from . import plugins
from tuiko import multiselect, prompt, select, session
from .ext import pdrain, megaNZ, gdrive
from .ext.megaNZ import _mega_fid, _mega_key
from .plugins._base import cache_clear, cached, http_download, resolve_url

# Human-readable byte size (1024-based).
def _fmt_size(n):
  for unit in ("B", "KB", "MB", "GB"):
    if n < 1024 or unit == "GB":
      return f"{n:.2f} {unit}"
    n /= 1024

# Compatible server prefixes
_COMPATIBLE = {'pdrain', 'pixeldrain', 'mega', 'gdrive', 'desustream'}


def _is_mega_link(url, name=''):
  # Otakudesu links arrive via the desustream resolver (?id=... → 302). That
  # resolver serves BOTH mega.nz and pixeldrain targets, so "desustream" alone
  # can't classify — follow the redirect once and check the real host.
  s = f'{url} {name}'.lower()
  if 'mega' in s:
    return True
  if 'desustream' not in s:
    return False
  try:
    cur = resolve_url(url, timeout=15)
    return 'mega.nz' in cur or 'mega.co.nz' in cur
  except Exception:
    return False

# Last-resort check (mirror server._play): provider links labeled pdrain/gdrive
# sometimes 302 to Mega — detect the real redirect target before giving up.
def _redirects_to_mega(url):
  try:
    cur = resolve_url(url, timeout=15)
    return 'mega.nz' in cur or 'mega.co.nz' in cur
  except Exception:
    return False

_CANCEL = "__cancel__"  # sentinel quality: user cancelled at the quality prompt
_DL_RETRIES = 2   # auto-retry attempts per failed episode (network blips)
_DL_WORKERS = 2   # parallel batch downloads — low-end devices, keep it small

def _safe_name(title):
  # Filesystem-safe episode filename stem (shared by dest-path + download fns).
  return "".join(c if c.isalnum() or c in " .-_()[]" else "_" for c in title)[:100]

def _dest_path(title):
  return os.path.join(os.path.expanduser("~"), "Downloads", f"{_safe_name(title)}.mp4")

def _already_downloaded(title):
  dest = _dest_path(title)
  return os.path.exists(dest) and os.path.getsize(dest) > 0

def _compatible_servers(dl_links):
  # Flatten {quality: {server: url}} → [(label, url)] for compatible servers.
  options = []
  for res, servers in dl_links.items():
    for s_name, s_url in servers.items():
      if any(x in s_name.lower() for x in _COMPATIBLE):
        options.append((f'[{res}] {s_name}', s_url))
  return options


# History
_HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".indonime", "history.json")
_HISTORY = None

def _load_history():
  global _HISTORY
  if _HISTORY is not None:
    return _HISTORY
  try:
    with open(_HISTORY_FILE) as f:
      _HISTORY = json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    _HISTORY = {}
  return _HISTORY

def _save_history(anime_url, episode_url):
  h = _load_history()
  h[anime_url] = {"episode_url": episode_url, "updated": time.time()}
  os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
  with open(_HISTORY_FILE, "w") as f:
    json.dump(h, f, indent=2)

def _check_history(anime_url, episode_list):
  h = _load_history()
  entry = h.get(anime_url)
  if not entry:
    return None
  for i, ep in enumerate(episode_list):
    if ep["url"] == entry.get("episode_url"):
      return i
  return None

# Play episode
def _play_mega(server_url, out=None):
  # Resolve a Mega stream + launch mpv. Returns (ok, final_mega_url).
  with progress("🔓 Resolving Mega link...", out=out):
    try:
      curr = resolve_url(server_url, timeout=15)
      if ("mega.nz" in curr or "mega.co.nz" in curr) and "#" in curr:
        final_mega_url = curr
      else:
        print_error("Redirect tidak mengarah ke Mega.")
        return False, None
    except Exception as e:
      print_error(f"Network Error: {e}")
      time.sleep(3)
      return False, None

    try:
      final_mega_url, f_id = _mega_fid(final_mega_url)
      if f_id is None:
        print_error("Gagal extract file ID MEGA.")
        return False, None
      stream = megaNZ.resolve_mega_file_stream(final_mega_url, f_id)
      if stream is None:
        return False, None
      path, ready, stop, dl_thread, bytes_counter, file_size = stream
    except Exception as e:
      print_error(f"Gagal Streaming: {e}")
      time.sleep(3)
      return False, None

  with progress("📥 Downloading stream...", out=out) as up:
    _stall_t0 = time.time()
    _last_bytes = 0
    # Wait for the FULL file: unlike the browser (range requests), mpv reads
    # the local temp file sequentially — launching on a partial faststart file
    # hits EOF when buffered data runs out and playback dies within seconds.
    # Loop ends when the downloader exits (full file normally, partial on
    # abort — either way mpv plays what's on disk instead of hanging).
    while dl_thread.is_alive():
      up(bytes_counter[0])
      done = bytes_counter[0]
      if done != _last_bytes:  # still making progress → reset the stall timer
        _last_bytes = done
        _stall_t0 = time.time()
      elif time.time() - _stall_t0 > 60:  # 60s without progress = dead connection
        print_warning("Download stalled (>60s tanpa progress). Cek koneksi atau retry.")
        stop.set()  # kill the old thread before retry
        return False, None
      time.sleep(0.15)

  print_step("🚀 Launching mpv player...")
  player.play_with_mpv(path, is_temp_file=True, cleanup=False)
  stop.set()
  dl_thread.join(timeout=10)
  if os.path.exists(path):
    os.remove(path)
  return True, final_mega_url

def _play_episode(episode_url, plugin, server_url=None, key_source=None, out=None):
  # Resolve stream and play. Returns (success, server_url).
  while True:
    if server_url is None:
      with progress("🔍 Resolving stream...", out=out):
        dl_links = plugin.downloads(episode_url)

      options = _compatible_servers(dl_links)

      if not options:
        print_warning("No compatible servers found.")
        return False, None

      labels = [o[0] for o in options]
      sel = select("📥  Select quality & server:", labels,
                   key_source=key_source, out=out, header=banner_header())
      if sel is None:
        return False, None
      last_selected_server_name, server_url = options[sel]
    else:
      last_selected_server_name = "replay"

    if _is_mega_link(server_url, last_selected_server_name):
      ok, final_mega_url = _play_mega(server_url, out=out)
      if not ok:
        server_url = None
        continue
      return True, final_mega_url

    if 'gdrive' in server_url.lower() or 'gdrive' in last_selected_server_name.lower():
      with progress("🌀 Resolving GDrive link...", out=out):
        final_target = gdrive.scrape(server_url)
    else:
      with progress("🌀 Bypassing PixelDrain link...", out=out):
        final_target = pdrain.scrape(server_url)

    if not final_target:
      # Last resort (mirror server._play): link may redirect to Mega.
      if _redirects_to_mega(server_url):
        ok, final_mega_url = _play_mega(server_url, out=out)
        if ok:
          return True, final_mega_url
      print_error("Stream tidak tersedia. Pilih resolusi lain.")
      server_url = None
      continue

    print_step("🚀 Launching mpv player...")
    return player.play_with_mpv(final_target), server_url


# Download episode
def _download_mega(server_url, safe, downloads_dir, out=None, agg=None):
  # Download a Mega file. Returns (dest, size, reason). reason None = success.
  # agg: optional _BatchBar — total + byte deltas feed the batch-wide bar.
  try:
    curr = resolve_url(server_url, timeout=15)
  except Exception as e:
    print_error(f"Network Error: {e}")
    return None, 0, f"Network Error: {e}"

  # Extract key + file_id — try server_url first, then redirect URL
  megakey_raw = _mega_key(server_url) or _mega_key(curr)
  _, f_id = _mega_fid(curr)
  if not f_id:
    _, f_id = _mega_fid(server_url)
  if not f_id:
    print_error("Could not extract Mega file ID.")
    return None, 0, "Could not extract Mega file ID."

  # Reconstruct a clean URL — the host isn't used downstream, only the #key fragment matters
  mega_url = f"https://mega.nz/file/{f_id}#{megakey_raw}"

  try:
    stream = megaNZ.resolve_mega_file_stream(mega_url, f_id)
    if stream is None:
      return None, 0, "Gagal resolve stream Mega"
    path, ready, stop, dl_thread, bytes_counter, file_size = stream
    if agg:
      agg.add_total(safe, file_size)

    # Wait for the full download. `ready` only means streaming (moov header
    # buffered → mpv can open), NOT a finished download — that's why the bar
    # used to stick at 100% early. The right signal: wait for the thread to end.
    with progress(f"⬇ Downloading {safe}...", total=file_size, out=out) as up:
      t0 = time.time()
      last = cur = 0
      while dl_thread.is_alive():
        if time.time() - t0 > 600:
          print_warning("Download timed out (>10 min).")
          stop.set()
          return None, 0, "Download timed out (>10 min)."
        time.sleep(0.15)
        cur = bytes_counter[0]
        if agg and cur != last:
          agg.add_done(cur - last)  # delta → batch bar
        last = cur
        up(cur)
      up(bytes_counter[0])  # final value → bar ends at the real size
      if agg and cur != last:
        agg.add_done(bytes_counter[0] - last)
    size = bytes_counter[0]
    if size != file_size:
      # the stream broke mid-way — never copy a truncated file as a "success"
      print_error(f"Download incomplete: {size}/{file_size} bytes")
      stop.set()
      if os.path.exists(path):
        os.remove(path)
      return None, 0, "Download incomplete"

    dest = os.path.join(downloads_dir, f"{safe}.mp4")
    shutil.copy2(path, dest)
    if os.path.exists(path):
      os.remove(path)
    return dest, size, None
  except Exception as e:
    print_error(f"Download failed: {e}")
    return None, 0, f"Download failed: {e}"

def _download_pdrain(server_url, safe, downloads_dir, out=None, scraper=pdrain.scrape, agg=None):
  # Download via a direct-URL resolver (PixelDrain or GDrive).
  # Returns (dest, size, reason). reason None = success.
  try:
    with progress("🌀 Bypassing link...", out=out):
      final_url = scraper(server_url)
    if not final_url:
      # Last resort (mirror server._play): link may redirect to Mega.
      if _redirects_to_mega(server_url):
        return _download_mega(server_url, safe, downloads_dir, out=out, agg=agg)
      print_error("Stream not available.")
      return None, 0, "Stream not available."

    dest = os.path.join(downloads_dir, f"{safe}.mp4")
    size = http_download(final_url, dest, f"⬇ Downloading {safe}...", out=out,
                         on_total=(lambda n: agg.add_total(safe, n)) if agg else None,
                         on_bytes=(lambda n: agg.add_done(n)) if agg else None)
    return dest, size, None
  except Exception as e:
    print_error(f"Download failed: {e}")
    return None, 0, f"Download failed: {e}"

def _download_episode(episode_title, episode_url, plugin,
                      key_source=None, out=None, bar_out=None,
                      quality=None, quiet=False, agg=None):
  # Download one episode. Returns (quality_label, bytes, reason).
  # quality == _CANCEL when the user bails; reason None on success. On failure
  # the picked quality_label is still returned (None if none was picked) so a
  # retry can reuse it instead of prompting again. quiet=True → never prompt
  # (parallel batch worker): reuse the given quality or silently take the
  # first compatible source. agg: optional _BatchBar — per-episode bars are
  # muted into bar_out (StringIO in batch) and the aggregate bar renders instead.
  safe = _safe_name(episode_title)
  downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
  os.makedirs(downloads_dir, exist_ok=True)
  bar_out = bar_out or out

  # Resolve server URL + pick quality (caller never pre-resolves)
  with progress("🔍 Resolving download links...", out=bar_out):
    dl_links = plugin.downloads(episode_url)

  options = _compatible_servers(dl_links)

  if not options:
    print_warning("No compatible download sources found.")
    return None, 0, "No compatible download sources found."

  labels = [o[0] for o in options]
  if quality is not None and quality in labels:
    sel = labels.index(quality)  # reuse same quality — no prompt
  elif quiet:
    sel = 0  # batch worker: never prompt, quietly take the first compatible
    quality = labels[0]
  else:
    sel = select("📥  Select quality & server:", labels,
                 key_source=key_source, out=out, header=banner_header())
    if sel is None:
      return _CANCEL, 0, "Dibatalkan"
    quality = labels[sel]

  server_name, server_url = options[sel]

  if _is_mega_link(server_url, server_name):
    dest, size, reason = _download_mega(server_url, safe, downloads_dir, out=bar_out, agg=agg)
  elif 'gdrive' in server_url.lower() or (server_name and 'gdrive' in server_name.lower()):
    dest, size, reason = _download_pdrain(server_url, safe, downloads_dir, out=bar_out,
                                          scraper=gdrive.scrape, agg=agg)
  else:
    dest, size, reason = _download_pdrain(server_url, safe, downloads_dir, out=bar_out, agg=agg)

  if reason:
    return quality, 0, reason  # picked quality survives → retry reuses, no re-prompt

  if not agg:
    print_success(f"✅ Downloaded: {dest}")  # batch → the status line under the bar covers it
  return quality, size, None


def _episode_labels(episode_list, resume_idx, back_label):
  # Label list for the episode picker: '▶' marks the resume episode.
  labels = []
  for i, ep in enumerate(episode_list):
    mark = '▶' if resume_idx == i else ' '
    labels.append(f"{mark} EP{i+1:02d}  —  {ep['title'][:50]}")
  labels.append(f"↩  {back_label}")
  return labels

class _BatchBar:
  # ONE never-moved progress bar + the finished-episode status lines below it.
  # Workers only report byte deltas (thread-safe counters). The render thread
  # redraws the whole block each tick — cursor up by the number of rows it
  # *emitted last time* (never the current count: a just-added status would
  # overshoot and wipe the TUI above), draw the tuiko bar, then re-emit the
  # status lines. Worker prints are muted in batch so no stray line shifts
  # the block; statuses replace by title so a retry→success updates one row.
  def __init__(self, eps_total, out=None):
    self._eps_total = eps_total
    self._out = out or sys.stdout
    self._lock = threading.Lock()
    self._sizes = {}   # safe-name → file size (per-episode, survives retries)
    self._total = 0
    self._done = 0     # bytes written across all workers
    self._status = {}  # safe-name → line (replace per episode, stable rows)
    self._rows = 0     # rows emitted by the last draw (bar + statuses)
    self._dirty = True  # statuses changed → full block redraw needed
    self._stop = threading.Event()
    self._thread = None

  def add_total(self, key, n):
    with self._lock:
      self._sizes[key] = n  # retry with the same key overwrites → no double count
      self._total = sum(self._sizes.values())

  def add_done(self, n):
    with self._lock:
      self._done += n

  def add_status(self, key, line):
    with self._lock:
      self._status[key] = line  # replace → the same row is redrawn, no growth
      self._dirty = True

  def _frac(self):
    with self._lock:
      total, done = self._total, self._done
    return min(done / total, 1.0) if total else 0.0

  def start(self):
    self._thread = threading.Thread(target=self._render, daemon=True)
    self._thread.start()

  def stop(self):
    self._stop.set()
    if self._thread:
      self._thread.join(timeout=2)
      self._thread = None

  def _draw(self, up, redraw):
    # The block occupies `rows` lines (bar + one per episode) and the cursor
    # always rests one line below it (the foot). Jumping up `rows` lands
    # exactly on the bar line; tuiko's bar redraws in place on that line.
    # redraw=True → a status row changed: re-emit bar + all statuses.
    # redraw=False → only the bar fraction moved: refresh it, return to foot.
    with self._lock:
      statuses = list(self._status.values())
    rows = 1 + len(statuses)  # bar + one row per episode
    if self._rows:
      self._out.write(f"\x1b[{self._rows}A")  # foot → bar line
    up(self._frac() * 100)
    if redraw:
      if statuses:
        self._out.write("\n" + "\n".join(statuses))
      self._out.write("\n")  # foot: one line below the last status
      self._rows = rows
    elif self._rows:
      self._out.write(f"\x1b[{self._rows}B")  # bar line → foot
    self._out.flush()

  def _render(self):
    ctx = progress(f"⬇ BATCH ({self._eps_total} episode)", total=100, out=self._out)
    up = ctx.__enter__()
    try:
      while not self._stop.wait(0.15):
        with self._lock:
          redraw = self._dirty
          self._dirty = False
        self._draw(up, redraw)
      with self._lock:
        redraw = self._dirty
        self._dirty = False
      self._draw(up, redraw)  # final frame: catch the last status
    finally:
      ctx.__exit__(None, None, None)


def _queue_attempt(ep_idx, quality, prompt, agg, episode_list, plugin,
                   key_source=None, out=None):
  # One episode with auto-retry. Returns (q, size, reason, skipped).
  # prompt=True → first pick, may ask the user at the quality prompt;
  # prompt=False → parallel worker: never prompts, reuses quality.
  title, url = episode_list[ep_idx]['title'], episode_list[ep_idx]['url']
  if _already_downloaded(title):
    return None, 0, None, True
  # Mute the per-episode bar into StringIO whenever the batch bar is live —
  # tuiko's bar is a single carriage-return line; concurrent bars would
  # shred the terminal.
  w_out = out if prompt else io.StringIO()
  w_bar = io.StringIO() if agg else None
  for attempt in range(_DL_RETRIES + 1):
    q, size, reason = _download_episode(
      title, url, plugin, key_source=key_source if prompt else None,
      out=w_out, bar_out=w_bar, quality=quality, quiet=not prompt, agg=agg)
    if q == _CANCEL or reason is None:
      return q, size, reason, False
    quality = q  # picked quality survives the failure → reuse on retry
    if attempt < _DL_RETRIES:
      print_warning(f"↻ {title}: {reason} — retry {attempt + 2}/{_DL_RETRIES + 1}")
      time.sleep(1)  # rate-limit / transient blip recovery, not a tight loop
  return q, size, reason, False


def _queue_record(i, q, size, reason, skipped, stats, bar, episode_list):
  key = _safe_name(episode_list[i]['title'])
  title = episode_list[i]['title'][:50]
  if skipped:
    stats['skip'] += 1
    bar.add_status(key, f"↺ {title} — sudah ada")
  elif reason is None:
    stats['ok'] += 1
    stats['total'] += size
    bar.add_status(key, f"✓ {title} — {_fmt_size(size)}")
  else:
    stats['fail'] += 1
    stats['failed'].append((episode_list[i]['title'], reason))
    bar.add_status(key, f"✘ {title} — {reason}")


def _run_download_queue(episode_list, plugin, resume_idx, header,
                        key_source=None, out=None):
  # ctrl-d: multi-select download queue. The first pick resolves the quality
  # prompt once (sequential); every other pick downloads in parallel (up to
  # _DL_WORKERS) reusing that quality, each with _DL_RETRIES auto-retries.
  # Episodes already on disk are skipped. A single _BatchBar renders the
  # overall progress (per-episode bars are muted). Returns None.
  ep_labels = _episode_labels(episode_list, resume_idx, "")[:-1]
  picks = multiselect("⬇  Pilih episode:", ep_labels, search=True, fuzzy=True,
                      key_source=key_source, out=out, header=header,
                      shortcuts={"ctrl-a": "pilih semua"})
  if picks == "pilih semua":
    picks = set(range(len(ep_labels)))
  if not picks:
    return

  print_header("⬇ DOWNLOADING", "⬇")
  picks = sorted(picks)
  stats = {'ok': 0, 'fail': 0, 'skip': 0, 'total': 0, 'failed': []}
  bar = _BatchBar(len(picks), out=out)

  bar.start()
  try:
    # First pick: sequential + prompt once → the quality used by the whole batch.
    quality = None
    q, size, reason, skipped = _queue_attempt(
      picks[0], None, True, bar, episode_list, plugin, key_source, out)
    if q == _CANCEL:
      return  # user bailed at the quality prompt → stop the queue
    _queue_record(picks[0], q, size, reason, skipped, stats, bar, episode_list)
    if reason is None:
      quality = q

    # The rest: parallel workers, same quality, no prompts.
    rest = picks[1:]
    if rest:
      with ThreadPoolExecutor(max_workers=min(_DL_WORKERS, len(rest))) as ex:
        futs = {ex.submit(_queue_attempt, i, quality, False, bar,
                          episode_list, plugin, key_source, None): i
                for i in rest}
        for fut in as_completed(futs):
          i = futs[fut]
          _queue_record(i, *fut.result(), stats, bar, episode_list)
  finally:
    bar.stop()

  if stats['ok'] or stats['fail'] or stats['skip']:
    print_success(f"Queue selesai — {stats['ok']} berhasil, {stats['skip']} sudah ada, "
                  f"{stats['fail']} gagal, {_fmt_size(stats['total'])}")
    for title, reason in stats['failed']:
      print_warning(f"{title}: {reason}")
    time.sleep(2)  # let the message be read before the list re-renders

def _post_play_action(cmd, idx, total):
  # Map post-play command → (new_idx, action). action: next/prev/replay/quality/back/quit.
  if cmd == '▶  NEXT':
    if idx + 1 < total:
      return idx + 1, 'next'
    return idx, 'back'
  if cmd == '◀  PREV':
    if idx > 0:
      return idx - 1, 'prev'
    return idx, 'back'
  if cmd == '↺  REPLAY':
    return idx, 'replay'
  if cmd == '⚙  QUALITY':
    return idx, 'quality'
  return idx, 'quit'

def _episode_nav(episode_list, plugin, back_label='<< BACK',
                 show_banner=True, anime_url=None, mode='play',
                 key_source=None, out=None):
  # Episode pick → play → post-play loop. Returns 'back' or 'quit'.
  idx = 0
  _last_url = None
  resume_idx = _check_history(anime_url, episode_list) if anime_url else None
  header = banner_header() if show_banner else ()

  while True:
    labels = _episode_labels(episode_list, resume_idx, back_label)
    sel = select("▶  Select episode:", labels, search=True, fuzzy=True,
                 key_source=key_source, out=out, header=header,
                 shortcuts={"ctrl-d": "download"})
    if isinstance(sel, str):
      if sel == 'download':
        _run_download_queue(episode_list, plugin, resume_idx, header,
                            key_source=key_source, out=out)
      continue
    if sel is None or sel == len(labels) - 1:
      cache_clear()
      return 'back'

    idx = sel
    if mode == 'download':
      print_header("⬇ DOWNLOADING", "⬇")
      _download_episode(episode_list[idx]['title'], episode_list[idx]['url'], plugin,
                        key_source=key_source, out=out)
      time.sleep(2)
      return 'back'
    _last_url = None

    while True:
      print_header("🎬 NOW PLAYING", "▶")
      ok, url = _play_episode(
        episode_list[idx]['url'], plugin, server_url=_last_url,
        key_source=key_source, out=out)
      if not ok:
        time.sleep(2)
        break
      if anime_url:
        _save_history(anime_url, episode_list[idx]['url'])
      _last_url = url

      print_separator()

      post_choices = make_postplay_actions(idx, len(episode_list))
      cmd_idx = select("🎮  Command:", post_choices,
                       key_source=key_source, out=out, header=header)
      if cmd_idx is None:
        return 'quit'

      idx, action = _post_play_action(post_choices[cmd_idx], idx, len(episode_list))
      if action == 'back':
        break
      if action == 'quit':
        return 'quit'
      if action != 'replay':
        _last_url = None
      # next/prev/quality/replay → back to NOW PLAYING with (maybe) a new episode



# Customizable shortcuts (search screen)
# Map key → action. Actions handled in _tui_loop: 'provider', 'quit', 'abort'.
# Keep keys non-printable (ctrl-...) so they don't hijack search-box typing.
# ctrl-b because VS Code's terminal strips Alt and swallows Ctrl+P/Q (Quick
# Open / Quick Access); b isn't intercepted by any terminal. Quit needs no
# shortcut — escape / the ABORT sentinel already quit.
_SHORTCUTS = {
  "ctrl-b": "provider",
}

# Catalog cache: list_all() is big (845KB) — keep it cached persistently so
# back-navigation doesn't refetch. Keyed per plugin module via cached().
@cached(ttl=600, persist=True)
def _get_catalog(plugin):
  with progress("Loading catalog..."):
    return plugin.list_all()

# Search and select helper
def _catalog_select(plugin, key_source=None, out=None, shortcuts=None):
  # Live fuzzy search over the full catalog — no Enter needed.
  # Returns (url, episode_list), a shortcut action string, 'abort' when the
  # user bails (escape / ABORT sentinel), or None when nothing is found.
  print_header("🔎 SEARCHING", "🔎")
  catalog = _get_catalog(plugin)

  if not catalog:
    return 'provider-down'  # load failed or provider is down — not "no results"

  titles = [item['title'] for item in catalog] + ['↩  -- ABORT --']
  sel = select("📺  Cari anime:", titles, search=True, fuzzy=True,
               key_source=key_source, out=out, header=banner_header(),
               shortcuts=shortcuts)

  if isinstance(sel, str):
    return sel  # shortcut action (e.g. 'provider', 'quit')
  if sel is None or sel == len(titles) - 1:
    return 'abort'  # user bailed (escape / ABORT sentinel) — back to search silently

  selected = catalog[sel]
  with progress("Fetching episode list...", out=out):
    episode_list = plugin.episodes(selected['url'])

  if not episode_list:
    return None

  return selected['url'], episode_list

def _search_and_select(plugin, query, key_source=None, out=None, shortcuts=None):
  # Search → pick title → fetch episode list.
  # Returns (url, episode_list), a shortcut action string ('provider'/'quit'/...),
  # 'abort' when the user bails, or None when nothing is found.
  # query=None → live fuzzy search over the cached full catalog (TUI mode).
  # query given → network search (one-shot CLI mode).
  if query is None:
    return _catalog_select(plugin, key_source=key_source, out=out, shortcuts=shortcuts)

  print_header("🔎 SEARCHING", "🔎")
  with progress("Searching...", out=out):
    results = plugin.search_anime(query)

  if not results:
    return None

  choices = [item['title'] for item in results] + ['↩  -- ABORT --']
  sel = select("📺  Select title:", choices, search=True, fuzzy=True,
               key_source=key_source, out=out, header=banner_header())

  if sel is None or sel == len(choices) - 1:
    return None

  selected_title = choices[sel]
  selected_url = next(
    item['url'] for item in results
    if item['title'] == selected_title
  )

  with progress("Fetching episode list...", out=out):
    episode_list = plugin.episodes(selected_url)

  if not episode_list:
    return None

  return selected_url, episode_list

def _tui_loop():
  p_name = 'otakudesu'
  _last_plugin_name = None
  _plugin = None
  available_providers = [
    m.name for m in pkgutil.iter_modules(plugins.__path__)
    if not m.name.startswith('_')
  ]

  while True:
    # Run straight into the anime search — no main menu.
    if p_name != _last_plugin_name:
      _plugin = importlib.import_module(f'indonime.plugins.{p_name}')
      _last_plugin_name = p_name

    hit = _search_and_select(_plugin, None, shortcuts=_SHORTCUTS)
    if isinstance(hit, str):
      if hit == 'provider':
        sel = select("📡  Select provider:", available_providers, header=banner_header())
        if sel is not None:
          p_name = available_providers[sel]
      elif hit == 'provider-down':
        print_warning("Catalog load failed — the site may be down. Try again or press ctrl-b to switch provider.")
        time.sleep(2)
      elif hit == 'quit' or hit == 'abort':
        break  # quit shortcut, or escape/ABORT with no menu left → leave
      # unknown action → just re-run the search
      continue
    if hit is None:
      print_warning("Nothing found.")
      time.sleep(2)
      continue

    selected_url, episode_list = hit
    if _episode_nav(
      episode_list, _plugin,
      back_label='<< BACK TO SEARCH', show_banner=True,
      anime_url=selected_url,
    ) == 'quit':
      break

  print_banner()
  make_footer()
  print_success("Thanks for using Indonime! ~ Sayonara ~")


def _one_shot_mode(query, provider, mode):
  # One-shot search → play or download → exit.
  print_banner()

  try:
    plugin = importlib.import_module(f'indonime.plugins.{provider}')
  except Exception as e:
    print_error(f"Plugin error: {e}")
    prompt("↩  [enter] to continue")
    return

  hit = _search_and_select(plugin, query)
  if hit is None:
    print_warning("Nothing found.")
    prompt("↩  [enter] to continue")
    return

  selected_url, episode_list = hit

  _episode_nav(
    episode_list, plugin,
    back_label='<< QUIT', show_banner=False,
    anime_url=selected_url, mode=mode,
  )

  if player.current_mpv_process and player.current_mpv_process.poll() is None:
    player.current_mpv_process.wait()


def main():
  parser = argparse.ArgumentParser(
    description='Indonime — Subtitle Indonesia Anime Searcher'
  )
  parser.add_argument(
    'mode', nargs='?', default='tui',
    help='Mode: tui (interactive, default) or search <query>'
  )
  parser.add_argument('query', nargs='*', help='Search query')
  parser.add_argument(
    '-d', '--download', action='store_true',
    help='Download instead of play (use with search mode)'
  )
  parser.add_argument(
    '-p', '--provider', default='otakudesu',
    choices=['otakudesu', 'anoboy'],
    help='Provider (default: otakudesu)'
  )
  args = parser.parse_args()

  try:
    with session():
      if args.mode == 'search' and args.query:
        _one_shot_mode(' '.join(args.query), args.provider, 'download' if args.download else 'play')
      else:
        _tui_loop()
  except KeyboardInterrupt:
    pass
  finally:
    print()
