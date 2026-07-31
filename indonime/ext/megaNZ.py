"""MEGA stream decrypt — reused cipher + prefetch thread."""
import random
import sys
import base64
import threading
import queue
import tempfile

from ..plugins._base import http_post_json, http_stream

# ── AES via cryptography (hard dep) ──────────
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def mega_base64_decode(data):
  data += '=' * (4 - len(data) % 4)
  return base64.urlsafe_b64decode(data)


def _mega_fid(url):
  """Extract file ID from MEGA URL. Handles #! format. Returns (clean_url, f_id)."""
  clean = url.replace("#!", "file/").replace("!", "#", 1) if "#!" in url else url
  try:
    return clean, clean.split("file/")[1].split("#")[0]
  except IndexError:
    return None, None


def _mega_key(url):
  """Extract decryption key from MEGA URL fragment."""
  if "#" in url:
    frag = url.split("#")[-1]
    if "!" in frag:
      return frag.split("!")[-1]
    return frag
  return None


def _parse_mega_url(url):
  """Parse MEGA URL → (key, iv)."""
  try:
    parts = url.split("#")
    encoded_key = parts[1]
    full_key = mega_base64_decode(encoded_key)
    k = bytes(full_key[i] ^ full_key[i + 16] for i in range(16))
    iv = full_key[16:24] + b"\x00" * 8
    return k, iv
  except Exception:
    return None


def _fetch_file_info(file_id):
  """MEGA API → (dl_link, file_size)."""
  try:
    seq = random.randint(0, 0xFFFFFFFF)
    res = http_post_json(
      f"https://g.api.mega.co.nz/cs?id={seq}",
      [{"a": "g", "g": 1, "p": file_id}],
      timeout=15,
    )
    if isinstance(res[0], int):
      err = res[0]
      err_names = {-1:"internal",-2:"invalid",-3:"retry",-4:"rate-limited",
                   -5:"denied",-6:"not found",-7:"inaccessible",-8:"quota",
                   -9:"bad key",-11:"logged out",-13:"expired",-14:"blocked"}
      print(f"[mega] API err {err} ({err_names.get(err,'?')})", file=sys.stderr)
      return None
    return res[0]['g'], res[0]['s']
  except Exception as e:
    print(f"[mega] _fetch_file_info exception: {e}", file=sys.stderr)
    return None


def _run_prefetch(resp, q, stop):
  """Fill chunk queue from stream response (runs in thread)."""
  try:
    while True:
      chunk = resp.read(1024 * 1024)
      if not chunk or stop.is_set():
        break
      q.put(chunk)
    q.put(None)
  except Exception as e:
    q.put(e)


def resolve_mega_file_stream(url, file_id, console, early_mb=2):
  """Download+decrypt MEGA file in background; return early once early_mb MB ready."""
  parsed = _parse_mega_url(url)
  if parsed is None:
    console.print("[red]✘ Gagal parse key MEGA[/red]")
    return None
  k, iv = parsed

  info = _fetch_file_info(file_id)
  if info is None:
    console.print("[red]✘ Gagal ambil API MEGA[/red]")
    return None
  dl_link, file_size = info

  ready = threading.Event()
  stop = threading.Event()
  early_bytes = early_mb * 1024 * 1024
  _fmt = [None]  # mutable for closure: 'mp4' or 'mkv'
  bytes_counter = [0]  # ponytail: shared counter for 0-100% progress

  temp_path = tempfile.mktemp(suffix='.mp4')

  def _download():
    try:
      response = http_stream(dl_link, timeout=30)
      chunk_queue = queue.Queue(maxsize=2)
      stop_prefetch = threading.Event()

      t = threading.Thread(
        target=_run_prefetch, args=(response, chunk_queue, stop_prefetch),
        daemon=True,
      )
      t.start()

      downloaded = 0
      _first_dec = None
      c = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend())
      d = c.decryptor()
      with open(temp_path, "wb") as f:
        while True:
          chunk = chunk_queue.get()
          if chunk is None:
            break
          if isinstance(chunk, Exception):
            raise chunk
          dec = d.update(chunk)
          f.write(dec)
          if _first_dec is None:
            _first_dec = dec[:8]
            _fmt[0] = 'mp4' if b'\x66\x74\x79\x70' in _first_dec else 'mkv'
          downloaded += len(chunk)
          bytes_counter[0] = downloaded  # ponytail: expose progress to caller
          if not ready.is_set() and downloaded >= early_bytes and _fmt[0] != 'mp4':
            ready.set()  # MKV can stream early
          if stop.is_set():
            break
        d.finalize()
    except Exception as e:
      console.print(f"[red]✘ Mega Stream Error: {e}[/red]")
      ready.set()
      return

    ready.set()  # always signal when download finishes (MP4 waits for this)

  dl_thread = threading.Thread(target=_download, daemon=True)
  dl_thread.start()

  return temp_path, ready, stop, dl_thread, bytes_counter, file_size
