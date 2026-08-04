# search → select → play — tuiko-powered.
import argparse
import importlib
import json
import os
import pkgutil
import shutil
import time

from . import player
from .ui import (
  banner_header, print_banner, print_header, print_step,
  print_success, print_error, print_warning, print_separator,
  make_postplay_actions, make_footer, progress,
)

from . import plugins
from tuiko import multiselect, prompt, select, session
from .ext import pdrain, megaNZ
from .ext.megaNZ import _mega_fid, _mega_key
from .plugins._base import cache_clear, cached, http_download, resolve_url

# Human-readable byte size (1024-based).
def _fmt_size(n):
  for unit in ("B", "KB", "MB", "GB"):
    if n < 1024 or unit == "GB":
      return f"{n:.2f} {unit}"
    n /= 1024

# Compatible server prefixes
_COMPATIBLE = {'pdrain', 'pixeldrain', 'mega'}
_CANCEL = "__cancel__"  # sentinel quality: user cancelled at the quality prompt

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

    final_target = None

    if 'mega' in server_url.lower() or 'mega' in last_selected_server_name.lower():
      with progress("🔓 Resolving Mega link...", out=out):
        try:
          curr = resolve_url(server_url, timeout=15)
          if ("mega.nz" in curr or "mega.co.nz" in curr) and "#" in curr:
            final_mega_url = curr
          else:
            print_error("Redirect tidak mengarah ke Mega.")
            server_url = None
            continue
        except Exception as e:
          print_error(f"Network Error: {e}")
          time.sleep(3)
          server_url = None
          continue

        try:
          final_mega_url, f_id = _mega_fid(final_mega_url)
          if f_id is None:
            print_error("Gagal extract file ID MEGA.")
            server_url = None
            continue
          stream = megaNZ.resolve_mega_file_stream(final_mega_url, f_id)
          if stream is None:
            server_url = None
            continue
          path, ready, stop, dl_thread, bytes_counter, file_size = stream
        except Exception as e:
          print_error(f"Gagal Streaming: {e}")
          time.sleep(3)
          server_url = None
          continue

      with progress("📥 Buffering stream...", out=out) as up:
        _stall_t0 = time.time()
        _last_bytes = 0
        while not ready.is_set():
          up(bytes_counter[0])  # show real byte progress while waiting
          done = bytes_counter[0]
          if done != _last_bytes:  # still making progress → reset the stall timer
            _last_bytes = done
            _stall_t0 = time.time()
          elif time.time() - _stall_t0 > 60:  # 60s without progress = dead connection
            print_warning("Download stalled (>60s tanpa progress). Cek koneksi atau retry.")
            stop.set()  # kill the old thread before retry
            server_url = None
            break
          time.sleep(0.15)
        if server_url is None:
          continue

      print_step("🚀 Launching mpv player...")
      player.play_with_mpv(path, is_temp_file=True, cleanup=False)
      stop.set()
      dl_thread.join(timeout=10)
      if os.path.exists(path):
        os.remove(path)
      return True, final_mega_url

    else:
      with progress("🌀 Bypassing PixelDrain link...", out=out):
        final_target = pdrain.scrape(server_url)

      if final_target:
        print_step("🚀 Launching mpv player...")
        return player.play_with_mpv(final_target), server_url
      else:
        print_error("Stream tidak tersedia. Pilih resolusi lain.")
        server_url = None
        continue


