import requests
from rich.console import Console

console = Console()

def scrape(url):
  headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  }
  
  try:
    with console.status("[bold cyan]Bypassing Otakulinks...[/bold cyan]"):
      response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
    
    final_url = response.url
    
    if "pixeldrain.com" in final_url:
      file_id = final_url.split('/')[-1].split('?')[0]
      return f"https://pixeldrain.com/api/file/{file_id}"
    else:
      console.print(f"[yellow]⚠ Redirect berakhir di: {final_url}[/yellow]")
      return None
      
  except Exception as e:
    console.print(f"[red]✘ Requests Error: {e}[/red]")
    if "pixeldrain.com" in url:
      file_id = url.split('/')[-1].split('?')[0]
      return f"https://pixeldrain.com/api/file/{file_id}"
    return None