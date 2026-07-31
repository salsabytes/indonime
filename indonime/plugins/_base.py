"""Cache, HTTP helpers (stdlib urllib), plugin base.

Plugin contract:
  search_anime(query: str) -> list[dict]  # [{title, url}]
  episodes(url: str)      -> list[dict]
  downloads(url: str)     -> dict        # {quality: {server: url}}
"""
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

# ── urllib helpers (replacement for requests) ──
def _open(url, timeout, method=None, headers=None, data=None):
  req = urllib.request.Request(url, data=data, headers=headers or HEADERS, method=method)
  return urllib.request.urlopen(req, timeout=timeout)

def http_get(url, timeout=15, headers=None):
  """GET → (final_url, status, headers, body). Raises on HTTP/network error."""
  with _open(url, timeout, headers=headers) as r:
    return r.geturl(), r.status, r.headers, r.read()

def http_head(url, timeout=10):
  """HEAD → (status, content_type). Raises on HTTP/network error."""
  with _open(url, timeout, method='HEAD') as r:
    return r.status, r.headers.get('Content-Type', '')

def http_post_json(url, payload, timeout=15):
  """POST JSON → parsed JSON response. Raises on error."""
  headers = {**HEADERS, 'Content-Type': 'application/json'}
  with _open(url, timeout, method='POST', headers=headers,
             data=json.dumps(payload).encode('utf-8')) as r:
    return json.loads(r.read().decode('utf-8'))

def http_stream(url, timeout=30):
  """GET → open file-like response; caller reads chunks. Raises on error."""
  return _open(url, timeout)

def resolve_url(url, timeout=15):
  """GET with redirects → final URL after all redirects."""
  with _open(url, timeout) as r:
    return r.geturl()

_CACHE = {}
_CACHE_AT = {}

def cached(ttl=300):
  """Memoize with TTL seconds. Skips caching empty results."""
  def dec(fn):
    def wrap(*args, **kwargs):
      key = (fn.__name__, args, tuple(sorted(kwargs.items())))
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

def fetch_soup(url, headers=HEADERS, timeout=15):
  """GET url → BeautifulSoup. Raises on failure."""
  _, _, _, body = http_get(url, timeout=timeout, headers=headers)
  return BeautifulSoup(body.decode('utf-8', 'replace'), 'html.parser')

def safe(fb):
  """Catch-all decorator → fallback value on error."""
  def dec(fn):
    def wrap(*a, **kw):
      try:
        return fn(*a, **kw)
      except Exception as e:
        hint = f'[_base] {fn.__name__}{a} -> {type(e).__name__}: {e}'
        print(hint[:200], file=sys.stderr)  # ponytail: trim for readability
        return fb
    return wrap
  return dec
