import os
import importlib
import subprocess
import time
from InquirerPy import inquirer
from rich.console import Console
from playwright.sync_api import sync_playwright
from ext import pdrain

console = Console()

def play_with_mpv(direct_url):
  base_path = os.path.dirname(os.path.abspath(__file__))
  folder_mpv = os.path.join(base_path, 'mpv')
  path_ke_mpv = os.path.join(folder_mpv, 'mpv.exe') 
  if not os.path.exists(path_ke_mpv):
    return False, f"File mpv.exe tidak ditemukan."
  mpv_args = [
    path_ke_mpv,
    direct_url,
    '--title=Indonime Player - Naz Edition',
    '--ontop',
    '--no-border',
    '--force-window=yes',
    '--cache=yes',
    '--demuxer-max-bytes=10M',
    '--demuxer-readahead-secs=5',
    '--network-timeout=15',
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
  ]
  try:
    subprocess.Popen(mpv_args, cwd=folder_mpv, creationflags=subprocess.CREATE_NEW_CONSOLE)
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
                
        [/bold cyan][italic]Stream Anime Subtitle Indonesia[/italic]""")
  console.print('            Supported Link: PDrain\n')
  if not os.path.exists('plugins'): os.makedirs('plugins')
  files = [f[:-3] for f in os.listdir('plugins') if f.endswith('.py') and f != '__init__.py']
  if not files:
    console.print("[red]Folder 'plugins' kosong![/red]")
    return
  p_name = inquirer.select(message='Pilih Provider:', choices=files).execute()
  plugin = importlib.import_module(f"plugins.{p_name}")
  while True:
    query = inquirer.text(message="Cari Judul Anime:").execute()
    if not query: break
    with console.status(f"[bold green]Mencari '{query}'..."):
      try:
        results = plugin.search_anime(query)
      except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        continue
    if not results:
      console.print("[yellow]Gak ketemu.[/yellow]")
      continue
    choices = [item['title'] for item in results] + ["-- KEMBALI --"]
    selected_title = inquirer.fuzzy(message="Pilih Anime:", choices=choices).execute()
    if selected_title == "-- KEMBALI --": continue
    selected_url = next(item['url'] for item in results if item['title'] == selected_title)
    with console.status("[bold blue]Ambil list episode..."):
      episode_list = plugin.episodes(selected_url)
    ep_choices = [{"name": f"EP {str(i+1).zfill(2)} - {ep['title']}", "value": i} for i, ep in enumerate(episode_list)]
    selected_idx = inquirer.select(message='Pilih Episode:', choices=ep_choices).execute()
    with console.status("[bold cyan]Bongkar link server..."):
      dl_links = plugin.downloads(episode_list[selected_idx]['url'])
    if dl_links:
      options = []
      for res, servers in dl_links.items():
        for s_name, s_url in servers.items():
          if "pdrain" in s_name.lower() or "pixeldrain" in s_name.lower():
            options.append({"name": f"[{res}] {s_name}", "value": s_url})
      if not options:
        console.print("[yellow]Server PDrain tidak tersedia untuk episode ini.[/yellow]")
        continue
      server_url = inquirer.select(message="Pilih Server:", choices=options).execute()
      with console.status("[bold magenta]Mengekstrak link...", spinner="dots") as status:
        final_link = None
        current_url = server_url
        if any(x in current_url for x in ["desustream.com", "otakudesu.cloud"]):
          status.update("[bold yellow]Redirecting...")
          try:
            with sync_playwright() as p:
              browser = p.chromium.launch(headless=True)
              page = browser.new_page()
              page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
              time.sleep(2)
              current_url = page.url
              browser.close()
          except:
            pass
        final_link = pdrain.scrape(current_url)
        is_valid = False
        if final_link:
          final_lower = final_link.lower()
          keywords = [".mp4", "download", ".mkv", "pixeldrain.com/api"]
          if any(kw in final_lower for kw in keywords):
            is_valid = True
        if is_valid:
          status.update("[bold cyan]Link Valid! Membuka MPV...")
          success, err = play_with_mpv(final_link)
          if success:
            time.sleep(1)
            console.print(f"[green]✔ Berhasil menonton![/green]")
          else:
            console.print(f"[red]✘ Gagal buka MPV: {err}[/red]")
        else:
          console.print(f"[red]✘ Gagal mengekstrak: {final_link}[/red]")
    else:
      console.print("[red]Gagal dapet link.[/red]")

if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    console.print("\n[yellow]Sayonara! 👋[/yellow]")