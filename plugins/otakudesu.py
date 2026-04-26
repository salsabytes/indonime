import requests
from bs4 import BeautifulSoup

HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def search_anime(query):
  q = query.replace(' ', '+')
  url = f"https://otakudesu.blog/?s={q}&post_type=anime"
  try:
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    results = soup.find_all('li', style="list-style:none;")
    lists = []
    for i in results:
      lists.append({
        'title': i.find('h2').text.strip(),
        'url': i.find('a')['href']
      })
    return lists
  except Exception as e:
    return []

def episodes(url):
  try:
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    container = soup.find_all('div', class_='episodelist')
    target = None

    for c in container:
      text = c.get_text().lower()
      if 'episode list' in text and 'batch' not in text:
        target = c
        break

    if not target: return []

    ep_list = []
    for a in target.find_all('a'):
      if 'episode' in a['href']:
        ep_list.append({
          'title': a.text.strip(),
          'url': a['href']
        })
    return ep_list[::-1]
  except Exception as e:
    return []

def downloads(url):
  try:
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    dl_div = soup.find('div', class_='download')

    if not dl_div: return {}

    all_links = {}
    for li in dl_div.find_all('li'):
      res_key = li.find('strong').text.strip()
      links = {}
      for a in li.find_all('a'):
        server_name = a.text.strip()
        server_url = a['href']
        links[server_name] = server_url
        all_links[res_key] = links
    return all_links
  except Exception as e:
    return {}