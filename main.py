import os
import sys
import importlib
import subprocess
import time
from InquirerPy import inquirer
from InquirerPy.utils import get_style
from rich.console import Console
from playwright.sync_api import sync_playwright
from ext import pdrain, megaNZ

console = Console()
current_mpv_process = None

def print_banner():
  console.clear()
  console.print(r"""[bold cyan]
 ___           _             _                 
|_ _|_ __    __| | ___  _ __ (_)_ __ ___  ___  
 | || '_ \  / _` |/ _ \| '_ \| | '_ ` _ \/ _ \ 
 | || | | | (_| | (_) | | | | | | | | | |  __/ 
|___|_| |_|\__,_|\___/|_| |_|_|_| |_| |_|\___|
                
    [/bold cyan][italic]Subtitle Indonesia Anime Searcher[/italic]
  """)

def play_with_mpv(video_target, is_temp_file=False):
  global current_mpv_process
  if current_mpv_process and current_mpv_process.poll() is None:
    try: current_mpv_process.terminate()
    except: pass
      
  is_exe = getattr(sys, 'frozen', False) or '__compiled__' in globals()
  
  if is_exe:
    base_dir = os.path.dirname(sys.executable)
  else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
  path_ke_mpv = os.path.join(base_dir, 'mpv', 'mpv.exe')

  if not os.path.exists(path_ke_mpv):
    console.print(f"[red]✘ Error: mpv.exe tidak ketemu di: {path_ke_mpv}[/red]")
    return False

  mpv_args = [path_ke_mpv, video_target, '--title=Indonime Player', '--force-window=yes', '--ontop']
  
  try:
    if is_temp_file:
      subprocess.run(mpv_args)
      if os.path.exists(video_target): os.remove(video_target)
    else:
      current_mpv_process = subprocess.Popen(mpv_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    return True
  except Exception as e:
    console.print(f"[red]✘ Gagal: {e}[/red]")
    return False

def main():
  global current_mpv_process
  p_name = 'otakudesu'
  is_exe = getattr(sys, 'frozen', False) or '__compiled__' in globals()
  if is_exe:
    base_dir = os.path.dirname(sys.executable)
  else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
  plugins_path = os.path.join(base_dir, 'plugins')
  custom_style = get_style({
    'questionmark': '#5fafd7 bold',
    'question': '#d1d1d1',
    'instruction': '#454545 italic',
    'pointer': '#5fafd7 bold',
    'answere': '#5fafd7',
  }, style_override=False)

  while True:
    print_banner()
    if not os.path.exists(plugins_path):
      console.print(f'[red]Error: Folder plugins not found: {plugins_path}[/red]')
      break
    
    available_providers = [f.replace('.py', '') for f in os.listdir(plugins_path) if f.endswith('.py') and not f.startswith('__')]
    
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
    current_ep_idx = 0

    while True:
      print_banner()
      ep_choices = [{'name': f'EP {str(i+1).zfill(2)} > {ep["title"]}', 'value': i} for i, ep in enumerate(episode_list)]
      ep_choices.append({'name': '<< BACK TO SEARCH', 'value': 'back'})
      
      selected_idx = inquirer.select(message='Select Episode:', choices=ep_choices, default=current_ep_idx, style=custom_style).execute()
      if selected_idx == 'back' or selected_idx is None: break
      current_ep_idx = selected_idx

      while True:
        with console.status(f'[bold cyan]Resolving stream...[/bold cyan]'):
          dl_links = plugin.downloads(episode_list[current_ep_idx]['url'])

        options = []
        for res, servers in dl_links.items():
          for s_name, s_url in servers.items():
            if any(x in s_name.lower() for x in ['pdrain', 'pixeldrain', 'mega']):
              options.append({'name': f'[{res}] {s_name}', 'value': s_url, 'raw_name': f'[{res}] {s_name}'})

        if not options:
          console.print(f'[yellow]⚠ No compatible servers found.[/yellow]'); time.sleep(2); break

        selected_opt = inquirer.select(message=f'Target: EP {str(current_ep_idx+1).zfill(2)}...', choices=options, style=custom_style).execute()
        if not selected_opt: break
        server_url = selected_opt
        last_selected_server_name = next(opt['raw_name'] for opt in options if opt['value'] == server_url)

        final_target = None
        is_temp = False

        if 'mega' in last_selected_server_name.lower():
          final_mega_url = None
          with console.status(f"[bold yellow]Resolving Mega Link...[/bold yellow]"):
            try:
              with sync_playwright() as p:
                browsers = [
                  {"channel": "chrome"}, 
                  {"channel": "msedge"}, 
                  {"channel": "chrome-beta"},
                ]
                browser = None
                for target in browsers:
                  try:
                    browser = p.chromium.launch(headless=True, **target)
                    if browser: break
                  except:
                    continue

                if not browser:
                  try:
                    browser = p.firefox.launch(headless=True)
                  except:
                    console.print("[red]✘ Error: Cannot find Chrome, Edge, or Firefox.[/red]")
                    break
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
                page = context.new_page()
                page.goto(server_url, wait_until='commit')
                start_time = time.time()
                while time.time() - start_time < 15:
                  curr = page.url
                  if "mega.nz" in curr and ("#" in curr or "#!" in curr):
                    final_mega_url = curr
                    break
                  time.sleep(0.5)
                browser.close()
            except Exception as e:
              console.print(f"[red]✘ Playwright Error: {e}[/red]")
              time.sleep(5)

          if final_mega_url:
            if "#!" in final_mega_url:
              final_mega_url = final_mega_url.replace("#!", "file/").replace("!", "#", 1)
            try:
              f_id = final_mega_url.split("file/")[1].split("#")[0]
              final_target = megaNZ.decrypt_mega_file(final_mega_url, f_id, console)
              is_temp = True
            except Exception as e:
              import traceback
              console.print("[red]✘ ERROR DEKRIPSI C++:[/red]")
              console.print(traceback.format_exc())
              time.sleep(10)
              break
          else:
            console.print("[red]✘ Timeout: Gagal mendapatkan link Mega asli.[/red]")
            time.sleep(3); break
        
        else:
          current_url = server_url
          if any(x in current_url for x in ['desustream.com', 'otakudesu.cloud']):
            try:
              with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(current_url, wait_until='domcontentloaded')
                time.sleep(1); current_url = page.url; browser.close()
            except: pass
          final_target = pdrain.scrape(current_url)

        if final_target:
          play_with_mpv(final_target, is_temp_file=is_temp)
        else:
          console.print(f'[red]✘ Stream resolution failed.[/red]'); time.sleep(2); break

        post_play = inquirer.select(message="Command:", choices=['▶ NEXT', '◀ PREV', '↺ REPLAY', '⚙ QUALITY', '✖ QUIT'], style=custom_style).execute()
        if post_play == '▶ NEXT': current_ep_idx += 1
        elif post_play == '◀ PREV': current_ep_idx -= 1
        elif post_play == '⚙ QUALITY': continue
        elif post_play == '↺ REPLAY': continue
        else: current_ep_idx = -1; break
      if current_ep_idx == -1: break

if __name__ == '__main__':
  try: main()
  except KeyboardInterrupt: console.print(f'\n[yellow]Sayonara![/yellow]')