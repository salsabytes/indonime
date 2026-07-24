import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
prefix = 'https://anoboy7.com'

def search_anime(query):
  q = query.replace(' ', '-')
  url = f"{prefix}/search/{q}/"
  try:
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    results = soup.find_all('td', class_="videsc")

    lists = []
    for i in results:
      lists.append({
        'title': i.find('a').text.strip(),
        'url': prefix + i.find('a')['href']
      })
    return lists
  except Exception as e:
    return []

def episodes(url):
  try:
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    container = soup.find_all('div', class_='ep')
    target = max(container, key=lambda x: len(x.find_all('a')))

    ep_list = []
    for a in target.find_all('a'):
        ep_list.append({
          'title': a.text.strip(),
          'url': prefix + a['href']
        })
    return ep_list
  except Exception as e:
    return []

def downloads(url):
  try:
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    dl_div = soup.find('div', class_='navi')
    if not dl_div:
      return {}
    links = []
    for a in dl_div('a'):
      links.append({'name': a.text.strip(), 'url': a['href']})
    links = links[2:]
    result = {}
    for l in links:
      result[l['name']] = {l['name']: l['url']}
    return result
  except Exception as e:
    return {}

if __name__ == "__main__":
  s = search_anime('otonari ni tenshi')[0]
  eps = episodes(s['url'])[0]
  dl_links = downloads(eps['url'])
  print(dl_links)