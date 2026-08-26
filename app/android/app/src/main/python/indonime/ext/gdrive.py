# GDrive resolver: xtwap direct MP4 + gdplayer.to API decrypt.
# xtwap: page carries a /download/file link serving video/mp4 straight up.
# gdplayer.to: AAEncode blob → octal-unescape → packed JS → apx/ps/pd/kaken/qsx
#   vars → GET config + POST sources (AES-CBC) → dcx decrypt → video URL.
# The final stream-vid URL is often WAF-gated (text/html to HEAD probes). The
# HEAD check below keeps the app from launching mpv into a dead link.
import base64
import html as _html
import json
import re
import urllib.parse

from ..plugins._base import HEADERS, _open, http_get, http_head
from ..ui import Palette
from tuiko import style

# Inline scripts: no src attr, content up to the closing tag. The end-tag
# allows trailing whitespace/attrs — `</script\n bar>` must still terminate.
_SCRIPT_RE = re.compile(r'<script(?![^>]*src)[^>]*>([\s\S]*?)</script\s*[^>]*>',
                        re.IGNORECASE)


# ── AAEncode decoder (gdplayer page obfuscation) ──────────────────────────────

def _eval_term(expr):
  # digits-only arithmetic after charset substitution; safe: no identifiers left
  e = expr.replace('(ﾟΘﾟ)', '1').replace('(ﾟｰﾟ)', '4') \
          .replace('(o^_^o)', '3').replace('(c^_^o)', '0') \
          .replace('(ﾟωﾟﾉ)', '0').replace(' ', '')
  return eval(e, {'__builtins__': {}}, {})


def _split_top(expr):
  # split on '+' at top level only (parens may nest '+')
  parts, depth, cur = [], 0, ''
  for ch in expr:
    if ch == '(':
      depth += 1
    elif ch == ')':
      depth -= 1
    if ch == '+' and depth == 0:
      parts.append(cur)
      cur = ''
      continue
    cur += ch
  if cur.strip():
    parts.append(cur)
  return parts


def _aa_payload(script):
  # Decode the AAEncode script → the octal-escaped 'return"..."' literal.
  marker = "(ﾟДﾟ) [ﾟoﾟ]='\\\"';"
  i = script.find(marker)
  if i == -1:
    raise ValueError('AAEncode marker not found')
  tail = script[i + len(marker):]
  end = tail.find("('_');")
  if end == -1:
    raise ValueError("('_'); terminator not found")
  expr = tail[:end]
  expr = expr.replace('ﾟεﾟ+/*´∇｀*/', 'return+')
  expr = expr.replace('(ﾟДﾟ)[ﾟoﾟ]', 'Q')
  expr = expr.replace('(ﾟДﾟ)[ﾟεﾟ]', 'N')
  first = expr.find("['_'] (")
  expr = expr[expr.find("['_'] (", first + 1) + len("['_'] (") :]

  out = ''
  for tok in _split_top(expr):
    tok = tok.strip()
    if not tok:
      continue
    if tok == 'return':
      out += 'return'
    elif tok == 'Q':
      out += '"'
    elif tok == 'N':
      out += '\\'
    else:
      # left-assoc JS concat: every term appends its digit string
      e = tok.replace('(ﾟΘﾟ)', '1').replace('(ﾟｰﾟ)', '4') \
             .replace('(o^_^o)', '3').replace('(c^_^o)', '0') \
             .replace('(ﾟωﾟﾉ)', '0').replace(' ', '')
      if not re.fullmatch(r'[\d+\-()]+', e):
        continue  # closing-call junk
      out += str(_eval_term(tok))
  return out


def _oct_unescape(s):
  # JS sloppy-mode \\<octal> escapes, 1-3 digits; 8/9 terminates the escape.
  out = ''
  i, n = 0, len(s)
  while i < n:
    c = s[i]
    if c == '\\' and i + 1 < n and s[i + 1] in '01234567':
      j = i + 1
      digits = ''
      while j < n and len(digits) < 3 and s[j] in '01234567' \
          and int(s[i + 1:j + 1], 8) <= 255:
        digits += s[j]
        j += 1
      out += chr(int(digits, 8))
      i = j
      continue
    out += c
    i += 1
  return out


# ── Dean Edwards packer (second obfuscation layer) ───────────────────────────

_DIGITS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def _to_base(n, base):
  out = ''
  while n >= base:
    out = _DIGITS[n % base] + out
    n //= base
  return _DIGITS[n] + out


def _unpack(packed):
  # Extract the (CODE, base, count, 'word|word|...') args and de-dupe the code.
  m = re.search(r",(\d+),(\d+),'([^']*)'\.split\('\|'\)\)+.*$", packed, re.S)
  if not m:
    raise ValueError('packer args not found')
  raw = packed[packed.rfind('(', 0, m.start()) + 1: m.start()].strip("'")
  base, count, words = int(m.group(1)), int(m.group(2)), m.group(3).split('|')
  for i in range(count - 1, -1, -1):
    if i < len(words) and words[i]:
      raw = re.sub(r'\b' + _to_base(i, base) + r'\b', words[i], raw)
  return raw


