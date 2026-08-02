# Cache, HTTP helpers (stdlib urllib), plugin base.
#
# Plugin contract:
#   search_anime(query: str) -> list[dict]  # [{title, url}]
#   episodes(url: str)      -> list[dict]
#   downloads(url: str)     -> dict        # {quality: {server: url}}
import json
import sys
import time
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
def _open(url, timeout, method=None, headers=None, data=None):
  req = urllib.request.Request(url, data=data, headers=headers or HEADERS, method=method)
  return urllib.request.urlopen(req, timeout=timeout)

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

_CACHE = {}
_CACHE_AT = {}

# Memoize with a TTL in seconds. Skips caching empty results.
def cached(ttl=300):
  def dec(fn):
    def wrap(*args, **kwargs):
      key = (fn.__module__, fn.__name__, args, tuple(sorted(kwargs.items())))
      now = time.time()
      val = _CACHE.get(key)
      if val is not None and now - _CACHE_AT.get(key, 0) < ttl:
        return val
      val = fn(*args, **kwargs)
      if val is not None and val != [] and val != {}:
        _CACHE[key] = val
        _CACHE_AT[key] = now
      return val
    return wrap
  return dec

def cache_clear():
  _CACHE.clear()
  _CACHE_AT.clear()

# GET url → BeautifulSoup. Raises on failure.
def fetch_soup(url, headers=HEADERS, timeout=15):
  _, _, _, body = http_get(url, timeout=timeout, headers=headers)
  return BeautifulSoup(body.decode('utf-8', 'replace'), 'html.parser')

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
