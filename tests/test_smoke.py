# Smoke tests for ponytail-audit refactors (stdlib unittest only — no new deps).
# Run: python -m unittest discover -s tests -v
import base64
import http.server
import inspect
import io
import json
import os
import sys
import threading
import unittest
import urllib.error
from contextlib import nullcontext

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)

import indonime
import indonime.ui as ui
from indonime.plugins._base import (fetch_soup, http_get, http_head,
                                    http_post_json, http_stream, resolve_url)
from indonime.ext.megaNZ import _mega_fid, _mega_key, _parse_mega_url

# ── local HTTP server: real sockets, no mocks ──
class _H(http.server.BaseHTTPRequestHandler):
  def log_message(self, *a):
    pass

  def _send(self, code, ctype, body):
    self.send_response(code)
    self.send_header("Content-Type", ctype)
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    if self.command != "HEAD":
      self.wfile.write(body)

  def do_GET(self):
    if self.path == "/ok":
      self._send(200, "text/plain", b"ok")
    elif self.path == "/r":
      self.send_response(302)
      self.send_header("Location", "/ok")
      self.end_headers()
    elif self.path == "/bin":
      self._send(200, "application/octet-stream", b"x" * (3 * 1024 * 1024))
    elif self.path == "/page":
      self._send(200, "text/html", b"<html><body><h1>Judul</h1></body></html>")
    elif self.path == "/echo":
      self._send(200, "application/json", b'{"a": 1}')
    else:
      self._send(404, "text/plain", b"nope")

  do_HEAD = do_GET

  def do_POST(self):
    if self.path == "/echo":
      n = int(self.headers.get("Content-Length", 0))
      data = json.loads(self.rfile.read(n))
      self._send(200, "application/json", json.dumps({"got": data}).encode())
    else:
      self._send(404, "text/plain", b"nope")

