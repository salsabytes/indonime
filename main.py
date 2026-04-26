import os
import importlib
import subprocess
import time
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.utils import get_style
from rich.console import Console
from playwright.sync_api import sync_playwright
from ext import pdrain

console = Console()

def play_with_mpv(direct_url):
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
    subprocess.Popen(mpv_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    return True, None
  except Exception as e:
    return False, str(e)

def main():
  console.print(r"""[bold cyan]
  ___           _             _                 
 |_ _|_ __   __| | ___  _ __ (_)_ __ ___   ___  
  | || '_ \ / _` |/ _ \| '_ \| | '_ ` _ \ / _ \ 
  | || | | | (_| | (_) | | | | | | | | | |  __/ 
 |___|_| |_|\__,_|\___/|_| |_|_|_| |_| |_|\___|
  [/bold cyan][italic]Subtitle Indonesia Anime Searcher[/italic]""")
  
  p_name = 'otakudesu'
  
  custom_style = get_style({
    'questionmark': '#5fafd7 bold',
    'question': '#d1d1d1',
    'instruction': '#454545 italic',
    'pointer': '#5fafd7 bold',
    'answere': '#5fafd7',
  }, style_override=False)

  while True:
    available_providers = [f.replace('.py', '') for f in os.listdir('plugins') if f.endswith('.py') and not f.startswith('__')]
    label_rich = f'[bold cyan]❮ {p_name.upper()} ❯[/bold cyan]'
    
    try:
      plugin = importlib.import_module(f'plugins.{p_name}')
      importlib.reload(plugin)
    except Exception as e:
      console.print(f'[red]Error Plugin: {e}[/red]')
      p_name = 'otakudesu'
      continue

    is_switching = False

    try:
      prompt = inquirer.text(
        message='Cari Judul Anime:',
        qmark=f'❮ {p_name.upper()} ❯',
        instruction='[⌥P]',
        style=custom_style,
        validate=lambda x: True if is_switching else len(x) > 0,
        invalid_message='Judulnya jangan kosong dong Naz...'
      )
      
      @prompt.register_kb('alt-p')
      def _(event):
        nonlocal is_switching
        is_switching = True
        event.app.exit(result='/switch')

      result = prompt.execute()
    except KeyboardInterrupt:
      console.print(f'\n[yellow]Sayonara, Naz! 👋[/yellow]')
      break

    if result == '/switch':
      new_p = inquirer.select(
        message='Pilih Provider Baru:',
        choices=available_providers,
        qmark='❯',
        style=custom_style
      ).execute()
      if new_p: p_name = new_p
      continue

    if not result: break
    query_text = result

    with console.status(f'{label_rich} [bold green]Mencari "{query_text}"...[/bold green]'):
      try:
        results = plugin.search_anime(query_text)
      except Exception as e:
        console.print(f'[red]Error: {e}[/red]')
        continue
    
    if not results:
      console.print(f'{label_rich} [yellow]Gak ketemu.[/yellow]')
      continue

    choices = [item['title'] for item in results] + ['-- KEMBALI --']
    selected_title = inquirer.fuzzy(
      message='Pilih Anime:',
      qmark=f'❮ {p_name.upper()} ❯',
      choices=choices,
      style=custom_style
    ).execute()
    if selected_title == '-- KEMBALI --' or selected_title is None: continue
    
    selected_url = next(item['url'] for item in results if item['title'] == selected_title)
    
    with console.status(f'{label_rich} [bold blue]Ambil list episode...[/bold blue]'):
      episode_list = plugin.episodes(selected_url)

    ep_choices = [{'name': f'EP {str(i+1).zfill(2)} - {ep['title']}', 'value': i} for i, ep in enumerate(episode_list)]
    selected_idx = inquirer.select(
      message='Pilih Episode:',
      qmark=f'❮ {p_name.upper()} ❯',
      choices=ep_choices,
      style=custom_style
    ).execute()
    if selected_idx is None: continue
    
    with console.status(f'{label_rich} [bold cyan]Bongkar link server...[/bold cyan]'):
      dl_links = plugin.downloads(episode_list[selected_idx]['url'])

    if dl_links:
      options = []
      for res, servers in dl_links.items():
        for s_name, s_url in servers.items():
          if 'pdrain' in s_name.lower() or 'pixeldrain' in s_name.lower():
            options.append({'name': f'[{res}] {s_name}', 'value': s_url})
      
      if not options:
        console.print(f'{label_rich} [yellow]Server PDrain tidak tersedia.[/yellow]')
        continue

      server_url = inquirer.select(
        message='Pilih Server:',
        qmark=f'❮ {p_name.upper()} ❯',
        choices=options,
        style=custom_style
      ).execute()
      if server_url is None: continue
      
      with console.status(f'{label_rich} [bold magenta]Mengekstrak link...', spinner='dots') as status:
        final_link = None
        current_url = server_url
        if any(x in current_url for x in ['desustream.com', 'otakudesu.cloud']):
          status.update(f'{label_rich} [bold yellow]Redirecting...')
          try:
            with sync_playwright() as p:
              browser = p.chromium.launch(headless=True)
              page = browser.new_page()
              page.goto(current_url, wait_until='domcontentloaded', timeout=30000)
              time.sleep(2)
              current_url = page.url
              browser.close()
          except: pass
        
        final_link = pdrain.scrape(current_url)
        is_valid = False
        if final_link:
          final_lower = final_link.lower()
          keywords = ['.mp4', 'download', '.mkv', 'pixeldrain.com/api']
          if any(kw in final_lower for kw in keywords): is_valid = True

        if is_valid:
          status.update(f'{label_rich} [bold cyan]Membuka MPV...')
          success, err = play_with_mpv(final_link)
          if success:
            time.sleep(1)
            console.print(f'[green]✔ Berhasil menonton![/green]')
          else:
            console.print(f'[red]✘ {err}[/red]')
        else:
          console.print(f'[red]✘ Link tidak valid.[/red]')
    else:
      console.print(f'{label_rich} [red]Gagal dapet link.[/red]')

if __name__ == '__main__':
  main()
