"""search → select → play."""
import argparse
import importlib
import json
import os
import pkgutil
import time

from . import player
from .ui import (
  console, print_banner, print_header, print_step,
  print_success, print_error, print_warning, print_info, print_separator,
  make_episode_table, make_episode_page, make_postplay_actions, make_footer,
  make_progress_bar, styled_status, make_style, Palette,
)

from . import plugins
import requests
from InquirerPy import inquirer
from .ext import pdrain, megaNZ

_SESSION = requests.Session()

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
def _play_episode(episode_url, plugin, custom_style, server_url=None):
  """Resolve stream and play. Returns (success, server_url)."""
  if server_url is None:
    with console.status(styled_status("🔍 Resolving stream...")):
      dl_links = plugin.downloads(episode_url)

    options = []
    for res, servers in dl_links.items():
      for s_name, s_url in servers.items():
        if any(x in s_name.lower() for x in ['pdrain', 'pixeldrain', 'mega']):
          label = f'[{res}] {s_name}'
          options.append({'name': label, 'value': (label, s_url)})

    if not options:
      print_warning("No compatible servers found.")
      return False, None

    selected = inquirer.select(
      message='📥  Select quality & server:',
      choices=options,
      style=custom_style,
    ).execute()
    if not selected:
      return False, None
    last_selected_server_name, server_url = selected
  else:
    last_selected_server_name = "replay"

  final_target = None
  is_temp = False

  if 'mega' in server_url.lower() or 'mega' in last_selected_server_name.lower():
    final_mega_url = None
    with make_progress_bar() as progress:
      task = progress.add_task(
        f"[{Palette.primary}]🔓 Resolving Mega link...",
        total=None,
      )

      try:
        resp = _SESSION.get(server_url, allow_redirects=True, timeout=15)
        curr = resp.url
        if "mega.nz" in curr and ("#" in curr or "#!" in curr):
          final_mega_url = curr
        else:
          print_error("Redirect tidak mengarah ke Mega.")
          return False, None
      except Exception as e:
        print_error(f"Requests Error: {e}")
        time.sleep(3)
        return False, None

      if not final_mega_url:
        print_error("Timeout: Gagal mendapatkan link Mega.")
        return False, None

      if "#!" in final_mega_url:
        final_mega_url = final_mega_url.replace("#!", "file/").replace("!", "#", 1)

      progress.update(task,
        description=f"[{Palette.highlight}]📥 Buffering stream...")

      # ponytail: sequential > parallel
      try:
        f_id = final_mega_url.split("file/")[1].split("#")[0]
        stream = megaNZ.resolve_mega_file_stream(final_mega_url, f_id, console)
        if stream is None:
          return False, None
        path, ready, stop, dl_thread = stream

        _stall_t0 = time.time()
        while not ready.is_set():
          if time.time() - _stall_t0 > 60:
            print_warning("Buffering timed out (>60s). Check connection or retry.")
            return False, None
          time.sleep(0.15)
      except Exception as e:
        print_error(f"Gagal Streaming: {e}")
        time.sleep(3)
        return False, None

    print_step("🚀 Launching mpv player...")
    player.play_with_mpv(path, is_temp_file=True, cleanup=False)
    stop.set()
    dl_thread.join(timeout=10)
    if os.path.exists(path):
      os.remove(path)
    return True, final_mega_url

  else:
    with make_progress_bar() as progress:
      task = progress.add_task(
        f"[{Palette.secondary}]🌀 Bypassing PixelDrain link...",
        total=None,
      )
      final_target = pdrain.scrape(server_url)

    if final_target:
      print_step("🚀 Launching mpv player...")
      return player.play_with_mpv(final_target, is_temp_file=is_temp), server_url
    else:
      print_error("Stream resolution failed.")
      return False, None