_SRV = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H)
threading.Thread(target=_SRV.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{_SRV.server_address[1]}"

def tearDownModule():
  _SRV.shutdown()

class TestHttpLayer(unittest.TestCase):
  def test_get(self):
    u, st, _, body = http_get(BASE + "/ok")
    self.assertEqual(st, 200)
    self.assertEqual(body, b"ok")

  def test_redirect_resolve(self):
    self.assertTrue(resolve_url(BASE + "/r").endswith("/ok"))

  def test_head(self):
    st, ct = http_head(BASE + "/bin")
    self.assertEqual(st, 200)
    self.assertTrue(ct.startswith("application/octet-stream"))

  def test_post_json(self):
    self.assertEqual(http_post_json(BASE + "/echo", {"a": 1}, timeout=5), {"got": {"a": 1}})

  def test_stream_chunks(self):
    with http_stream(BASE + "/bin", timeout=10) as r:
      total = int(r.headers.get("Content-Length", 0))
      self.assertEqual(total, 3 * 1024 * 1024)
      got = 0
      while True:
        c = r.read(65536)
        if not c:
          break
        got += len(c)
      self.assertEqual(got, total)

  def test_fetch_soup(self):
    self.assertEqual(fetch_soup(BASE + "/page").find("h1").text, "Judul")

  def test_http_error_raises(self):
    with self.assertRaises(urllib.error.HTTPError) as ctx:
      http_get(BASE + "/missing")
    self.assertEqual(ctx.exception.code, 404)

class TestMegaParser(unittest.TestCase):
  def test_fid(self):
    self.assertEqual(_mega_fid("https://mega.nz/file/ABC123#key")[1], "ABC123")

  def test_key_formats(self):
    self.assertEqual(_mega_key("https://mega.nz/file/ABC123#k1!k2"), "k2")
    self.assertEqual(_mega_key("https://mega.nz/#!ABC!KEY"), "KEY")

  def test_parse_roundtrip(self):
    b64key = base64.urlsafe_b64encode(b"A" * 32).decode().rstrip("=")
    k, iv = _parse_mega_url(f"https://mega.nz/file/ABC123#{b64key}")
    self.assertEqual(len(k), 16)
    self.assertEqual(len(iv), 16)

  def test_single_home(self):
    # definisi cuma di megaNZ — di __init__ cuma reference import
    self.assertEqual(inspect.getmodule(indonime._mega_fid).__name__, "indonime.ext.megaNZ")
    self.assertEqual(inspect.getmodule(indonime._mega_key).__name__, "indonime.ext.megaNZ")

class TestCompatibleServers(unittest.TestCase):
  def test_filter(self):
    dl = {"1080p": {"PixelDrain": "https://pd/x", "MEGA": "https://mega/x", "GoFile": "https://gf/x"}}
    self.assertEqual([o[0] for o in indonime._compatible_servers(dl)],
                     ["[1080p] PixelDrain", "[1080p] MEGA"])

class TestEpisodeNav(unittest.TestCase):
  # 15 eps: exercises tuiko-driven episode pick + post-play loop (no TTY, key_source)
  EPS = [{"title": f"Ep {i}", "url": f"u{i}"} for i in range(15)]

  def _nav(self, keys):
    out = io.StringIO()
    return indonime._episode_nav(self.EPS, plugin=None, show_banner=False,
                                 key_source=iter(keys), out=out)

  def test_back_on_escape(self):
    self.assertEqual(self._nav(["escape"]), "back")

  def test_select_first_then_quit(self):
    # enter picks EP1 → post-play: QUIT is index 3 (NEXT/REPLAY/QUALITY/QUIT)
    orig = indonime._play_episode
    indonime._play_episode = lambda *a, **k: (True, None)
    try:
      self.assertEqual(self._nav(["enter", "down", "down", "down", "enter"]), "quit")
    finally:
      indonime._play_episode = orig

  def test_postplay_next_loops(self):
    # EP1 (enter) → NEXT (enter) → EP2 → QUIT (down x4, enter)
    calls = []
    orig = indonime._play_episode
    indonime._play_episode = lambda *a, **k: calls.append(a) or (True, None)
    try:
      self.assertEqual(self._nav(["enter", "enter", "down", "down", "down", "down", "enter"]), "quit")
      self.assertEqual([c[0] for c in calls], ["u0", "u1"])
    finally:
      indonime._play_episode = orig

  def test_download_shortcut_multiselect(self):
    # ctrl-d → multiselect → space marks EP1, down+space marks EP2, enter downloads both;
    # quality picked once on EP1, reused for EP2 (queue)
    calls = []
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or ("1080p", 100, None)
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], ["Ep 0", "Ep 1"])
      self.assertEqual([c[1].get("quality") for c in calls], [None, "1080p"])
    finally:
      indonime._download_episode = orig

  def test_download_shortcut_select_all(self):
    # ctrl-d → multiselect → ctrl-a pilih SEMUA episode → enter → semua masuk queue
    calls = []
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or ("1080p", 100, None)
    try:
      self.assertEqual(self._nav(["ctrl-d", "ctrl-a", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], [f"Ep {i}" for i in range(15)])
    finally:
      indonime._download_episode = orig

  def test_download_shortcut_skips_failure(self):
    # EP1 ok → EP2 gagal (None, 0) → queue tetap lanjut, summary 1 berhasil + 1 gagal
    calls = []
    returns = iter([("1080p", 100, None), (None, 0, "Download failed")])
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or next(returns)
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], ["Ep 0", "Ep 1"])
      self.assertEqual([c[1].get("quality") for c in calls], [None, "1080p"])
    finally:
      indonime._download_episode = orig

  def test_download_first_episode_failure_recorded(self):
    # EP1 gagal (bukan cancel) → tetap dicatat, queue lanjut ke EP2
    calls = []
    returns = iter([(None, 0, "No sources"), ("1080p", 100, None)])
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or next(returns)
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], ["Ep 0", "Ep 1"])
      self.assertEqual([c[1].get("quality") for c in calls], [None, None])
    finally:
      indonime._download_episode = orig

  def test_download_cancel_stops_queue(self):
    # user batal di prompt quality (sentinel) → queue langsung berhenti
    calls = []
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or (indonime._CANCEL, 0, "Dibatalkan")
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "enter", "escape"]), "back")
      self.assertEqual(len(calls), 1)
    finally:
      indonime._download_episode = orig

