# Map AniList title → detail URL per provider. Search provider sekali per
# judul, hasil di-cache ke disk biar gak re-hit. Multi-provider: semua
# provider yang match ikut disimpan → gap-filling (fallback per episode/source).
import concurrent.futures
import json
import os
import re

_MAP_FILE = os.path.join(os.path.expanduser("~"), ".indonime", "map.json")
_map = {}
try:
  with open(_MAP_FILE) as f:
    _map = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
  pass


def _save():
  tmp = _MAP_FILE + ".tmp"
  os.makedirs(os.path.dirname(tmp), exist_ok=True)
  with open(tmp, "w") as f:
    json.dump(_map, f)
  os.replace(tmp, _MAP_FILE)


def _norm(s):
  # buang suffix umum provider (Subtitle Indonesia/Batch/TV/OVA...) + non-alnum
  s = s.lower()
  s = re.sub(r'\b(subtitle indonesia|batch|bd|tv|movie|ova|ona)\b', ' ', s)
  s = re.sub(r'[^a-z0-9]+', ' ', s)
  return ' '.join(s.split())


def _score(a, b):
  a, b = _norm(a), _norm(b)
  if not a or not b:
    return 0.0
  if a == b:
    return 1.0
  sa, sb = set(a.split()), set(b.split())
  inter = sa & sb
  if not inter:
    return 0.0
  jaccard = len(inter) / len(sa | sb)
  return jaccard + 0.3 * (len(sa - sb) == 0)  # bonus: seluruh token judul pendek cocok


def resolve(plugin_list, title, min_score=0.45):
  # plugin_list: [(name, plugin), ...] urutan fallback. Return {provider: url}
  # untuk semua yang match; kosong kalau gak ada yang match.
  key = title
  if key in _map:
    return _map[key]
  # cari semua provider secara paralel
  # ponytail: 8 thread cap — aman utk ratusan plugin nanti; upgrade path: async (trio/httpx) kalau perlu retry/budget
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(plugin_list), 8)) as ex:
    futures = {ex.submit(p.search_anime, title): name for name, p in plugin_list}
    results = {}
    for f in concurrent.futures.as_completed(futures):
      results[futures[f]] = f.result()
  out = {}
  for name, _ in plugin_list:
    hits = results.get(name) or []
    if not hits:
      continue
    best = max(hits, key=lambda h: _score(title, h.get('title', '')))
    if _score(title, best.get('title', '')) >= min_score:
      out[name] = best['url']
  _map[key] = out
  _save()
  return out


def candidates(plugin_list, title):
  # Semua hasil search semua provider → UI bisa tampilkan list manual (kalau
  # resolve kosong semua atau user mau pilih sendiri).
  # cari semua provider secara paralel
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(plugin_list), 8)) as ex:
    futures = {ex.submit(p.search_anime, title): name for name, p in plugin_list}
    results = {}
    for f in concurrent.futures.as_completed(futures):
      results[futures[f]] = f.result()
  # gabung hasil urut sesuai plugin_list
  out = []
  for name, _ in plugin_list:
    for h in results.get(name) or []:
      out.append((name, h['title'], h['url']))
  return out
