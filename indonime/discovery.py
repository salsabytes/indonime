# AniList discovery client — pengganti list_all/latest/search_anime sebagai
# sumber daftar. GraphQL publik tanpa auth, urllib native (http_post_json),
# limit 90 req/min → @cached TTL cukup, tanpa throttle.
import json
import re

from .plugins._base import cached, http_post_json

BASE = 'https://graphql.anilist.co'

# AniList seasons (JST): WINTER=Jan-Mar, SPRING=Apr-Jun, SUMMER=Jul-Sep, FALL=Oct-Dec
_SEASONS = ['WINTER', 'SPRING', 'SUMMER', 'FALL']

_QUERY = '''query ($page: Int, $perPage: Int, $search: String, $season: MediaSeason,
                  $seasonYear: Int, $genre: String, $sort: [MediaSort]) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME, search: $search, season: $season, seasonYear: $seasonYear,
          genre: $genre, sort: $sort) {
      id
      title { romaji english }
      coverImage { large extraLarge }
      description
      genres
      averageScore
      startDate { year }
    }
  }
}'''


def _items(media_list, take=24):
  # AniList → item contract {id, title, image, image_full, synopsis, genres, score, year}
  out = []
  for a in media_list or []:
    t = a.get('title') or {}
    img = a.get('coverImage') or {}
    desc = re.sub(r'<[^>]+>', '', a.get('description') or '')
    out.append({
      'id': f"anilist-{a.get('id')}",
      'title': t.get('romaji') or t.get('english') or '',
      'image': img.get('large') or '',
      'image_full': img.get('extraLarge') or '',
      'synopsis': desc.strip()[:400],
      'genres': sorted(a.get('genres') or []),
      'score': round((a.get('averageScore') or 0) / 10, 2) or None,
      'year': (a.get('startDate') or {}).get('year'),
    })
  return out[:take]


def _get(variables, take=24):
  # AniList intermittent 5xx/gateway → retry 1x (cache skip empty, jadi
  # transient error gak nempel; retry di sini nutupin web+RN+TUI sekaligus).
  import time
  last = None
  for attempt in range(2):
    try:
      payload = http_post_json(f'{BASE}/', {'query': _QUERY, 'variables': variables})
      if 'data' not in payload:
        raise RuntimeError(f'AniList error: {payload.get("errors") or payload}')
      return _items(payload['data'].get('Page', {}).get('media'), take)
    except Exception as e:
      last = e
      if attempt == 0:
        time.sleep(0.8)
  raise last


@cached(ttl=86400)
def top(n=24):
  return _get({'perPage': n, 'sort': ['POPULARITY_DESC']}, n)


@cached(ttl=3600)
def seasonal(n=24):
  import datetime
  now = datetime.datetime.now()
  season = _SEASONS[(now.month - 1) // 3]
  return _get({'perPage': n, 'season': season, 'seasonYear': now.year,
               'sort': ['POPULARITY_DESC']}, n)


@cached(ttl=86400)
def by_genre(genre, n=24):
  return _get({'perPage': n, 'genre': genre, 'sort': ['POPULARITY_DESC']}, n)


@cached(ttl=300)
def search(query, n=8):
  return _get({'perPage': n, 'search': query, 'sort': ['SEARCH_MATCH']}, n)


@cached(ttl=86400)
def browse(sort='POPULARITY_DESC', n=50, page=1):
  return _get({'page': page, 'perPage': n, 'sort': [sort]}, n)


# Subset genre umum yang ada di AniList genre taxonomy (populer di Indonesia).
GENRES = ['Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Romance',
          'Sci-Fi', 'Shounen', 'Slice of Life', 'Supernatural', 'Sports',
          'Mystery']
