"""Anoboy provider — search, episodes, download links."""
from ._base import HEADERS, fetch_soup, cached, safe

BASE = 'https://anoboy7.com'


@safe([])
@cached(ttl=300)
def search_anime(query):
    q = query.replace(' ', '-')
    soup = fetch_soup(f'{BASE}/search/{q}/')
    return [
        {'title': td.find('a').text.strip(), 'url': BASE + td.find('a')['href']}
        for td in soup.find_all('td', class_='videsc')
    ]


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
    links = [{'name': a.text.strip(), 'url': a['href']} for a in dl_div('a')][2:]
    return {l['name']: {l['name']: l['url']} for l in links}
