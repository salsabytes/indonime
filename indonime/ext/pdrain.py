from urllib.parse import urlparse
from tuiko import status, style
from ..ui import Palette
from ..plugins._base import http_head, resolve_url


_PIXELDRAIN_DOMAIN = "pixeldrain.com"


# Proper hostname check — not a substring match.
def _is_pixeldrain_url(url):
  try:
    host = urlparse(url).netloc.lower()
    return host == _PIXELDRAIN_DOMAIN or host.endswith("." + _PIXELDRAIN_DOMAIN)
  except Exception:
    return False


# HEAD check: file exists & returns video content.
def _is_playable(url):
  try:
    status_code, ctype = http_head(url, timeout=10)
    return status_code == 200 and ctype.startswith("video/")
  except Exception:
    return False


def scrape(url):
  try:
    status("🌀 Bypassing Otakulinks...")
    final_url = resolve_url(url, timeout=15)

    if _is_pixeldrain_url(final_url):
      file_id = final_url.split('/')[-1].split('?')[0]
      api_url = f"https://pixeldrain.com/api/file/{file_id}"
      # HEAD check prevents mpv launching into dead file (451 takedown)
      if not _is_playable(api_url):
        print(style("⚠ Stream tidak tersedia (mungkin kena takedown)", Palette.warning))
        return None
      return api_url
    else:
      print(style(f"⚠ Redirect berakhir di: {final_url}", Palette.warning))
      return None

  except Exception as e:
    print(style(f"✘ Network Error: {e}", Palette.error))
    if _is_pixeldrain_url(url):
      file_id = url.split('/')[-1].split('?')[0]
      api_url = f"https://pixeldrain.com/api/file/{file_id}"
      if _is_playable(api_url):
        return api_url
    return None