class TestMainDispatch(unittest.TestCase):
  def test_modes(self):
    calls = []
    indonime._one_shot_mode = lambda q, p, m: calls.append((q, p, m))
    indonime._tui_loop = lambda: calls.append(("tui",))
    # session() needs a real TTY (termios raw mode) — neutralize it in tests
    orig_session = indonime.session
    indonime.session = lambda: nullcontext()
    try:
      sys.argv = ["indonime", "search", "naruto", "shippuden", "-d"]
      indonime.main()
      self.assertEqual(calls[-1], ("naruto shippuden", "otakudesu", "download"))
      sys.argv = ["indonime", "search", "naruto", "-p", "anoboy"]
      indonime.main()
      self.assertEqual(calls[-1], ("naruto", "anoboy", "play"))
      sys.argv = ["indonime"]
      indonime.main()
      self.assertEqual(calls[-1], ("tui",))
    finally:
      indonime.session = orig_session

class TestDeletedSymbols(unittest.TestCase):
  def test_gone(self):
    self.assertFalse(hasattr(ui, "print_info"))
    self.assertFalse(hasattr(ui, "make_style"))
    self.assertFalse(hasattr(indonime, "inquirer"))
    self.assertFalse(hasattr(indonime, "_search_mode"))
    self.assertFalse(hasattr(indonime, "_download_mode"))

class TestCatalogParsing(unittest.TestCase):
  """list_all() parses the anime-list pages without network (patched fetch_soup)."""
  def setUp(self):
    from indonime.plugins._base import cache_clear
    cache_clear()
    from indonime.plugins import anoboy, otakudesu
    self._orig = {'anoboy': anoboy.fetch_soup, 'otakudesu': otakudesu.fetch_soup}

  def tearDown(self):
    from indonime.plugins import anoboy, otakudesu
    anoboy.fetch_soup = self._orig['anoboy']
    otakudesu.fetch_soup = self._orig['otakudesu']

  def test_otakudesu(self):
    from bs4 import BeautifulSoup
    from indonime.plugins import otakudesu
    html = '''<ul>
      <li><a href="https://otakudesu.blog/anime/naruto-sub-indo/">Naruto Shippuden</a></li>
      <li><a href="https://otakudesu.blog/anime/one-piece-sub-indo/">One Piece</a></li>
      <li><a href="https://otakudesu.blog/">Home</a></li>
    </ul>'''
    otakudesu.fetch_soup = lambda url: BeautifulSoup(html, 'html.parser')
    out = otakudesu.list_all()
    self.assertEqual(out, [
      {'title': 'Naruto Shippuden', 'url': 'https://otakudesu.blog/anime/naruto-sub-indo/'},
      {'title': 'One Piece', 'url': 'https://otakudesu.blog/anime/one-piece-sub-indo/'},
    ])

  def test_cache_separated_per_plugin(self):
    # regression: otakudesu.list_all and anoboy.list_all must NOT share a cache
    # slot (cached() key includes fn.__module__) — no cache_clear in between
    from bs4 import BeautifulSoup
    from indonime.plugins import otakudesu, anoboy
    otakudesu.fetch_soup = lambda url: BeautifulSoup(
      '<ul><li><a href="https://otakudesu.blog/anime/naruto-sub-indo/">Naruto</a></li></ul>',
      'html.parser')
    anoboy.fetch_soup = lambda url: BeautifulSoup(
      '<ul><li><a href="/anime/spy-x-family/">Spy x Family</a></li></ul>',
      'html.parser')
    o = otakudesu.list_all()
    a = anoboy.list_all()  # must NOT return otakudesu's cached catalog
    self.assertEqual(o[0]['url'], 'https://otakudesu.blog/anime/naruto-sub-indo/')
    self.assertEqual(a[0]['url'], 'https://anoboy7.com/anime/spy-x-family/')

  def test_anoboy_relative_urls(self):
    from bs4 import BeautifulSoup
    from indonime.plugins import anoboy
    html = '''<div class="anime-list"><ul>
      <li><a href="/anime/oshi-no-ko-2nd-season/">Oshi no Ko 2nd Season</a></li>
      <li><a href="/anime/spy-x-family/">Spy x Family</a></li>
      <li><a href="/">Home</a></li>
    </ul></div>'''
    anoboy.fetch_soup = lambda url: BeautifulSoup(html, 'html.parser')
    out = anoboy.list_all()
    self.assertEqual(out, [
      {'title': 'Oshi no Ko 2nd Season', 'url': 'https://anoboy7.com/anime/oshi-no-ko-2nd-season/'},
      {'title': 'Spy x Family', 'url': 'https://anoboy7.com/anime/spy-x-family/'},
    ])

