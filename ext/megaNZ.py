#!/usr/bin/env python3
"""MEGA stream decrypt — reused cipher + prefetch thread for overlapping I/O."""
import requests
import base64
import threading
import queue
from pathlib import Path

# Try fastest backend first
_decryptor = None
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    _decryptor = 'cryptography'
except ImportError:
    try:
        from ext import videodec
        _decryptor = 'videodec'
    except ImportError:
        pass


def _decrypt_chunk(chunk, k, iv, offset):
    """Single-chunk decrypt — used by videodec fallback per-chunk."""
    if _decryptor == 'cryptography':
        blocks = offset // 16
        ctr = int.from_bytes(iv, 'big') + blocks
        ctr_iv = ctr.to_bytes(16, 'big')
        c = Cipher(algorithms.AES(k), modes.CTR(ctr_iv), backend=default_backend())
        d = c.decryptor()
        return d.update(chunk) + d.finalize()
    elif _decryptor == 'videodec':
        return videodec.decode(chunk, k, iv, offset)
    raise RuntimeError("No AES backend available (install cryptography or videodec.py)")


def mega_base64_decode(data):
    data += '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data)


def resolve_mega_file(url, file_id, console):
    if not _decryptor:
        console.print("[red]✘ Tidak ada AES backend. Install: pip install cryptography[/red]")
        return None

    try:
        parts = url.split("#")
        encoded_key = parts[1]
        full_key = mega_base64_decode(encoded_key)
        k = bytes(full_key[i] ^ full_key[i + 16] for i in range(16))
        iv = full_key[16:24] + b"\x00" * 8
    except Exception as e:
        console.print(f"[red]✘ Gagal parse key MEGA: {e}[/red]")
        return None

    api_url = "https://g.api.mega.co.nz/cs"
    payload = [{"a": "g", "g": 1, "p": file_id}]
    try:
        res = requests.post(api_url, json=payload).json()
        if isinstance(res[0], int):
            console.print(f"[red]✘ MEGA API Error: {res[0]}[/red]")
            return None
        dl_link = res[0]['g']
        file_size = res[0]['s']
    except Exception as e:
        console.print(f"[red]✘ Gagal ambil API MEGA: {e}[/red]")
        return None

    script_dir = Path(__file__).parent.parent.absolute()
    temp_file = script_dir / "stream_cache.mp4"

    try:
        with console.status(f"[bold magenta]Decrypting... (0%)") as status:
            response = requests.get(dl_link, stream=True)

            # Prefetch thread — downloads chunks ahead while main thread decrypts
            chunk_queue = queue.Queue(maxsize=2)
            stop_prefetch = threading.Event()

            def _prefetch(resp, q, stop):
                try:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if stop.is_set():
                            break
                        q.put(chunk)
                    q.put(None)  # EOF sentinel
                except Exception as e:
                    q.put(e)     # error sentinel

            t = threading.Thread(
                target=_prefetch, args=(response, chunk_queue, stop_prefetch),
                daemon=True,
            )
            t.start()

            downloaded = 0
            with open(temp_file, "wb") as f:
                if _decryptor == 'cryptography':
                    # Reuse single Cipher + decryptor for entire stream
                    c = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend())
                    d = c.decryptor()
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        if isinstance(chunk, Exception):
                            raise chunk
                        f.write(d.update(chunk))
                        downloaded += len(chunk)
                        percent = (downloaded / file_size) * 100
                        status.update(f"[bold magenta]Decrypting... ({percent:.1f}%)")
                    d.finalize()
                else:
                    # videodec — no reusable cipher state, decrypt per chunk
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        if isinstance(chunk, Exception):
                            raise chunk
                        f.write(videodec.decode(chunk, k, iv, downloaded))
                        downloaded += len(chunk)
                        percent = (downloaded / file_size) * 100
                        status.update(f"[bold magenta]Decrypting... ({percent:.1f}%)")
            return str(temp_file)
    except Exception as e:
        console.print(f"[red]✘ Mega Decrypt Error: {e}[/red]")
        return None


def resolve_mega_file_stream(url, file_id, console, early_mb=2):
    """Download + decrypt MEGA file in background; return early once early_mb MB ready.

    Returns (temp_path, ready_event, stop_event, thread) on success, or None on error.
    Caller: ready_event.wait() → launch mpv → stop_event.set() → thread.join() → cleanup path.
    """
    if not _decryptor:
        console.print("[red]✘ Tidak ada AES backend. Install: pip install cryptography[/red]")
        return None

    try:
        parts = url.split("#")
        encoded_key = parts[1]
        full_key = mega_base64_decode(encoded_key)
        k = bytes(full_key[i] ^ full_key[i + 16] for i in range(16))
        iv = full_key[16:24] + b"\x00" * 8
    except Exception as e:
        console.print(f"[red]✘ Gagal parse key MEGA: {e}[/red]")
        return None

    api_url = "https://g.api.mega.co.nz/cs"
    payload = [{"a": "g", "g": 1, "p": file_id}]
    try:
        res = requests.post(api_url, json=payload).json()
        if isinstance(res[0], int):
            console.print(f"[red]✘ MEGA API Error: {res[0]}[/red]")
            return None
        dl_link = res[0]['g']
        file_size = res[0]['s']
    except Exception as e:
        console.print(f"[red]✘ Gagal ambil API MEGA: {e}[/red]")
        return None

    script_dir = Path(__file__).parent.parent.absolute()
    temp_file = script_dir / "stream_cache.mp4"

    ready = threading.Event()
    stop = threading.Event()
    early_bytes = early_mb * 1024 * 1024

    def _download():
        try:
            response = requests.get(dl_link, stream=True)
            chunk_queue = queue.Queue(maxsize=2)
            stop_prefetch = threading.Event()

            def _prefetch():
                try:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if stop_prefetch.is_set() or stop.is_set():
                            break
                        chunk_queue.put(chunk)
                    chunk_queue.put(None)
                except Exception as e:
                    chunk_queue.put(e)

            t = threading.Thread(target=_prefetch, daemon=True)
            t.start()

            downloaded = 0
            with open(temp_file, "wb") as f:
                if _decryptor == 'cryptography':
                    c = Cipher(algorithms.AES(k), modes.CTR(iv), backend=default_backend())
                    d = c.decryptor()
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        if isinstance(chunk, Exception):
                            raise chunk
                        f.write(d.update(chunk))
                        downloaded += len(chunk)
                        if not ready.is_set() and downloaded >= early_bytes:
                            ready.set()
                        if stop.is_set():
                            break
                    d.finalize()
                else:
                    while True:
                        chunk = chunk_queue.get()
                        if chunk is None:
                            break
                        if isinstance(chunk, Exception):
                            raise chunk
                        f.write(videodec.decode(chunk, k, iv, downloaded))
                        downloaded += len(chunk)
                        if not ready.is_set() and downloaded >= early_bytes:
                            ready.set()
                        if stop.is_set():
                            break
        except Exception as e:
            console.print(f"[red]✘ Mega Stream Error: {e}[/red]")
        finally:
            ready.set()  # always unblock caller even on error/early stop

    dl_thread = threading.Thread(target=_download, daemon=True)
    dl_thread.start()

    return str(temp_file), ready, stop, dl_thread
