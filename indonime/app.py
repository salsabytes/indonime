# pywebview GUI entry: WebView2 check/repair → local API server → window.
import os
import sys


def _stdio_fix():
  if sys.stdout is None or sys.stderr is None:  # --noconsole build
    d = os.path.join(os.path.expanduser('~'), '.indonime')
    os.makedirs(d, exist_ok=True)
    sys.stdout = sys.stderr = open(os.path.join(d, 'gui.log'), 'a',
                                   encoding='utf-8', buffering=1)


_stdio_fix()

import subprocess
import tempfile
import urllib.request

# WebView2 Evergreen runtime registration key (same GUID across users).
_CLIENT_KEY = r'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
_BOOTSTRAP_URL = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'


def _webview2_present():
  if sys.platform != 'win32':
    return True
  import winreg
  subs = ('SOFTWARE\\WOW6432Node\\' + _CLIENT_KEY, 'SOFTWARE\\' + _CLIENT_KEY)
  for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
    for sub in subs:
      try:
        with winreg.OpenKey(hive, sub) as k:
          if winreg.QueryValueEx(k, 'pv')[0]:
            return True
      except OSError:
        pass
  return False


def _install_webview2():
  from ctypes import windll
  windll.user32.MessageBoxW(0, 'WebView2 runtime tidak ditemukan — '
                             'menginstal otomatis...', 'Indonime', 0x40)
  dst = os.path.join(tempfile.gettempdir(), 'webview2-setup.exe')
  try:
    urllib.request.urlretrieve(_BOOTSTRAP_URL, dst)  # nosec B310: hardcoded Microsoft fwlink
    subprocess.run([dst, '--silent', '--install'], check=True)
  except Exception as e:
    print(f'WebView2 auto-install gagal: {e}', file=sys.stderr)
  finally:
    if os.path.exists(dst):
      os.remove(dst)
  if not _webview2_present():
    windll.user32.MessageBoxW(0, 'Instalasi WebView2 gagal. Install manual: '
                             'https://developer.microsoft.com/microsoft-edge/webview2/',
                             'Indonime', 0x10)


def main():
  dev = '--dev' in sys.argv
  if not _webview2_present():
    _install_webview2()

  from indonime.server import _STATIC_DIR, start_server
  port = start_server(port=8756 if dev else 0,
                      static_dir=str(_STATIC_DIR))
  import webview
  url = f'http://127.0.0.1:{port}/'
  if dev:
    print(f'Debug: http://127.0.0.1:{port}  (chrome://inspect untuk DevTools)')
  win = webview.create_window('Indonime', url, width=1180, height=800, min_size=(960, 640))
  webview.start(debug=dev)


if __name__ == '__main__':
  main()