class TestCatalogSelect(unittest.TestCase):
  """Live fuzzy search: type keys → filter catalog → enter picks the match."""
  class _Plugin:
    CATALOG = [
      {'title': 'Naruto Shippuden', 'url': 'u1'},
      {'title': 'One Piece', 'url': 'u2'},
      {'title': 'Spy x Family', 'url': 'u3'},
      {'title': 'Kimetsu no Yaiba', 'url': 'u4'},
    ]
    def list_all(self):
      return self.CATALOG
    def episodes(self, url):
      return [{'title': 'EP1', 'url': url + '/ep1'}]
    def search_anime(self, query):
      return [self.CATALOG[0]]

  def _pick(self, keys):
    out = io.StringIO()
    return indonime._catalog_select(self._Plugin(), key_source=iter(keys), out=out)

  def test_live_fuzzy_no_enter_needed(self):
    # 'sxf' fuzzy-matches "Spy x Family" (subsequence), then enter picks it
    hit = self._pick(['s', 'x', 'f', 'enter'])
    self.assertEqual(hit, ('u3', [{'title': 'EP1', 'url': 'u3/ep1'}]))

  def test_escape_aborts(self):
    self.assertEqual(self._pick(['escape']), 'abort')

  def test_abort_sentinel(self):
    # 4 items + ABORT = 5 rows on one page; scroll to last (ABORT) and enter
    hit = self._pick(['down', 'down', 'down', 'down', 'enter'])
    self.assertEqual(hit, 'abort')

  def _pick_with_shortcuts(self, keys):
    out = io.StringIO()
    return indonime._catalog_select(self._Plugin(), key_source=iter(keys), out=out,
                                    shortcuts=indonime._SHORTCUTS)

  def test_provider_shortcut(self):
    self.assertEqual(self._pick_with_shortcuts(['ctrl-b']), 'provider')

  def test_unknown_shortcut_action_passthrough(self):
    out = io.StringIO()
    res = indonime._catalog_select(self._Plugin(), key_source=iter(['ctrl-t']), out=out,
                                   shortcuts={'ctrl-t': 'whatever'})
    self.assertEqual(res, 'whatever')

  def test_search_and_select_one_shot(self):
    # one-shot CLI path (query given) — regression: used to call the removed
    # tuiko progress() and would NameError at runtime
    out = io.StringIO()
    hit = indonime._search_and_select(self._Plugin(), "naruto",
                                      key_source=iter(['enter']), out=out)
    self.assertEqual(hit, ('u1', [{'title': 'EP1', 'url': 'u1/ep1'}]))

if __name__ == "__main__":
  unittest.main()
