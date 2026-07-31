# Smoke tests for ponytail-audit refactors (stdlib unittest only — no new deps).
# Run: python -m unittest discover -s tests -v
import base64
import http.server
import inspect
import json
import os
import sys
import threading
import unittest
import urllib.error
from types import SimpleNamespace

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

# ── fake InquirerPy select: exercises _episode_nav kb wiring without a TTY ──
class FakeSelect:
  def __init__(self, result="back", **kw):
    self._result = result
    self.content_control = SimpleNamespace(selection={"value": None}, choices=[], _selected_choice_index=0)
    self.kb_func_lookup = {}
    self._message = ""
    self._handle_enter = None

  def register_kb(self, name):
    def deco(fn):
      self.kb_func_lookup[name] = fn
      return fn
    return deco

  def execute(self):
    return self._result

class FakeEvent:
  app = SimpleNamespace(invalidate=lambda: None)

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
    self.assertEqual([o["name"] for o in indonime._compatible_servers(dl)],
                     ["[1080p] PixelDrain", "[1080p] MEGA"])

class TestEpisodeNav(unittest.TestCase):
  # 15 eps / 2 pages: exercises enter-patch, _change_page, _jump_to, backspace
  EPS = [{"title": f"Ep {i}", "url": f"u{i}"} for i in range(15)]

  def _nav(self):
    captured = []
    orig = indonime.inquirer.select
    indonime.inquirer.select = lambda **kw: (captured.append(FakeSelect("back", **kw)) or captured[-1])
    try:
      self.assertEqual(indonime._episode_nav(self.EPS, plugin=None, custom_style=None, show_banner=False), "back")
    finally:
      indonime.inquirer.select = orig
    return captured[-1]

  def test_next_prev_and_jump(self):
    sel = self._nav()
    ctl = sel.content_control
    ctl.selection = {"value": "__next__"}
    sel._handle_enter(FakeEvent())
    vals = [ch["value"] for ch in ctl.choices]
    self.assertIn("__prev__", vals)
    self.assertNotIn("__next__", vals)
    sel.kb_func_lookup["left"](FakeEvent())
    sel.kb_func_lookup["3"](FakeEvent())
    self.assertEqual(ctl._selected_choice_index, 2)
    sel.kb_func_lookup["backspace"](FakeEvent())
    self.assertEqual(sel._message, "▶  Select episode:")

class TestMainDispatch(unittest.TestCase):
  def test_modes(self):
    calls = []
    indonime._one_shot_mode = lambda q, p, m: calls.append((q, p, m))
    indonime._tui_loop = lambda: calls.append(("tui",))
    sys.argv = ["indonime", "search", "naruto", "shippuden", "-d"]
    indonime.main()
    self.assertEqual(calls[-1], ("naruto shippuden", "otakudesu", "download"))
    sys.argv = ["indonime", "search", "naruto", "-p", "anoboy"]
    indonime.main()
    self.assertEqual(calls[-1], ("naruto", "anoboy", "play"))
    sys.argv = ["indonime"]
    indonime.main()
    self.assertEqual(calls[-1], ("tui",))

class TestDeletedSymbols(unittest.TestCase):
  def test_gone(self):
    self.assertFalse(hasattr(ui, "print_info"))
    self.assertFalse(hasattr(indonime, "_search_mode"))
    self.assertFalse(hasattr(indonime, "_download_mode"))

if __name__ == "__main__":
  unittest.main()
