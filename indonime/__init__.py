"""search → select → play — tuiko-powered (no rich / InquirerPy / pyfiglet)."""
import argparse
import importlib
import json
import os
import pkgutil
import shutil
import time

from . import player
from .ui import (
  banner_header, make_progress_bar, print_banner, print_header, print_step,
  print_success, print_error, print_warning, print_separator,
  make_postplay_actions, make_footer,
)

from . import plugins
from tuiko import prompt, select, session
from .ext import pdrain, megaNZ
from .ext.megaNZ import _mega_fid, _mega_key
from .plugins._base import http_stream, resolve_url

# ── Compatible server prefixes ────────────────
_COMPATIBLE = {'pdrain', 'pixeldrain', 'mega'}

def _compatible_servers(dl_links):
  """Flatten {quality: {server: url}} → [(label, url)] for compatible servers."""
  options = []
  for res, servers in dl_links.items():
    for s_name, s_url in servers.items():
      if any(x in s_name.lower() for x in _COMPATIBLE):
        options.append((f'[{res}] {s_name}', s_url))
  return options


# ── History ─────────────────────────────────────
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

# ── Play episode ────────────────────────────────
def _play_episode(episode_url, plugin, server_url=None, episode_title=None,
                  key_source=None, out=None):
  """Resolve stream and play. Returns (success, server_url)."""
  while True:
    if server_url is None:
      with make_progress_bar() as p:
        p.add_task("🔍 Resolving stream...", total=None)
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

      # After quality selection, offer Play or Download
      if episode_title:
        mode_idx = select("📥  What to do with " + episode_title[:50],
                          [" ▶  Play", " ⬇  Download"],
                          key_source=key_source, out=out, header=banner_header())
        if mode_idx is None:
          return False, None
        mode = 'download' if mode_idx == 1 else 'play'
      else:
        mode = 'play'

      if mode == 'download':
        _download_episode(episode_title, episode_url, plugin,
                          server_url=server_url, server_name=last_selected_server_name,
                          key_source=key_source, out=out)
        return True, server_url
    else:
      last_selected_server_name = "replay"

    final_target = None

    if 'mega' in server_url.lower() or 'mega' in last_selected_server_name.lower():
      with make_progress_bar() as p:
        p.add_task("🔓 Resolving Mega link...", total=None)
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

        if not final_mega_url:
          print_error("Timeout: Gagal mendapatkan link Mega.")
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

      with make_progress_bar() as p:
        p.add_task("📥 Buffering stream...", total=None)
        _stall_t0 = time.time()
        while not ready.is_set():
          if time.time() - _stall_t0 > 60:
            print_warning("Buffering timed out (>60s). Check connection or retry.")
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
      with make_progress_bar() as p:
        p.add_task("🌀 Bypassing PixelDrain link...", total=None)
        final_target = pdrain.scrape(server_url)

      if final_target:
        print_step("🚀 Launching mpv player...")
        return player.play_with_mpv(final_target), server_url
      else:
        print_error("Stream tidak tersedia. Pilih resolusi lain.")
        server_url = None
        continue


# ── Download episode ────────────────────────────
def _download_episode(episode_title, episode_url, plugin, server_url=None, server_name=None,
                      key_source=None, out=None):
  # Sanitize filename first
  safe = "".join(c if c.isalnum() or c in " .-_()[]" else "_" for c in episode_title)[:100]
  downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
  os.makedirs(downloads_dir, exist_ok=True)

  # Resolve server URL if not pre-resolved
  if server_url is None:
    with make_progress_bar() as p:
      p.add_task("🔍 Resolving download links...", total=None)
      dl_links = plugin.downloads(episode_url)

    options = _compatible_servers(dl_links)

    if not options:
      print_warning("No compatible download sources found.")
      return

    labels = [o[0] for o in options]
    sel = select("📥  Select quality & server:", labels,
                 key_source=key_source, out=out, header=banner_header())
    if sel is None:
      return

    server_name, server_url = options[sel]

  if 'mega' in server_url.lower() or (server_name and 'mega' in server_name.lower()):
    # Follow redirect to get final Mega URL
    try:
      curr = resolve_url(server_url, timeout=15)
    except Exception as e:
      print_error(f"Network Error: {e}")
      return

    # Extract key + file_id — try server_url first, then redirect URL
    megakey_raw = _mega_key(server_url) or _mega_key(curr)
    _, f_id = _mega_fid(curr)
    if not f_id:
      _, f_id = _mega_fid(server_url)
    if not f_id:
      print_error("Could not extract Mega file ID.")
      return

    # Reconstruct clean URL — host gak dipakai downstream, cuma #key fragment yang penting
    mega_url = f"https://mega.nz/file/{f_id}#{megakey_raw}"

    try:
      stream = megaNZ.resolve_mega_file_stream(mega_url, f_id)
      if stream is None:
        return
      path, ready, stop, dl_thread, bytes_counter, file_size = stream

      # Wait for full download
      with make_progress_bar(show_size=True) as p:
        task = p.add_task(f"⬇ Downloading {safe}...", total=file_size)
        while not ready.is_set():
          time.sleep(0.15)
          p.update(task, completed=bytes_counter[0])
        p.update(task, completed=file_size)
        dl_thread.join(timeout=600)
        if dl_thread.is_alive():
          print_warning("Download timed out (>10 min).")
          stop.set()
          return

      # Copy to Downloads
      dest = os.path.join(downloads_dir, f"{safe}.mp4")
      shutil.copy2(path, dest)
      if os.path.exists(path):
        os.remove(path)

    except Exception as e:
      print_error(f"Download failed: {e}")
      return

  else:
    # PixelDrain — download stream
    try:
      with make_progress_bar() as p:
        p.add_task("🌀 Bypassing PixelDrain link...", total=None)
        final_url = pdrain.scrape(server_url)
      if not final_url:
        print_error("Stream not available.")
        return

      dest = os.path.join(downloads_dir, f"{safe}.mp4")
      with http_stream(final_url, timeout=30) as resp:
        total = int(resp.headers.get('Content-Length', 0))

        with make_progress_bar(show_size=True) as p:
          task = p.add_task(f"⬇ Downloading {safe}...", total=total or None)
          with open(dest, 'wb') as f:
            while True:
              chunk = resp.read(64 * 1024)
              if not chunk:
                break
              f.write(chunk)
              if total:
                p.update(task, advance=len(chunk))
    except Exception as e:
      print_error(f"Download failed: {e}")
      return

  print_success(f"✅ Downloaded: {dest}")


