#!/usr/bin/env python3
"""MEGA stream decrypt — cryptography (C, fast) fallback ext.videodec (pure Python)."""
import requests
import base64
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
    if _decryptor == 'cryptography':
        # Advance CTR counter by offset // 16 blocks
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
            downloaded = 0
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        break
                    decrypted = _decrypt_chunk(chunk, k, iv, downloaded)
                    f.write(decrypted)
                    downloaded += len(chunk)
                    percent = (downloaded / file_size) * 100
                    status.update(f"[bold magenta]Decrypting... ({percent:.1f}%)")
            return str(temp_file)
    except Exception as e:
        console.print(f"[red]✘ Mega Decrypt Error: {e}[/red]")
        return None
