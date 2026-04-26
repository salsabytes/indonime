import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
prefix = 'https://anoboy7.com'

def search(query):
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

def get_episodes(url):
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

def download(url):
  try:
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    dl_div = soup.find('div', class_='navi')
    if not dl_div:
      return []
    all_links = []
    for li in dl_div('a'):
        all_links.append({
          'title' : li.text.strip(),
          'url' : li['href']
        })
    del all_links[0:2]
    return all_links
  except Exception as e:
    return []

if __name__ == "__main__":
  s = search('otonari ni tenshi')[0]
  eps = get_episodes(s['url'])[0]
  dl_links = download(eps['url'])
  print(dl_links)
 