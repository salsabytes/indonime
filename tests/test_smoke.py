# Smoke tests (stdlib unittest only — no new deps).
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

# local HTTP server: real sockets, no mocks
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
    # defined only in megaNZ — __init__ only re-references the import
    self.assertEqual(inspect.getmodule(indonime._mega_fid).__name__, "indonime.ext.megaNZ")
    self.assertEqual(inspect.getmodule(indonime._mega_key).__name__, "indonime.ext.megaNZ")

  def test_faststart(self):
    from indonime.ext.megaNZ import _is_faststart
    # moov before mdat → faststart → can stream from the start
    faststart = b'\x00\x00\x00\x18ftypisom' + b'\x00\x00\x00\x10moov' + b'\x00\x00\x00\x10mdat'
    self.assertTrue(_is_faststart(faststart))
    # moov at the end → not faststart → must wait for the full download
    slowstart = b'\x00\x00\x00\x18ftypisom' + b'\x00\x00\x00\x10mdat' + b'\x00\x00\x00\x10moov'
    self.assertFalse(_is_faststart(slowstart))
    # no moov at all yet in the early buffer
    self.assertFalse(_is_faststart(b'\x00\x00\x00\x18ftypisom' + b'\x00\x00\x00\x10mdat'))
    # non-MP4 (mkv etc.) — the helper is only called for mp4, but stays safe
    self.assertFalse(_is_faststart(b'\x1a\x45\xdf\xa3'))

  def test_moov_complete(self):
    from indonime.ext.megaNZ import _moov_complete
    # box MP4: [4-byte size][type][payload] — ftyp=24B, moov=16B, mdat=16B
    full = (b'\x00\x00\x00\x18ftyp' + b'isom' * 4) + \
           (b'\x00\x00\x00\x10moov' + b'x' * 8) + \
           (b'\x00\x00\x00\x10mdat' + b'y' * 8)
    self.assertTrue(_moov_complete(full))
    self.assertFalse(_moov_complete(full[:30]))  # truncated moov → don't stream
    self.assertFalse(_moov_complete(b'\x00\x00\x00\x10mdat' + b'y' * 8))  # no moov
    # moov complete but mdat not in the buffer yet → still ready (stream starts)
    self.assertTrue(_moov_complete(b'\x00\x00\x00\x18ftyp' + b'isom' * 4 + b'\x00\x00\x00\x10moov' + b'x' * 8))

  @staticmethod
  def _key():
    b64 = base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode()
    return _parse_mega_url(f"https://mega.nz/file/X#{b64}")

  def test_ctr_range_decrypt(self):
    # range decrypt ≡ slice of the continuous whole-file decryptor (16-aligned)
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from indonime.ext.megaNZ import _decrypt_range
    k, iv = self._key()
    plain = bytes((i * 7) % 256 for i in range(300 * 1024))
    enc = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend()).encryptor().update(plain)
    self.assertEqual(_decrypt_range(k, iv, enc[:1024], 0), plain[:1024])
    off = 12345 & ~15
    self.assertEqual(_decrypt_range(k, iv, enc[off:off + 4096], off), plain[off:off + 4096])
    off2 = (300 * 1024 - 1000) & ~15
    self.assertEqual(_decrypt_range(k, iv, enc[off2:], off2), plain[off2:])

  def test_moov_first_rebuild(self):
    # A non-faststart MP4 (ftyp|mdat|moov) is rebuilt as faststart, AND the
    # chunk-offset table (stco) is patched by +len(moov) — without this, players
    # read data from the old offsets → decode error → mpv closes in < 1s (real regression).
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from indonime.ext.megaNZ import _decrypt_range, _write_moov_first
    k, iv = self._key()

    def box(t, payload):
      return (len(payload) + 8).to_bytes(4, "big") + t + payload

    stco = box(b"stco", b"\x00\x00\x00\x00" + (3).to_bytes(4, "big") +
               (24).to_bytes(4, "big") + (1000).to_bytes(4, "big") + (5000).to_bytes(4, "big"))
    co64 = box(b"co64", b"\x00\x00\x00\x00" + (2).to_bytes(4, "big") +
               (100000).to_bytes(8, "big") + (200000).to_bytes(8, "big"))
    trak = lambda t: box(b"trak", box(b"mdia", box(b"minf", box(b"stbl", t))))
    moov = box(b"moov", box(b"mvhd", b"\x00" * 80) + trak(stco) + trak(co64))
    ftyp = box(b"ftyp", b"isom" * 4)
    mdat = box(b"mdat", bytes((i * 13) % 256 for i in range(1_200_000)))
    plain = ftyp + mdat + moov
    size = len(plain)
    enc = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend()).encryptor().update(plain)

    def get_range(s, e):  # production get_range: s always 16-aligned
      return _decrypt_range(k, iv, enc[s:e], s)

    out = bytearray()
    marks = []
    st = _write_moov_first(k, iv, size, get_range, out.extend, lambda: marks.append(1))
    self.assertEqual(st, "done")
    self.assertEqual(marks, [1])         # header (ftyp+moov) written → ready
    out = bytes(out)
    self.assertEqual(out[:len(ftyp)], ftyp)                 # prelude intact
    self.assertEqual(out[len(ftyp) + len(moov):], mdat)     # mdat intact, just shifted
    i = out.find(b"stco")
    entries = [int.from_bytes(out[i + 12 + k * 4: i + 16 + k * 4], "big") for k in range(3)]
    self.assertEqual(entries, [24 + len(moov), 1000 + len(moov), 5000 + len(moov)])
    i2 = out.find(b"co64")
    entries64 = [int.from_bytes(out[i2 + 12 + k * 8: i2 + 20 + k * 8], "big") for k in range(2)]
    self.assertEqual(entries64, [100000 + len(moov), 200000 + len(moov)])

    # faststart MP4 → untouched (fallback, the sequential flow runs)
    plain2 = ftyp + moov + mdat
    enc2 = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend()).encryptor().update(plain2)
    out2 = bytearray()
    st2 = _write_moov_first(k, iv, len(plain2),
                            lambda s, e: _decrypt_range(k, iv, enc2[s:e], s),
                            out2.extend, lambda: None)
    self.assertEqual(st2, "fallback")
    self.assertEqual(bytes(out2), b"")

  def test_moov_first_abort(self):
    # a range fetch fails mid-mdat → 'abort' (not 'fallback'): the header
    # (ftyp+moov) was written, the rest stops — mpv plays partial, user retries
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from indonime.ext.megaNZ import _decrypt_range, _write_moov_first
    k, iv = self._key()

    def box(t, n):
      return (n + 8).to_bytes(4, "big") + t + b"x" * n

    ftyp, mdat, moov = box(b"ftyp", 16), box(b"mdat", 1_200_000), box(b"moov", 3000)
    plain = ftyp + mdat + moov
    enc = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend()).encryptor().update(plain)
    calls = [0]

    def get_range(s, e):
      calls[0] += 1
      if calls[0] > 2:  # head + tail ok, the first mdat fetch fails
        return None
      return _decrypt_range(k, iv, enc[s:e], s)

    out = bytearray()
    marks = []
    st = _write_moov_first(k, iv, len(plain), get_range, out.extend, lambda: marks.append(1))
    self.assertEqual(st, "abort")
    self.assertEqual(bytes(out), ftyp + moov)  # only the header was written
    self.assertEqual(marks, [])                # no mdat yet → ready was not called

  def test_plan_moov_first(self):
    from indonime.ext.megaNZ import _HEAD_SCAN, _TAIL_SCAN, _plan_moov_first

    def box(t, n):
      return (n + 8).to_bytes(4, "big") + t + b"x" * n

    ftyp, mdat, moov = box(b"ftyp", 16), box(b"mdat", 1_200_000), box(b"moov", 3000)
    plain = ftyp + mdat + moov
    size = len(plain)
    tail_off = max(0, size - _TAIL_SCAN) & ~15
    plan = _plan_moov_first(plain[:_HEAD_SCAN], plain[tail_off:], size, tail_off)
    self.assertEqual(plan, (len(ftyp), len(ftyp) + len(mdat), size))
    # faststart (moov at the front) → None (already streamable)
    fast = ftyp + moov + mdat
    self.assertIsNone(_plan_moov_first(fast[:_HEAD_SCAN], b"", len(fast), 0))
    # not an MP4 (no mdat) → None
    self.assertIsNone(_plan_moov_first(b"\x1a\x45\xdf\xa3" + b"x" * 100, b"", 108, 0))