# Download episode
def _download_episode(episode_title, episode_url, plugin,
                      key_source=None, out=None, quality=None):
  # Download one episode. Returns (quality_label, bytes, reason).
  # quality == _CANCEL when the user bails; quality None + reason on failure;
  # reason None on success.
  # Sanitize filename first
  safe = "".join(c if c.isalnum() or c in " .-_()[]" else "_" for c in episode_title)[:100]
  downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
  os.makedirs(downloads_dir, exist_ok=True)

  # Resolve server URL + pick quality (caller never pre-resolves)
  with progress("🔍 Resolving download links...", out=out):
    dl_links = plugin.downloads(episode_url)

  options = _compatible_servers(dl_links)

  if not options:
    print_warning("No compatible download sources found.")
    return None, 0, "No compatible download sources found."

  labels = [o[0] for o in options]
  if quality is not None and quality in labels:
    sel = labels.index(quality)  # reuse same quality — no prompt
  else:
    sel = select("📥  Select quality & server:", labels,
                 key_source=key_source, out=out, header=banner_header())
    if sel is None:
      return _CANCEL, 0, "Dibatalkan"
    quality = labels[sel]

  server_name, server_url = options[sel]

  if 'mega' in server_url.lower() or (server_name and 'mega' in server_name.lower()):
    # Follow redirect to get final Mega URL
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

      # Wait for full download. `ready` itu penanda streaming (moov awal sudah
      # kebuffer → mpv bisa buka), BUKAN penanda download tuntas — makanya bar
      # pernah nempel 100% di awal. Yang benar: nunggu thread download mati.
      with progress(f"⬇ Downloading {safe}...", total=file_size, out=out) as up:
        t0 = time.time()
        while dl_thread.is_alive():
          if time.time() - t0 > 600:
            print_warning("Download timed out (>10 min).")
            stop.set()
            return None, 0, "Download timed out (>10 min)."
          time.sleep(0.15)
          up(bytes_counter[0])
        up(bytes_counter[0])  # nilai akhir → bar tuntas di ukuran sebenarnya
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

    except Exception as e:
      print_error(f"Download failed: {e}")
      return None, 0, f"Download failed: {e}"

  else:
    # PixelDrain — download stream
    try:
      with progress("🌀 Bypassing PixelDrain link...", out=out):
        final_url = pdrain.scrape(server_url)
      if not final_url:
        print_error("Stream not available.")
        return None, 0, "Stream not available."

      dest = os.path.join(downloads_dir, f"{safe}.mp4")
      size = http_download(final_url, dest, f"⬇ Downloading {safe}...", out=out)
    except Exception as e:
      print_error(f"Download failed: {e}")
      return None, 0, f"Download failed: {e}"

  print_success(f"✅ Downloaded: {dest}")
  return quality, size, None


def _episode_nav(episode_list, plugin, back_label='<< BACK',
                 show_banner=True, anime_url=None, mode='play',
                 key_source=None, out=None):
  # Episode pick → play → post-play loop. Returns 'back' or 'quit'.
  idx = 0
  _last_url = None
  resume_idx = _check_history(anime_url, episode_list) if anime_url else None
  header = banner_header() if show_banner else ()

  while True:
    labels = []
    for i, ep in enumerate(episode_list):
      mark = '▶' if resume_idx == i else ' '
      labels.append(f"{mark} EP{i+1:02d}  —  {ep['title'][:50]}")
    labels.append(f"↩  {back_label}")

    sel = select("▶  Select episode:", labels, search=True, fuzzy=True,
                 key_source=key_source, out=out, header=header,
                 shortcuts={"ctrl-d": "download"})
    if isinstance(sel, str):
      if sel == 'download':
        ep_labels = labels[:-1]
        picks = multiselect("⬇  Pilih episode:", ep_labels, search=True, fuzzy=True,
                            key_source=key_source, out=out, header=header,
                            shortcuts={"ctrl-a": "pilih semua"})
        if picks == "pilih semua":
          picks = set(range(len(ep_labels)))
        if picks:
          print_header("⬇ DOWNLOADING", "⬇")
          quality = None
          ok = fail = 0
          total_bytes = 0
          failed = []
          for i in sorted(picks):
            q, size, reason = _download_episode(episode_list[i]['title'], episode_list[i]['url'], plugin,
                                                key_source=key_source, out=out, quality=quality)
            if q == _CANCEL:
              break  # user cancelled at the quality prompt → stop the queue
            if q:
              quality = q
              ok += 1
              total_bytes += size
            else:
              fail += 1  # episode failed (incl. the first) → noted; queue continues (quality None = re-prompt)
              failed.append((episode_list[i]['title'], reason))
          if ok or fail:
            print_success(f"Queue selesai — {ok} berhasil, {fail} gagal, {_fmt_size(total_bytes)}")
            for title, reason in failed:
              print_warning(f"{title}: {reason}")
            time.sleep(2)  # let the message be read before the list re-renders
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
      cmd = post_choices[cmd_idx]

      if cmd == '▶  NEXT':
        if idx + 1 < len(episode_list):
          idx += 1
          _last_url = None
          continue
        break
      elif cmd == '◀  PREV':
        if idx > 0:
          idx -= 1
          _last_url = None
          continue
        break
      elif cmd == '↺  REPLAY':
        continue
      elif cmd == '⚙  QUALITY':
        _last_url = None
        continue
      else:
        return 'quit'


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
