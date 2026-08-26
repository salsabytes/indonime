# Map AniList title → detail URL per provider. Search each provider once per
# title, cache results to disk to avoid re-hits. Multi-provider: every matching
# provider is stored → gap-filling (per-episode/source fallback).
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


def _search_all(plugin_list, title):
  """Search all providers in parallel, return {name: [hits]}."""
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(plugin_list), 8)) as ex:
    futures = {ex.submit(p.search_anime, title): name for name, p in plugin_list}
    results = {}
    for f in concurrent.futures.as_completed(futures):
      results[futures[f]] = f.result()
  return results


def resolve(plugin_list, title, min_score=0.45):
  # plugin_list: [(name, plugin), ...] fallback order. Return {provider: url}
  # for every match; empty when nothing matches.
  key = title
  if key in _map:
    return _map[key]
  results = _search_all(plugin_list, title)
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
  # All provider search results → UI can show a manual list (when resolve
  # comes up empty or the user wants to pick).
  results = _search_all(plugin_list, title)
  # merge results in plugin_list order
  out = []
  for name, _ in plugin_list:
    for h in results.get(name) or []:
      out.append((name, h['title'], h['url']))
  return out
