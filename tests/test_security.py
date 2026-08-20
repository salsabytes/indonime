# Security guards: redirect allowlist + script end-tag regex.
# No network beyond a local throwaway HTTP server.
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from indonime.ext.gdrive import _SCRIPT_RE
from indonime.plugins import _base


class _Redirector(BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path == '/hop':
      self.send_response(200)
      self.end_headers()
      self.wfile.write(b'ok')
    else:
      self.send_response(302)
      self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/hop')
      self.end_headers()

  def log_message(self, *a):
    pass


def test_redirect_hop_is_guarded():
  srv = HTTPServer(('127.0.0.1', 0), _Redirector)
  threading.Thread(target=srv.serve_forever, daemon=True).start()
  try:
    base = f'http://127.0.0.1:{srv.server_port}'
    def allow(url):
      return url.startswith(base) and not url.endswith('/hop')
    orig = _base._url_allowed
    _base._url_allowed = allow
    try:
      _base.http_get(base + '/')
    except Exception as e:
      assert type(e).__name__ == 'HTTPError', f'unexpected: {e!r}'
    else:
      raise AssertionError('redirect to disallowed host was followed')
    finally:
      _base._url_allowed = orig
  finally:
    srv.shutdown()


def test_script_regex_matches_whitespace_end_tag():
  html = '<script>var x=1;</script\n\t bar>'
  assert _SCRIPT_RE.findall(html) == ['var x=1;']
  assert _SCRIPT_RE.findall('<script src="x.js"></script>') == []


if __name__ == '__main__':
  test_redirect_hop_is_guarded()
  test_script_regex_matches_whitespace_end_tag()
  print('test_security OK')