# Otakudesu provider: search, episodes, download links.
from ._base import catalog_links, fetch_soup, cached, safe, full_image

BASE = 'https://otakudesu.blog'


@safe([])
@cached(ttl=300)
def search_anime(query):
  q = query.replace(' ', '+')
  soup = fetch_soup(f'{BASE}/?s={q}&post_type=anime')
  items = []
  for li in soup.find_all('li', style='list-style:none;'):
    img = li.find('img')
    items.append({
      'title': li.find('h2').text.strip(),
      'url': li.find('a')['href'],
      'image': (img.get('src') or img.get('data-src') or '') if img else '',
    })
  return items


@safe({})
@cached(ttl=300)
def latest():
  # Home page: featured/latest posts with posters (the catalog has no images).
  soup = fetch_soup(f'{BASE}/')
  items = []
  for v in soup.find_all('div', class_='venz'):
    for a in v.find_all('a', href=True):
      if '/anime/' not in a['href']:
        continue
      img = a.find('img')
      if not img:
        continue
      src = img.get('src') or img.get('data-src') or ''
      items.append({
        'title': (a.get('title') or '').strip() or a.get_text(' ', strip=True),
        'url': a['href'],
        'image': src,
        'image_full': full_image(src),
      })
  return items


@safe({})
@cached(ttl=600)
def info(url):
  # Detail page → poster, title, synopsis (for the anime header in the GUI).
  soup = fetch_soup(url)
  foto = soup.find('div', class_='fotoanime')
  img = foto.find('img') if foto else None
  sinopc = soup.find('div', class_='sinopc') or soup.find('div', class_='sinopke')
  h1 = soup.find('h1')
  return {
    'title': h1.text.strip() if h1 else '',
    'image': (img.get('src') or '') if img else '',
    'synopsis': sinopc.get_text(' ', strip=True) if sinopc else '',
  }


@safe([])
# Full catalog — live fuzzy search source. Cached by _get_catalog, not here.
def list_all():
  return catalog_links(fetch_soup(f'{BASE}/anime-list/'), BASE)


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
