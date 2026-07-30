from urllib.parse import urlparse
from ..ui import console
from ..plugins._base import SESSION


_PIXELDRAIN_DOMAIN = "pixeldrain.com"


def _is_pixeldrain_url(url):
  """Proper hostname check — not a substring match."""
  try:
    host = urlparse(url).netloc.lower()
    return host == _PIXELDRAIN_DOMAIN or host.endswith("." + _PIXELDRAIN_DOMAIN)
  except Exception:
    return False


def _is_playable(url):
  """HEAD check: file exists & returns video content."""
  try:
    r = SESSION.head(url, allow_redirects=True, timeout=10)
    if r.status_code != 200:
      return False
    ctype = r.headers.get("Content-Type", "")
    return ctype.startswith("video/")
  except Exception:
    return False


def scrape(url):
  try:
    with console.status("[bold cyan]Bypassing Otakulinks...[/bold cyan]"):
      response = SESSION.get(url, allow_redirects=True, timeout=15)

    final_url = response.url

    if _is_pixeldrain_url(final_url):
      file_id = final_url.split('/')[-1].split('?')[0]
      api_url = f"https://pixeldrain.com/api/file/{file_id}"
      # ponytail: HEAD check prevents mpv launching into dead file (451 takedown)
      if not _is_playable(api_url):
        console.print("[yellow]⚠ Stream tidak tersedia (mungkin kena takedown)[/yellow]")
        return None
      return api_url
    else:
      console.print(f"[yellow]⚠ Redirect berakhir di: {final_url}[/yellow]")
      return None

  except Exception as e:
    console.print(f"[red]✘ Requests Error: {e}[/red]")
    if _is_pixeldrain_url(url):
      file_id = url.split('/')[-1].split('?')[0]
      api_url = f"https://pixeldrain.com/api/file/{file_id}"
      if _is_playable(api_url):
        return api_url
    return None
