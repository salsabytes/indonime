# Anoboy provider: search, episodes, download links.
from ._base import catalog_links, fetch_soup, cached, safe, full_image

BASE = 'https://anoboy7.com'


@safe([])
@cached(ttl=300)
def search_anime(query):
  q = query.replace(' ', '-')
  soup = fetch_soup(f'{BASE}/search/{q}/')
  return [
    {'title': td.find('a').text.strip(), 'url': BASE + td.find('a')['href'], 'image': ''}
    for td in soup.find_all('td', class_='videsc')
  ]


@safe([])
@cached(ttl=300)
def latest():
  # Home page: latest posts with posters.
  soup = fetch_soup(f'{BASE}/')
  items = []
  for a in soup.find_all('a', href=True):
    if '/anime/' not in a['href']:
      continue
    img = a.find('img')
    src = (img.get('src') or img.get('data-src') or '') if img else ''
    if not src:
      continue
    src = src if src.startswith('http') else BASE + src
    items.append({
      'title': (a.get('title') or '').strip() or a.get_text(' ', strip=True),
      'url': BASE + a['href'],
      'image': src,
      'image_full': full_image(src),
    })
  return items


@safe({})
@cached(ttl=600)
def info(url):
  # Detail page → poster + title (anoboy has no synopsis).
  soup = fetch_soup(url)
  img = soup.find('img', src=lambda s: s and '/img/' in s)
  title = soup.title.text.strip() if soup.title else ''
  if ' - anoBoy' in title:
    title = title.replace(' - anoBoy', '')
  return {
    'title': title,
    'image': (BASE + img['src']) if img else '',
    'synopsis': '',
  }


@safe([])
# Full catalog — live fuzzy search source. Cached by _get_catalog, not here.
def list_all():
  return catalog_links(fetch_soup(f'{BASE}/anime-list/'), BASE)


@safe([])
@cached(ttl=300)
def episodes(url):
  soup = fetch_soup(url)
  container = soup.find_all('div', class_='ep')
  target = max(container, key=lambda x: len(x.find_all('a')))
  return [
    {'title': a.text.strip(), 'url': BASE + a['href']}
    for a in target.find_all('a')
  ]


@safe({})
@cached(ttl=60)
def downloads(url):
  soup = fetch_soup(url)
  dl_div = soup.find('div', class_='navi')
  if not dl_div:
    return {}
  # Real download servers are absolute http links; nav (Prev/Semua/Next) are relative.
  links = [
    {'name': a.text.strip(), 'url': a['href']}
    for a in dl_div('a') if a['href'].startswith('http')
  ]
  # quality label = server type ("GDrive"/"MP4"), server name keeps full text
  return {link['name'].replace('Download ', ''): {link['name']: link['url']}
          for link in links}