class TestCompatibleServers(unittest.TestCase):
  def test_filter(self):
    dl = {"1080p": {"PixelDrain": "https://pd/x", "MEGA": "https://mega/x", "GoFile": "https://gf/x"}}
    self.assertEqual([o[0] for o in indonime._compatible_servers(dl)],
                     ["[1080p] PixelDrain", "[1080p] MEGA"])

class TestEpisodeNav(unittest.TestCase):
  # 15 episodes: exercises tuiko-driven episode pick + post-play loop (no TTY, key_source)
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
    # ctrl-d → multiselect → ctrl-a selects ALL episodes → enter → all queued.
    # First pick runs sequential (quality prompt), the rest in parallel — so
    # assert on the set of titles, not the completion order.
    calls = []
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or ("1080p", 100, None)
    try:
      self.assertEqual(self._nav(["ctrl-d", "ctrl-a", "escape"]), "back")
      self.assertEqual({c[0][0] for c in calls}, {f"Ep {i}" for i in range(15)})
      self.assertEqual(calls[0][1].get("quality"), None)  # first pick prompts
      self.assertEqual({c[1].get("quality") for c in calls[1:]}, {"1080p"})  # workers reuse
    finally:
      indonime._download_episode = orig

  def test_download_retry_after_failure(self):
    # EP1 fails twice then succeeds → auto-retried (_DL_RETRIES), queue still OK.
    calls = []
    fails = {"Ep 1": 2}
    def fake(title, *a, **k):
      calls.append((title, k))
      if fails.get(title, 0) > 0:
        fails[title] -= 1
        return (k.get("quality"), 0, "Download failed")  # real code keeps the picked quality
      return ("1080p", 100, None)
    orig = indonime._download_episode
    indonime._download_episode = fake
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0] for c in calls], ["Ep 0", "Ep 1", "Ep 1", "Ep 1"])
      self.assertEqual([c[1].get("quality") for c in calls], [None, "1080p", "1080p", "1080p"])
    finally:
      indonime._download_episode = orig

  def test_download_exhausted_retries_fail(self):
    # EP1 always fails → retried _DL_RETRIES times then recorded as failed.
    calls = []
    orig = indonime._download_episode
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or (None, 0, "Download failed")
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], ["Ep 0", "Ep 0", "Ep 0", "Ep 1", "Ep 1", "Ep 1"])
    finally:
      indonime._download_episode = orig

  def test_download_first_episode_failure_recorded(self):
    # First pick exhausts retries → quality stays None → worker (Ep 1) picks
    # its own source quietly; queue continues and both episodes are attempted.
    calls = []
    fails = {"Ep 0": 99}
    def fake(title, *a, **k):
      calls.append((title, k))
      if fails.get(title, 0) > 0:
        fails[title] -= 1
        return (None, 0, "No sources")
      return ("1080p", 100, None)
    orig = indonime._download_episode
    indonime._download_episode = fake
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual({c[0] for c in calls}, {"Ep 0", "Ep 1"})
      self.assertEqual([c[1].get("quality") for c in calls], [None] * 4)  # no quality ever resolved
      self.assertTrue(all(c[1].get("quiet") is True for c in calls if c[0] == "Ep 1"))  # worker never prompts
    finally:
      indonime._download_episode = orig

  def test_download_skip_already_downloaded(self):
    # An episode whose file already exists in ~/Downloads is skipped entirely.
    calls = []
    orig_dl = indonime._download_episode
    orig_skip = indonime._already_downloaded
    indonime._download_episode = lambda *a, **k: calls.append((a, k)) or ("1080p", 100, None)
    indonime._already_downloaded = lambda title: title == "Ep 1"
    try:
      self.assertEqual(self._nav(["ctrl-d", "space", "down", "space", "enter", "escape"]), "back")
      self.assertEqual([c[0][0] for c in calls], ["Ep 0"])  # Ep 1 skipped
    finally:
      indonime._download_episode = orig_dl
      indonime._already_downloaded = orig_skip

  def test_download_cancel_stops_queue(self):
    # user cancels at the quality prompt (sentinel) → the queue stops immediately
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

# list_all() parses the anime-list pages without network (patched fetch_soup).
class TestCatalogParsing(unittest.TestCase):
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

# Live fuzzy search: type keys → filter catalog → enter picks the match.
class TestCatalogSelect(unittest.TestCase):
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
