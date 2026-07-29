import requests
from urllib.parse import urlparse
from ..ui import console
from ..plugins._base import HEADERS


_PIXELDRAIN_DOMAIN = "pixeldrain.com"


def _is_pixeldrain_url(url):
  """Proper hostname check — not a substring match."""
  try:
    host = urlparse(url).netloc.lower()
    return host == _PIXELDRAIN_DOMAIN or host.endswith("." + _PIXELDRAIN_DOMAIN)
  except Exception:
    return False


def scrape(url):
  try:
    with console.status("[bold cyan]Bypassing Otakulinks...[/bold cyan]"):
      response = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)

    final_url = response.url

    if _is_pixeldrain_url(final_url):
      file_id = final_url.split('/')[-1].split('?')[0]
      return f"https://pixeldrain.com/api/file/{file_id}"
    else:
      console.print(f"[yellow]⚠ Redirect berakhir di: {final_url}[/yellow]")
      return None

  except Exception as e:
    console.print(f"[red]✘ Requests Error: {e}[/red]")
    if _is_pixeldrain_url(url):
      file_id = url.split('/')[-1].split('?')[0]
      return f"https://pixeldrain.com/api/file/{file_id}"
    return None
