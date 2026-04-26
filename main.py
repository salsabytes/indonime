import os
import importlib
import subprocess
import time
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.utils import get_style
from rich.console import Console
from rich.panel import Panel
from playwright.sync_api import sync_playwright
from ext import pdrain

console = Console()
current_mpv_process = None

def print_banner():
  console.clear()
  console.print(r"""[bold cyan]
  ___           _             _                 
 |_ _|_ __   __| | ___  _ __ (_)_ __ ___   ___  
  | || '_ \ / _` |/ _ \| '_ \| | '_ ` _ \ / _ \ 
  | || | | | (_| | (_) | | | | | | | | | |  __/ 
 |___|_| |_|\__,_|\___/|_| |_|_|_| |_| |_|\___|
                
       [/bold cyan][italic]Subtitle Indonesia Anime Searcher[/italic]
  """)

def play_with_mpv(direct_url):
  global current_mpv_process
  if current_mpv_process and current_mpv_process.poll() is None:
    try:
      current_mpv_process.terminate() 
    except:
      pass
  base_path = os.path.dirname(os.path.abspath(__file__))
  path_ke_mpv = os.path.join(base_path, 'mpv', 'mpv.exe')
  if not os.path.exists(path_ke_mpv):
    path_ke_mpv = os.path.join(base_path, 'mpv.exe')
  if not os.path.exists(path_ke_mpv):
    check_system = subprocess.run(['where', 'mpv'], capture_output=True, text=True)
    if check_system.returncode == 0:
      path_ke_mpv = 'mpv'
    else:
      return False, "mpv.exe tidak ditemukan."
  mpv_args = [
    path_ke_mpv, direct_url,
    '--title=Indonime Player - Naz Edition',
    '--ontop', '--no-border', '--force-window=yes',
    '--cache=yes', '--demuxer-max-bytes=10M',
    '--demuxer-readahead-secs=5', '--network-timeout=15',
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
  ]
  try:
    current_mpv_process = subprocess.Popen(mpv_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    return True, None
  except Exception as e:
    return False, str(e)

def main():
  global current_mpv_process
  p_name = 'otakudesu'
  custom_style = get_style({
    'questionmark': '#5fafd7 bold',
    'question': '#d1d1d1',
    'instruction': '#454545 italic',
    'pointer': '#5fafd7 bold',
    'answere': '#5fafd7',
  }, style_override=False)
  while True:
    print_banner()
    available_providers = [f.replace('.py', '') for f in os.listdir('plugins') if f.endswith('.py') and not f.startswith('__')]
    label_rich = f'[bold cyan]❮ {p_name.upper()} ❯[/bold cyan]'
    try:
      plugin = importlib.import_module(f'plugins.{p_name}')
      importlib.reload(plugin)
    except Exception as e:
      console.print(f'[red]Error Plugin: {e}[/red]')
      p_name = 'otakudesu'
      time.sleep(2)
      continue
    is_switching = False
    try:
      prompt = inquirer.text(
        message='Search Query:',
        qmark='[SCAN]',
        instruction='[ALT+P to Switch]',
        style=custom_style,
        validate=lambda x: True if is_switching else len(x) > 0,
        invalid_message='Input required.'
      )
      @prompt.register_kb('alt-p')
      def _(event):
        nonlocal is_switching
        is_switching = True
        event.app.exit(result='/switch')
      result = prompt.execute()
    except KeyboardInterrupt:
      if current_mpv_process and current_mpv_process.poll() is None:
        current_mpv_process.terminate()
      console.print(f'\n[yellow]Shutdown sequence initiated. Goodbye, Naz![/yellow]')
      break
    if result == '/switch':
      new_p = inquirer.select(message='Select Provider:', choices=available_providers, qmark='[PROV]', style=custom_style).execute()
      if new_p: p_name = new_p
      continue
    if not result: break
    query_text = result
    with console.status(f'{label_rich} [bold green]Searching for "{query_text}"...[/bold green]'):
      try:
        results = plugin.search_anime(query_text)
      except Exception as e:
        console.print(f'[red]Search Failed: {e}[/red]')
        time.sleep(2)
        continue
    if not results:
      console.print(f'{label_rich} [yellow]No results found.[/yellow]')
      time.sleep(2)
      continue
    print_banner()
    choices = [item['title'] for item in results] + ['-- ABORT --']
    selected_title = inquirer.fuzzy(message='Select Title:', qmark='[LIST]', choices=choices, style=custom_style).execute()
    if selected_title == '-- ABORT --' or selected_title is None: continue
    selected_url = next(item['url'] for item in results if item['title'] == selected_title)
    print_banner()
    with console.status(f'{label_rich} [bold blue]Fetching metadata...[/bold blue]'):
      episode_list = plugin.episodes(selected_url)
    current_ep_idx = 0
    last_selected_server_name = None 
    while True:
      print_banner()
      ep_choices = [{'name': f'EP {str(i+1).zfill(2)} > {ep["title"]}', 'value': i} for i, ep in enumerate(episode_list)]
      ep_choices.append({'name': '<< BACK TO SEARCH', 'value': 'back'})
      selected_idx = inquirer.select(
        message='Select Episode:',
        qmark='[EP]',
        choices=ep_choices,
        default=current_ep_idx,
        style=custom_style
      ).execute()
      if selected_idx == 'back' or selected_idx is None: break
      current_ep_idx = selected_idx
      while True:
        with console.status(f'{label_rich} [bold cyan]Resolving stream (EP {str(current_ep_idx+1).zfill(2)})...[/bold cyan]'):
          dl_links = plugin.downloads(episode_list[current_ep_idx]['url'])
        if not dl_links:
          console.print(f'[red]✘ Stream resolution failed.[/red]')
          time.sleep(2)
          break
        options = []
        for res, servers in dl_links.items():
          for s_name, s_url in servers.items():
            if 'pdrain' in s_name.lower() or 'pixeldrain' in s_name.lower():
              options.append({'name': f'[{res}] {s_name}', 'value': s_url, 'raw_name': f'[{res}] {s_name}'})
        if not options:
          console.print(f'[yellow]⚠ No compatible servers found (PDrain).[/yellow]')
          time.sleep(2)
          break
        server_url = None
        if last_selected_server_name:
          match = next((opt for opt in options if opt['raw_name'] == last_selected_server_name), None)
          if match:
            server_url = match['value']
            console.print(f'[blue]» Auto-selecting: {last_selected_server_name}[/blue]')
        if not server_url:
          selected_opt = inquirer.select(
            message=f'Target: EP {str(current_ep_idx+1).zfill(2)}...',
            choices=options,
            qmark='[SVR]',
            style=custom_style
          ).execute()
          if selected_opt is None: break
          server_url = selected_opt
          last_selected_server_name = next(opt['raw_name'] for opt in options if opt['value'] == server_url)
        with console.status(f'[magenta]Decrypting links...', spinner='dots') as status:
          final_link = None
          current_url = server_url
          if any(x in current_url for x in ['desustream.com', 'otakudesu.cloud']):
            try:
              with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(current_url, wait_until='domcontentloaded', timeout=15000)
                time.sleep(2)
                current_url = page.url
                browser.close()
            except: pass
          final_link = pdrain.scrape(current_url)
          if final_link and any(kw in final_link.lower() for kw in ['.mp4', 'download', '.mkv', 'api']):
            status.update(f'[cyan]Launching MPV...')
            play_with_mpv(final_link)
            console.print(f'[green]✔ Process started successfully.[/green]')
          else:
            console.print(f'[red]✘ Failed to extract direct link.[/red]')
            last_selected_server_name = None 
            time.sleep(2)
            break
        dynamic_choices = []
        if current_ep_idx + 1 < len(episode_list):
          dynamic_choices.append({'name': '▶ NEXT EPISODE', 'value': 'next'})
        if current_ep_idx > 0:
          dynamic_choices.append({'name': '◀ PREVIOUS EPISODE', 'value': 'prev'})
        dynamic_choices.extend([
          {'name': '↺ REPLAY', 'value': 'replay'},
          {'name': '⚙ CHANGE QUALITY', 'value': 'quality'},
          {'name': '☰ SELECT EPISODE', 'value': 'select'},
          {'name': '✖ ABORT SESSION', 'value': 'quit'},
        ])
        console.print(f"\n[bold cyan]─── PLAYER CONTROL [EP {str(current_ep_idx+1).zfill(2)}] ───[/bold cyan]")
        post_play = inquirer.select(
          message="Execute Command:",
          choices=dynamic_choices,
          qmark='[CMD]',
          style=custom_style
        ).execute()
        if post_play == 'next':
          current_ep_idx += 1
          print_banner()
          continue 
        elif post_play == 'prev':
          current_ep_idx -= 1
          print_banner()
          continue
        elif post_play == 'replay':
          print_banner()
          continue 
        elif post_play == 'quality':
          last_selected_server_name = None 
          print_banner()
          continue 
        elif post_play == 'select':
          break 
        elif post_play == 'quit' or post_play is None:
          current_ep_idx = -1 
          break
      if current_ep_idx == -1: break

if __name__ == '__main__':
  main()