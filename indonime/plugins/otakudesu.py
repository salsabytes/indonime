"""Otakudesu provider — search, episodes, download links."""
from ._base import HEADERS, fetch_soup, cached, safe

BASE = 'https://otakudesu.blog'


@safe([])
@cached(ttl=300)
def search_anime(query):
  q = query.replace(' ', '+')
  soup = fetch_soup(f'{BASE}/?s={q}&post_type=anime')
  return [
    {'title': li.find('h2').text.strip(), 'url': li.find('a')['href']}
    for li in soup.find_all('li', style='list-style:none;')
  ]


@safe([])
@cached(ttl=300)
def episodes(url):
  soup = fetch_soup(url)
  target = None
  for c in soup.find_all('div', class_='episodelist'):
    text = c.get_text().lower()
    if 'episode list' in text and 'batch' not in text:
      target = c
      break
  if not target:
    return []
  eps = [
    {'title': a.text.strip(), 'url': a['href']}
    for a in target.find_all('a') if 'episode' in a['href']
  ]
  return eps[::-1]


@safe({})
@cached(ttl=60)
def downloads(url):
  soup = fetch_soup(url)
  dl_div = soup.find('div', class_='download')
  if not dl_div:
    return {}
  result = {}
  for li in dl_div.find_all('li'):
    res_key = li.find('strong').text.strip()
    links = {a.text.strip(): a['href'] for a in li.find_all('a')}
    result[res_key] = links
  return result
