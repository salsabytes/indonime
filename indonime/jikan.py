# Jikan v4 discovery client — pengganti list_all/latest/search_anime sebagai
# sumber daftar. Rate limit 3/s, 60/min → throttle 350ms + @cached TTL.
import json

from .plugins._base import cached

BASE = 'https://api.jikan.moe/v4'
_MIN_GAP = 0.35
_last = [0.0]


def _throttle():
  import time
  wait = _MIN_GAP - (time.time() - _last[0])
  if wait > 0:
    time.sleep(wait)
  _last[0] = time.time()


def _items(payload, take=8):
  # Jikan → item contract {id, title, image, image_full, synopsis, genres, score, year}
  out = []
  for a in payload.get('data', []):
    img = (a.get('images') or {}).get('jpg') or {}
    year = None
    aired = a.get('aired') or {}
    from_ = aired.get('from') or ''
    if len(from_) >= 4 and from_[:4].isdigit():
      year = int(from_[:4])
    out.append({
      'id': f"jikan-{a.get('mal_id')}",
      'title': a.get('title') or '',
      'image': img.get('image_url') or '',
      'image_full': img.get('large_image_url') or '',
      'synopsis': (a.get('synopsis') or '')[:400],
      'genres': sorted({g['name'] for g in a.get('genres') or []}),
      'score': a.get('score'),
      'year': year,
    })
  return out[:take]


def _curl_json(path, timeout=20):
  # urllib di-block Jikan (Cloudflare TLS fingerprint → 504 konstan), curl.exe
  # (built-in Win10+/git-bash) lolos. Host constant dari BASE → tanpa SSRF risk.
  # Jikan 504 intermitten (upstream MAL) → retry 5xx 3x. ponytail: ganti ke
  # curl_cffi/requests kapan perlu, upgrade path jelas.
  import subprocess
  import time
  from .plugins._base import HEADERS
  url = f'{BASE}/{path}'
  last = None
  for attempt in range(3):
    if attempt:
      time.sleep(1.5 * attempt)
    try:
      out = subprocess.run(
        ['curl', '-sSf', '--max-time', str(timeout), '-A', HEADERS['User-Agent'], url],
        capture_output=True, text=True, timeout=timeout + 10)
    except Exception as e:
      last = RuntimeError(f'Jikan network error: {e}')
      continue
    if out.returncode == 0:
      return json.loads(out.stdout)
    last = RuntimeError(f'Jikan HTTP/curl error ({out.returncode}): '
                        f"{(out.stderr or out.stdout).strip()[:200]}")
  raise last


def _get(path, take=8):
  _throttle()
  return _items(_curl_json(path), take)


@cached(ttl=86400)
def top(n=24):
  pages = min(2, (n + 24) // 25)  # ponytail: cap 48 item (2 page), naikkan kapan perlu
  items = []
  for p in range(1, pages + 1):
    items += _get(f'top/anime?page={p}', take=n - len(items))
    if len(items) >= n:
      break
  return items


@cached(ttl=3600)
def seasonal(n=24):
  return _get('seasons/now', n)


@cached(ttl=86400)
def by_genre(genre_id, n=24):
  return _get(f'anime?genres={genre_id}&order_by=popularity&sort=asc&page=1', n)


@cached(ttl=300)
def search(query, n=8):
  from urllib.parse import quote
  return _get(f'anime?q={quote(query)}&order_by=popularity&sort=asc&page=1', n)


# ponytail: subset genre umum, naikkan ke fetch dinamis /genres/anime kapan perlu
GENRES = {
  1: 'Action', 2: 'Adventure', 4: 'Comedy', 8: 'Drama', 10: 'Fantasy',
  22: 'Romance', 24: 'Sci-Fi', 27: 'Shounen', 36: 'Slice of Life',
  37: 'Supernatural', 30: 'Sports', 7: 'Mystery',
}