def _episode_nav(episode_list, plugin, custom_style, back_label='<< BACK',
                 show_banner=True, anime_url=None):
  """Episode pick → play → post-play loop. Returns 'back' or 'quit'."""
  idx = 0
  _last_url = None
  page = 0
  page_size = 25
  total_pages = max(1, (len(episode_list) + page_size - 1) // page_size)
  resume_idx = _check_history(anime_url, episode_list) if anime_url else None
  clean = True  # full redraw: clear + banner

  while True:
    if clean:
      if show_banner:
        print_banner()
      clean = False
    console.print(make_episode_page(episode_list, start=page * page_size))

    start = page * page_size
    end = min(start + page_size, len(episode_list))

    ep_choices = []
    if page > 0:
      ep_choices.append({'name': '  ◀  PREV PAGE', 'value': 'prev'})

    # resume button if target not on current page
    if resume_idx is not None and (resume_idx < start or resume_idx >= end):
      ep_choices.append({
        'name': f'  ⏺  RESUME  EP{resume_idx+1:02d}',
        'value': resume_idx,
      })

    for i in range(start, end):
      prefix = '  ▶' if resume_idx == i else '   '
      ep_choices.append({
        'name': f'{prefix} EP{i+1:02d}  —  {episode_list[i]["title"][:50]}',
        'value': i,
      })

    if page + 1 < total_pages:
      next_end = min(end + page_size, len(episode_list))
      ep_choices.append({
        'name': f'  ▶  NEXT PAGE (EP{end+1}–{next_end})',
        'value': 'next',
      })

    ep_choices.append({'name': f'  ↩  {back_label}', 'value': 'back'})

    fz = inquirer.fuzzy(
      message='▶  Select episode:',
      choices=ep_choices,
      default=idx if start <= idx < end else 0,
      style=custom_style,
      qmark="",
    )
    @fz.register_kb('left')
    def _(event):
      event.app.exit(result='__prev__')
    @fz.register_kb('right')
    def _(event):
      event.app.exit(result='__next__')
    selected = fz.execute()

    if selected is None or selected == 'back':
      from .plugins._base import cache_clear
      cache_clear()
      return 'back'

    if selected in ('prev', '__prev__'):
      page -= 1
      continue
    if selected in ('next', '__next__'):
      page += 1
      continue

    idx = selected
    _last_url = None

    while True:
      print_header("🎬 NOW PLAYING", "▶")
      ok, url = _play_episode(
        episode_list[idx]['url'], plugin, custom_style, server_url=_last_url)
      if not ok:
        time.sleep(2)
        clean = True
        break
      if anime_url:
        _save_history(anime_url, episode_list[idx]['url'])
      _last_url = url

      print_separator()

      post_choices = make_postplay_actions(idx, len(episode_list))
      cmd = inquirer.select(
        message="🎮  Command:",
        choices=post_choices,
        style=custom_style,
        qmark="",
      ).execute()

      if cmd == '▶  NEXT':
        if idx + 1 < len(episode_list):
          idx += 1
          _last_url = None
          continue
        clean = True
        break
      elif cmd == '◀  PREV':
        if idx > 0:
          idx -= 1
          _last_url = None
          continue
        clean = True
        break
      elif cmd == '↺  REPLAY':
        continue
      elif cmd == '⚙  QUALITY':
        _last_url = None
        continue
      else:
        return 'quit'


def _tui_loop():
  p_name = 'otakudesu'
  _last_plugin_name = None
  _plugin = None
  custom_style = make_style()
  available_providers = [
    m.name for m in pkgutil.iter_modules(plugins.__path__)
    if not m.name.startswith('_')
  ]

  while True:
    print_banner()

    if p_name != _last_plugin_name:
      _plugin = importlib.import_module(f'indonime.plugins.{p_name}')
      _last_plugin_name = p_name

    is_switching = False
    try:
      prompt = inquirer.text(
        message='🔍  Search anime:',
        qmark='',
        instruction='[alt+p] switch provider  [esc] quit',
        style=custom_style,
        validate=lambda x: True if is_switching else len(x) > 0,
      )
      @prompt.register_kb('alt-p')
      def _(event):
        nonlocal is_switching
        is_switching = True
        event.app.exit(result='/switch')
      @prompt.register_kb('escape')
      def _(event):
        event.app.exit(result=None)
      result = prompt.execute()
    except KeyboardInterrupt:
      break

    if result == '/switch':
      new_p = inquirer.select(
        message='📡  Select provider:',
        choices=available_providers,
        qmark='',
        style=custom_style,
      ).execute()
      if new_p:
        p_name = new_p
      continue
    if not result:
      break

    print_header("🔎 SEARCHING", "🔎")
    with console.status(styled_status(f'Searching for "{result}"...')):
      results = _plugin.search_anime(result)

    if not results:
      print_warning("No results found.")
      time.sleep(2)
      continue

    choices = [item['title'] for item in results] + ['-- ABORT --']
    selected_title = inquirer.fuzzy(
      message='📺  Select title:',
      choices=choices,
      style=custom_style,
    ).execute()

    if selected_title == '-- ABORT --' or not selected_title:
      continue

    selected_url = next(
      item['url'] for item in results
      if item['title'] == selected_title
    )

    print_header("📋 EPISODES", "🎬")
    with console.status(styled_status("Fetching episode list...")):
      episode_list = _plugin.episodes(selected_url)

    if not episode_list:
      print_warning("No episodes found.")
      time.sleep(2)
      continue

    if _episode_nav(
      episode_list, _plugin, custom_style,
      back_label='<< BACK TO SEARCH', show_banner=True,
      anime_url=selected_url,
    ) == 'quit':
      break

  print_banner()
  make_footer()
  print_success("Thanks for using Indonime! ~ Sayonara ~")


def _search_mode(query, provider='otakudesu'):
  """One-shot search → play → exit."""
  custom_style = make_style()
  print_banner()

  try:
    plugin = importlib.import_module(f'indonime.plugins.{provider}')
  except Exception as e:
    print_error(f"Plugin error: {e}")
    input('[Press Enter]')
    return

  print_header("🔎 SEARCHING", "🔎")
  with console.status(styled_status(f'Searching for "{query}"...')):
    results = plugin.search_anime(query)

  if not results:
    print_warning("No results found.")
    input('[Press Enter]')
    return

  choices = [item['title'] for item in results] + ['-- ABORT --']
  selected_title = inquirer.fuzzy(
    message='📺  Select title:',
    choices=choices,
    style=custom_style,
  ).execute()

  if selected_title == '-- ABORT --' or not selected_title:
    return

  selected_url = next(
    item['url'] for item in results
    if item['title'] == selected_title
  )

  print_header("📋 EPISODES", "🎬")
  with console.status(styled_status("Fetching episode list...")):
    episode_list = plugin.episodes(selected_url)

  if not episode_list:
    print_warning("No episodes found.")
    input('[Press Enter]')
    return

  _episode_nav(
    episode_list, plugin, custom_style,
    back_label='<< QUIT', show_banner=False,
    anime_url=selected_url,
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
    '-p', '--provider', default='otakudesu',
    choices=['otakudesu', 'anoboy'],
    help='Provider (default: otakudesu)'
  )
  args = parser.parse_args()

  if args.mode == 'search' and args.query:
    _search_mode(' '.join(args.query), args.provider)
  else:
    _tui_loop()
