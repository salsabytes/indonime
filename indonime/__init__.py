import argparse
import importlib
import pkgutil
import time

from . import player
from .ui import console, print_banner, make_style

import plugins
import requests
from InquirerPy import inquirer
from ext import pdrain, megaNZ


def _play_episode(episode_url, plugin, custom_style):
  """Resolve stream and play. Returns True if played successfully."""
  with console.status(f'[bold cyan]Resolving stream...[/bold cyan]'):
    dl_links = plugin.downloads(episode_url)

  options = []
  for res, servers in dl_links.items():
    for s_name, s_url in servers.items():
      if any(x in s_name.lower() for x in ['pdrain', 'pixeldrain', 'mega']):
        options.append({'name': f'[{res}] {s_name}', 'value': s_url, 'raw_name': f'[{res}] {s_name}'})

  if not options:
    console.print(f'[yellow]⚠ No compatible servers found.[/yellow]')
    return False

  selected_opt = inquirer.select(message='Select Quality...', choices=options, style=custom_style).execute()
  if not selected_opt:
    return False
  server_url = selected_opt
  last_selected_server_name = next(opt['raw_name'] for opt in options if opt['value'] == server_url)

  final_target = None
  is_temp = False

  if 'mega' in last_selected_server_name.lower():
    final_mega_url = None
    with console.status(f"[bold yellow]Resolving Mega Link...[/bold yellow]"):
      try:
        resp = requests.get(server_url, allow_redirects=True, timeout=15)
        curr = resp.url
        if "mega.nz" in curr and ("#" in curr or "#!" in curr):
          final_mega_url = curr
        else:
          console.print(f"[red]✘ Redirect tidak mengarah ke Mega.[/red]")
      except Exception as e:
        console.print(f"[red]✘ Requests Error: {e}[/red]")
        time.sleep(3)

    if final_mega_url:
      if "#!" in final_mega_url:
        final_mega_url = final_mega_url.replace("#!", "file/").replace("!", "#", 1)
      try:
        f_id = final_mega_url.split("file/")[1].split("#")[0]
        final_target = megaNZ.resolve_mega_file(final_mega_url, f_id, console)
        is_temp = True
      except Exception as e:
        console.print(f"[red]✘ Gagal Dekripsi: {e}[/red]")
        time.sleep(3)
        return False
    else:
      console.print("[red]✘ Timeout: Gagal mendapatkan link Mega.[/red]")
      return False
  else:
    final_target = pdrain.scrape(server_url)

  if final_target:
    return player.play_with_mpv(final_target, is_temp_file=is_temp)
  else:
    console.print(f'[red]✘ Stream resolution failed.[/red]')
    return False


def _episode_nav(episode_list, plugin, custom_style, back_label='<< BACK', show_banner=True, show_quality=True):
  """Episode pick -> play -> post-play. Returns 'back' or 'quit'."""
  idx = 0
  while True:
    if show_banner:
      print_banner()

    ep_choices = [{'name': f'EP {str(i+1).zfill(2)} > {ep["title"]}', 'value': i} for i, ep in enumerate(episode_list)]
    ep_choices.append({'name': back_label, 'value': 'back'})

    selected = inquirer.select(message='Select Episode:', choices=ep_choices, default=idx, style=custom_style).execute()
    if selected == 'back' or selected is None:
      return 'back'
    idx = selected

    if not _play_episode(episode_list[idx]['url'], plugin, custom_style):
      time.sleep(2)
      return 'back'

    post_choices = ['▶ NEXT', '◀ PREV', '↺ REPLAY', '✖ QUIT']
    if show_quality:
      post_choices.insert(-1, '⚙ QUALITY')
    cmd = inquirer.select(message="Command:", choices=post_choices, style=custom_style).execute()

    if cmd == '▶ NEXT': idx += 1
    elif cmd == '◀ PREV': idx -= 1
    elif cmd in ('↺ REPLAY', '⚙ QUALITY'): continue
    else: return 'quit'


def _tui_loop():
  p_name = 'otakudesu'
  custom_style = make_style()

  while True:
    print_banner()
    available_providers = [module.name for module in pkgutil.iter_modules(plugins.__path__)]

    try:
      plugin = importlib.import_module(f'plugins.{p_name}')
      importlib.reload(plugin)
    except Exception as e:
      console.print(f'[red]Error Plugin: {e}[/red]'); time.sleep(2); continue

    is_switching = False
    try:
      prompt = inquirer.text(message='Search Query:', qmark='[SCAN]', instruction='[ALT+P to Switch]', style=custom_style, validate=lambda x: True if is_switching else len(x) > 0)
      @prompt.register_kb('alt-p')
      def _(event):
        nonlocal is_switching
        is_switching = True
        event.app.exit(result='/switch')
      result = prompt.execute()
    except KeyboardInterrupt: break

    if result == '/switch':
      new_p = inquirer.select(message='Select Provider:', choices=available_providers, qmark='[PROV]', style=custom_style).execute()
      if new_p: p_name = new_p
      continue
    if not result: break

    with console.status(f'[bold green]Searching for "{result}"...[/bold green]'):
      results = plugin.search_anime(result)

    if not results:
      console.print(f'[yellow]No results found.[/yellow]'); time.sleep(2); continue

    choices = [item['title'] for item in results] + ['-- ABORT --']
    selected_title = inquirer.fuzzy(message='Select Title:', choices=choices, style=custom_style).execute()
    if selected_title == '-- ABORT --' or not selected_title: continue

    selected_url = next(item['url'] for item in results if item['title'] == selected_title)
    episode_list = plugin.episodes(selected_url)

    if _episode_nav(episode_list, plugin, custom_style, back_label='<< BACK TO SEARCH', show_banner=True, show_quality=True) == 'quit':
      break


def _search_mode(query, provider='otakudesu'):
  """One-shot search -> play -> exit."""
  custom_style = make_style()

  try:
    plugin = importlib.import_module(f'plugins.{provider}')
    importlib.reload(plugin)
  except Exception as e:
    console.print(f'[red]Error Plugin: {e}[/red]')
    input('[Press Enter]')
    return

  with console.status(f'[bold green]Searching for "{query}"...[/bold green]'):
    results = plugin.search_anime(query)

  if not results:
    console.print(f'[yellow]No results found.[/yellow]')
    input('[Press Enter]')
    return

  choices = [item['title'] for item in results] + ['-- ABORT --']
  selected_title = inquirer.fuzzy(message='Select Title:', choices=choices, style=custom_style).execute()
  if selected_title == '-- ABORT --' or not selected_title:
    return

  selected_url = next(item['url'] for item in results if item['title'] == selected_title)
  episode_list = plugin.episodes(selected_url)

  _episode_nav(episode_list, plugin, custom_style, back_label='<< QUIT', show_banner=False, show_quality=False)

  if player.current_mpv_process and player.current_mpv_process.poll() is None:
    player.current_mpv_process.wait()


def main():
  parser = argparse.ArgumentParser(description='Indonime - Subtitle Indonesia Anime Searcher')
  parser.add_argument('mode', nargs='?', default='tui',
                      help='Mode: tui (interactive, default) or search <query>')
  parser.add_argument('query', nargs='*', help='Search query')
  parser.add_argument('-p', '--provider', default='otakudesu',
                      choices=['otakudesu', 'anoboy'], help='Provider (default: otakudesu)')
  args = parser.parse_args()

  if args.mode == 'search' and args.query:
    _search_mode(' '.join(args.query), args.provider)
  else:
    _tui_loop()