def _vars_from_packed(packed):
  # oct literal ('return"...') → packed JS → the window var dict.
  body = _oct_unescape(packed[len('return"'):-1])
  code = _unpack(body)
  return dict(re.findall(r'(?:window\.)?([A-Za-z_]\w*)="([^"]*)"', code))


def _page_vars(script):
  # Full chain: AAEncode script → window.apx/ps/pd/kaken/qsx dict.
  return _vars_from_packed(_aa_payload(script))


# ── AES decrypt (dcx): PBKDF2-SHA256 ×10000 → AES-256-CBC, PKCS7 ─────────────

def _dcx(pd_num, b64_blob):
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
  from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
  from cryptography.hazmat.primitives import hashes

  raw = base64.b64decode(b64_blob)
  salt, ct = raw[:16], raw[16:]
  kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=48, salt=salt, iterations=10000)
  derived = kdf.derive(str(pd_num).encode())
  key, iv = derived[:32], derived[32:]
  dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
  out = dec.update(ct) + dec.finalize()
  pad = out[-1]
  if not (1 <= pad <= 16 and out[-pad:] == bytes([pad]) * pad):
    raise ValueError('bad PKCS7 pad')
  return out[:-pad].decode('utf-8')


def _video_url(url):
  # HEAD gate: reject hard failures (4xx/5xx) but accept 2xx even when the
  # upstream WAF returns text/html to HEAD probes (common with stream-vid CDN).
  try:
    status, _ = http_head(url, timeout=10)
    return url if 200 <= status < 300 else None
  except Exception:
    return None


def _xtwap_url(url):
  # dl.xtwap.top/download/?link=... → /download/file?s=..&t=.. → direct MP4.
  _, _, _, body = http_get(url, timeout=15)
  m = re.search(r'href="(/download/file[^"]+)"', body.decode('utf-8', 'replace'))
  if not m:
    return None
  return urllib.parse.urljoin(url, m.group(1).replace('&amp;', '&'))


def _gdplayer_url(url):
  # Full API flow: page vars → config → sources → decrypted video URL.
  _, _, _, body = http_get(url, timeout=15)
  html = body.decode('utf-8', 'replace')
  # gdplayer.to/embed2 now returns an auto-submit form (POST to /x/...).
  # The AAEncode script lives on the POST response — follow it once.
  form_m = re.search(r'<form[^>]+action="([^"]+)"', html, re.I)
  if form_m:
    form_url = urllib.parse.unquote(form_m.group(1))
    form_data = urllib.parse.urlencode({'referer': ''}).encode()
    form_h = {**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded',
              'Referer': url}
    with _open(form_url, timeout=15, method='POST',
               headers=form_h, data=form_data) as r:
      html = r.read().decode('utf-8', 'replace')
  scripts = _SCRIPT_RE.findall(html)
  if not scripts:
    return None
  vars_ = _page_vars(max(scripts, key=len))
  apx = base64.b64decode(vars_.get('apx', '')).decode('utf-8', 'replace')
  if not apx or 'apx' not in vars_:
    return None
  ps, kaken, pd = vars_['ps'], vars_['kaken'], vars_['pd']

  headers = {'User-Agent': _HEADERS_USER_AGENT, 'Referer': url}
  # Route through _open so the host allowlist + redirect guard apply (these
  # API hosts are gdplayer.to — already allowlisted).
  cfg_url = f'{apx}{vars_["qsx"]}/?p={ps}'
  with _open(cfg_url, timeout=15, headers=headers) as r:
    cfg = _dcx(pd, r.read().decode())
  json.loads(cfg)  # validates decrypt; config itself unused

  api = apx.replace('-config', '')
  data = kaken.encode()
  hdrs = {**headers, 'Content-Type': 'text/plain'}
  api_url = api + f'?p={ps}'
  with _open(api_url, timeout=15, method='POST', headers=hdrs, data=data) as r:
    sources = json.loads(_dcx(pd, r.read().decode()))
  files = [_html.unescape(s['file']) for s in sources.get('sources', []) if s.get('file')]
  return files[0] if files else None


_HEADERS_USER_AGENT = (
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
  'AppleWebKit/537.36 (KHTML, like Gecko) '
  'Chrome/120.0.0.0 Safari/537.36'
)


def scrape(url):
  try:
    if 'xtwap' in url.lower():
      target = _xtwap_url(url)
      if target is None:
        print(style("⚠ GDrive: link download tidak ditemukan", Palette.warning))
      return _video_url(target) if target else None
    if 'gdplayer' in url.lower():
      target = _gdplayer_url(url)
      if target is None:
        print(style("⚠ GDrive stream tidak tersedia (server may be gated)", Palette.warning))
      return _video_url(target) if target else None
    print(style(f"⚠ Bukan link GDrive: {url[:60]}", Palette.warning))
    return None
  except Exception as e:
    print(style(f"✘ Network Error: {e}", Palette.error))
    return None
