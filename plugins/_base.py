"""Shared plugin utilities — cache, HTTP helpers, decorators.

Plugin contract (duck-typed):
  search_anime(query: str) -> list[dict]  # [{title, url}, ...]
  episodes(url: str)      -> list[dict]  # [{title, url}, ...]
  downloads(url: str)     -> dict        # {quality: {server: url, ...}, ...}
"""
import sys
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}

_SESSION = requests.Session()  # reuse TCP + TLS across plugin calls

# ── Simple TTL cache ──────────────────────────────────────────────
_CACHE = {}
_CACHE_AT = {}  # key -> timestamp

def cached(ttl=300):
    """Memoize with time-to-live seconds. Skips caching empty results."""
    def dec(fn):
        def wrap(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            val = _CACHE.get(key)
            if val is not None and now - _CACHE_AT.get(key, 0) < ttl:
                return val
            val = fn(*args, **kwargs)
            # don't poison cache with error results
            if val is not None and val != [] and val != {}:
                _CACHE[key] = val
                _CACHE_AT[key] = now
            return val
        return wrap
    return dec

def cache_clear():
    _CACHE.clear()
    _CACHE_AT.clear()

# ── HTTP + BS4 helpers ────────────────────────────────────────────
def fetch_soup(url, headers=HEADERS, timeout=15):
    """GET url, return BeautifulSoup object. Raises on failure."""
    res = _SESSION.get(url, headers=headers, timeout=timeout)
    res.raise_for_status()
    return BeautifulSoup(res.text, 'html.parser')

# ── Safety decorators ─────────────────────────────────────────────
def _safe_err(fn, e, fallback, args, kwargs):
    """Print debug hint to stderr so silent failures aren't invisible."""
    hint = f'[_base] {fn.__name__}{args} -> {type(e).__name__}: {e}'
    print(hint[:200], file=sys.stderr)  # ponytail: trim for readability
    return fallback

def safe(fb):
    """Catch-all decorator → fallback value on error. Errors printed to stderr."""
    def dec(fn):
        def wrap(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception as e:
                return _safe_err(fn, e, fb, a, kw)
        return wrap
    return dec
