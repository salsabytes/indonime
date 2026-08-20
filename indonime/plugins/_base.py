# Cache, HTTP helpers (stdlib urllib), plugin base.
#
# Plugin contract:
#   search_anime(query: str) -> list[dict]  # [{title, url}]
#   episodes(url: str)      -> list[dict]
#   downloads(url: str)     -> dict        # {quality: {server: url}}
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

HEADERS = {
  'User-Agent': (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
  ),
}

# urllib helpers (replacement for requests)
def _scheme_ok(url):
  # Bandit B310: only allow http(s) — never file:/ custom schemes.
  return urllib.parse.urlparse(url).scheme in ('http', 'https')

# SSRF guard: this app only ever fetches these hosts. New provider/stream hosts
# must be added here.
_ALLOWED_HOSTS = frozenset({
  'otakudesu.blog', 'anoboy7.com',
  'pixeldrain.com',
  'g.api.mega.co.nz', 'mega.nz', 'dl.xtwap.top', 'gdplayer.to',
})

def _url_allowed(url):
  if not _scheme_ok(url):
    return False
  host = urllib.parse.urlparse(url).hostname
  if not host:
    return False
  host = host.lower()
  return (host in _ALLOWED_HOSTS
          or host.endswith('.mega.co.nz') or host.endswith('.mega.nz'))

# Redirect hops re-checked against the allowlist — urlopen follows redirects
# automatically, so a host allowed for the first request must not be able to
# point us anywhere else (classic SSRF guard bypass).
class _GuardRedirects(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, newurl):
    if not _url_allowed(newurl):
      raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
    return super().redirect_request(req, fp, code, msg, headers, newurl)

_opener = urllib.request.build_opener(_GuardRedirects)

def _open(url, timeout, method=None, headers=None, data=None):
  if not _url_allowed(url):
    raise ValueError(f"URL diblokir: {url}")
  req = urllib.request.Request(url, data=data, headers=headers or HEADERS, method=method)
  return _opener.open(req, timeout=timeout)

# GET → (final_url, status, headers, body). Raises on HTTP/network error.
def http_get(url, timeout=15, headers=None):
  with _open(url, timeout, headers=headers) as r:
    return r.geturl(), r.status, r.headers, r.read()

# HEAD → (status, content_type). Raises on HTTP/network error.
def http_head(url, timeout=10):
  with _open(url, timeout, method='HEAD') as r:
    return r.status, r.headers.get('Content-Type', '')

# POST JSON → parsed JSON response. Raises on error.
def http_post_json(url, payload, timeout=15):
  headers = {**HEADERS, 'Content-Type': 'application/json'}
  with _open(url, timeout, method='POST', headers=headers,
             data=json.dumps(payload).encode('utf-8')) as r:
    return json.loads(r.read().decode('utf-8'))

# GET → open file-like response; caller reads chunks. Raises on error.
def http_stream(url, timeout=30):
  return _open(url, timeout)

# GET with redirects → final URL after all redirects.
def resolve_url(url, timeout=15):
  with _open(url, timeout) as r:
    return r.geturl()

# Download url → dest in 64KB chunks with a tuiko progress bar; returns bytes.
# on_total(total)/on_bytes(delta) → aggregate batch progress (workers report
# deltas into one shared bar; the internal bar here draws into a discard buffer).
def http_download(url, dest, desc, timeout=30, out=None, on_total=None, on_bytes=None):
  from ..ui import progress
  with http_stream(url, timeout=timeout) as resp:
    total = int(resp.headers.get('Content-Length', 0))
    if on_total:
      on_total(total)
    with progress(desc, total=total or None, out=out) as up:
      size = 0
      with open(dest, 'wb') as f:
        while True:
          chunk = resp.read(64 * 1024)
          if not chunk:
            break
          f.write(chunk)
          size += len(chunk)
          if on_bytes:
            on_bytes(len(chunk))
          if total:
            up(size)
  return size

_CACHE = {}
_CACHE_AT = {}
_PERSIST = set()  # keys that survive cache_clear() — the big catalog

# Memoize with a TTL in seconds. Skips caching empty results.
# persist=True → the entry survives cache_clear() (used for the catalog).
def cached(ttl=300, persist=False):
  def dec(fn):
    def wrap(*args, **kwargs):
      key = (fn.__module__, fn.__name__, args)
      now = time.time()
      val = _CACHE.get(key)
      if val is not None and now - _CACHE_AT.get(key, 0) < ttl:
        return val
      val = fn(*args, **kwargs)
      if val not in (None, [], {}):
        _CACHE[key] = val
        _CACHE_AT[key] = now
        if persist:
          _PERSIST.add(key)
      return val
    return wrap
  return dec

def cache_clear():
  # Transient entries die; persistent (catalog) entries stay.
  for k in list(_CACHE):
    if k not in _PERSIST:
      del _CACHE[k]
      del _CACHE_AT[k]

# GET url → BeautifulSoup. Raises on failure.
def fetch_soup(url, timeout=15):
  _, _, _, body = http_get(url, timeout=timeout, headers=HEADERS)
  return BeautifulSoup(body.decode('utf-8', 'replace'), 'html.parser')

# Parse anime links from an /anime-list/ page: dedupe, keep /anime/ hrefs,
# absolutize relative hrefs via base.
def catalog_links(soup, base=''):
  seen, out = set(), []
  for a in soup.find_all('a', href=True):
    href = a['href']
    if '/anime/' not in href or href in seen:
      continue
    seen.add(href)
    url = href if href.startswith('http') else base + href
    out.append({'title': a.get_text(' ', strip=True), 'url': url})
  return out

# Catch-all decorator → fallback value on error.
def safe(fb):
  def dec(fn):
    def wrap(*a, **kw):
      try:
        return fn(*a, **kw)
      except Exception as e:
        hint = f'[_base] {fn.__name__}{a} -> {type(e).__name__}: {e}'
        print(hint[:200], file=sys.stderr)  # trim for readability
        return fb
    return wrap
  return dec

# Wordpress-style size suffix → original file:
# ".../img-236x350.jpg" → ".../img.jpg" (also drops ?resize=/w=/h= params).
def full_image(url):
  if not url:
    return ''
  url = re.sub(r'[?&](?:resize|w|h|fit|crop)=[^&#]*', '', url)
  return re.sub(r'-\d+x\d+(?=\.[a-zA-Z0-9]+$)', '', url)
