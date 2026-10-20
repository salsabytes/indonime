# Map AniList title → detail URL per provider. Search each provider once per
# title, cache results to disk to avoid re-hits. Multi-provider: every matching
# provider is stored → gap-filling (per-episode/source fallback).
import concurrent.futures
import json
import os
import re

_MAP_FILE = os.path.join(os.path.expanduser("~"), ".indonime", "map.json")
# Bump tiap scorer/ladder di file ini berubah → entry cache lama (yang bisa
# ngarah ke season/entry salah) otomatis diabaikan tanpa migrasi manual.
_MAP_VER = 'v3|'
_map = {}
try:
  with open(_MAP_FILE) as f:
    # Buang entry versi lama (scorer sebelumnya bisa ngarah ke season atau
    # provider yang salah). Regenerate sendiri saat judul dibuka lagi.
    _map = {k: v for k, v in json.load(f).items() if k.startswith(_MAP_VER)}
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
  s = re.sub(r'\b(\d+)(?:st|nd|rd|th)\b', r'\1', s)  # "2nd Season" == "Season 2"
  s = re.sub(r'\bs(\d+)\b', r'season \1', s)         # "S3" == "Season 3"
  # Rentang episode "(Episode 1-170)" bukan pembeda judul → buang, biar
  # entry series utuh nggak kalah dari entry part lanjutan (Bleach TYBW
  # "Kashin-tan" dulu menang 0.80 vs entry dasar 0.73).
  s = re.sub(r'\(\s*(?:episode|eps?)\b[^)]*\)', ' ', s)
  s = re.sub(r'\b(subtitle indonesia|batch|bd|tv|movie|ova|ona)\b', ' ', s)
  s = re.sub(r'[^a-z0-9]+', ' ', s)
  return ' '.join(s.split())


def _seasons(s):
  # Nomor season/part/cour dari judul mentah ("2nd Season", "Season 2",
  # "S2", "Part 2"). Dipakai buat nolak match antar-season di _score.
  s = s.lower()
  nums = set()
  nums |= {int(n) for n in re.findall(r'\bseason\s*(\d+)', s)}
  nums |= {int(n) for n in re.findall(r'\bs(\d+)\b', s)}
  nums |= {int(n) for n in re.findall(r'\b(\d+)(?:st|nd|rd|th)\s+season', s)}
  nums |= {int(n) for n in re.findall(r'\b(?:part|cour)\s*(\d+)', s)}
  return nums


def _variants(title):
  # Otakudesu (WP search) butuh SEMUA kata cocok → "Black Clover 2nd Season"
  # balikin 0 hasil padahal "Season 2" ada. Ladder: judul asli → "Season N"
  # → judul tanpa season. Provider lain tetap dapat query asli dulu.
  out = [title]
  alt = re.sub(r'\b(\d+)(?:st|nd|rd|th)\s+season\b', r'Season \1', title, flags=re.I)
  if alt not in out:
    out.append(alt)
  base = ' '.join(_SEASON_RE.sub(' ', title).split())
  if base and base not in out:
    out.append(base)
  return out


_SEASON_RE = re.compile(r'\b(?:\d+(?:st|nd|rd|th)\s+season|season\s*\d+|s\d+|part\s*\d+|cour\s*\d+)\b', re.I)


def _score(a, b):
  raw_a, raw_b = a, b
  a, b = _norm(a), _norm(b)
  if not a or not b:
    return 0.0
  # Season mismatch → 0. "X Season 2" vs "X Season 3" beda konten walau
  # token-nya hampir sama; part/cour ikut dihitung supaya "Final Season
  # Part 2" nggak nyasar ke "Final Season".
  sa_n, sb_n = _seasons(raw_a), _seasons(raw_b)
  if sa_n and sb_n and not (sa_n & sb_n):
    return 0.0
  if a == b:
    return 1.0
  sa, sb = set(a.split()), set(b.split())
  inter = sa & sb
  if not inter:
    return 0.0
  # F1 dari recall (token query kecover?) + precision (kandidat minim
  # embel-embel?). Jaccard + bonus lama meloloskan "Bleach" vs sekuel
  # "Bleach: Sennen Kessen-hen ..." (0.47 >= threshold) → judul salah
  # ke-resolve otomatis. F1 menekan itu (<0.45) → resolve kosong → GUI
  # nawarin kandidat manual. ponytail: alias English→romaji
  # (Thousand-Year Blood War → Sennen Kessen-hen) belum ditangani.
  recall = len(inter) / len(sa)
  precision = len(inter) / len(sb)
  return 2 * recall * precision / (recall + precision)


def _ladder(plugin, title, min_score):
  # Coba query ladder sampai ada hit yang lolos min_score. Kalau nggak ada,
  # balikin hasil query pertama yang ada isinya (buat daftar kandidat).
  fallback = []
  for q in _variants(title):
    hits = plugin.search_anime(q) or []
    if not hits:
      continue
    best = max(hits, key=lambda h: _score(title, h.get('title', '')))
    if _score(title, best.get('title', '')) >= min_score:
      return hits, best
    fallback = fallback or hits
  return fallback, None


def _search_all(plugin_list, title, min_score=0.45):
  """Search all providers in parallel, return {name: (hits, best)}."""
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(plugin_list), 8)) as ex:
    futures = {ex.submit(_ladder, p, title, min_score): name for name, p in plugin_list}
    results = {}
    for f in concurrent.futures.as_completed(futures):
      results[futures[f]] = f.result()
  return results


def resolve(plugin_list, title, min_score=0.45):
  # plugin_list: [(name, plugin), ...] fallback order. Return {provider: url}
  # for every match; empty when nothing matches.
  # ponytail: prefix versi di key cache → hasil lama (dari scorer/ladder yang
  # lebih lemah) diabaikan, nggak perlu migrasi map.json.
  key = _MAP_VER + title
  if key in _map:
    return _map[key]
  results = _search_all(plugin_list, title, min_score)
  out = {}
  for name, _ in plugin_list:
    best = (results.get(name) or ([], None))[1]
    if best:
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
    hits = (results.get(name) or ([], None))[0]
    for h in hits:
      out.append((name, h['title'], h['url']))
  return out