def _episode_nav(episode_list, plugin, back_label='<< BACK',
                 show_banner=True, anime_url=None, mode='play',
                 key_source=None, out=None):
  """Episode pick → play → post-play loop. Returns 'back' or 'quit'."""
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
                 key_source=key_source, out=out, header=header)
    if sel is None or sel == len(labels) - 1:
      from .plugins._base import cache_clear
      cache_clear()
      return 'back'

    idx = sel
    if mode == 'download':
      _download_episode(episode_list[idx]['title'], episode_list[idx]['url'], plugin,
                        key_source=key_source, out=out)
      time.sleep(2)
      return 'back'
    _last_url = None

    while True:
      print_header("🎬 NOW PLAYING", "▶")
      ok, url = _play_episode(
        episode_list[idx]['url'], plugin, server_url=_last_url,
        episode_title=episode_list[idx]['title'],
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


# ── Customizable shortcuts (search screen) ──
# Map key → action. Actions handled in _tui_loop: 'provider', 'quit', 'abort'.
# Keep keys non-printable (ctrl-...) so they don't hijack search-box typing.
# ctrl-b because VS Code's terminal strips Alt and swallows Ctrl+P/Q (Quick
# Open / Quick Access); b isn't intercepted by any terminal. Quit needs no
# shortcut — escape / the ABORT sentinel already quit.
_SHORTCUTS = {
  "ctrl-b": "provider",
}

# ── Catalog cache ───────────────────────────
_CATALOG_CACHE = {}  # plugin module name -> (ts, catalog)

def _get_catalog(plugin):
  """Catalog with a module-level cache that survives cache_clear() (no 845KB refetch on back)."""
  name = getattr(plugin, '__name__', type(plugin).__name__)
  now = time.time()
  hit = _CATALOG_CACHE.get(name)
  if hit and now - hit[0] < 600:
    return hit[1]
  with make_progress_bar() as p:
    p.add_task("Loading catalog...", total=None)
    catalog = plugin.list_all()
  if catalog:
    _CATALOG_CACHE[name] = (now, catalog)
  return catalog

# ── Search and select helper ──────────────
def _catalog_select(plugin, key_source=None, out=None, shortcuts=None):
  """Live fuzzy search over the full catalog — no Enter needed.

  Returns (url, episode_list), a shortcut action string, 'abort' when the
  user bails (escape / ABORT sentinel), or None when nothing is found.
  """
  print_header("🔎 SEARCHING", "🔎")
  catalog = _get_catalog(plugin)

  if not catalog:
    return None

  titles = [item['title'] for item in catalog] + ['↩  -- ABORT --']
  sel = select("📺  Cari anime:", titles, search=True, fuzzy=True,
               key_source=key_source, out=out, header=banner_header(),
               shortcuts=shortcuts)

  if isinstance(sel, str):
    return sel  # shortcut action (e.g. 'provider', 'quit')
  if sel is None or sel == len(titles) - 1:
    return 'abort'  # user bailed (escape / ABORT sentinel) — back to search silently

  selected = catalog[sel]
  with make_progress_bar() as p:
    p.add_task("Fetching episode list...", total=None)
    episode_list = plugin.episodes(selected['url'])

  if not episode_list:
    return None

  return selected['url'], episode_list

def _search_and_select(plugin, query, key_source=None, out=None, shortcuts=None):
  """Search → pick title → fetch episode list.

  Returns (url, episode_list), a shortcut action string ('provider'/'quit'/...),
  'abort' when the user bails, or None when nothing is found.

  query=None → live fuzzy search over the cached full catalog (TUI mode).
  query given → network search (one-shot CLI mode).
  """
  if query is None:
    return _catalog_select(plugin, key_source=key_source, out=out, shortcuts=shortcuts)

  print_header("🔎 SEARCHING", "🔎")
  with make_progress_bar() as p:
    p.add_task("Searching...", total=None)
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

  with make_progress_bar() as p:
    p.add_task("Fetching episode list...", total=None)
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
  """One-shot search → play or download → exit."""
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
