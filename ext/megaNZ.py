import requests
import base64
from pathlib import Path

try:
  import megadec
except ImportError:
  megadec = None

def mega_base64_decode(data):
  data += '=' * (4 - len(data) % 4)
  return base64.urlsafe_b64decode(data)

def decrypt_mega_file(url, file_id, console):
  if not megadec:
    console.print("[red]✘ Error: Modul 'megadec' tidak ditemukan.[/red]")
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
          if not chunk: break
          decrypted = megadec.decrypt(chunk, k, iv, downloaded)
          if decrypted:
            f.write(decrypted)
            downloaded += len(chunk)
            percent = (downloaded / file_size) * 100
            status.update(f"[bold magenta]Decrypting... ({percent:.1f}%)")
      return str(temp_file)
  except Exception as e:
    console.print(f"[red]✘ Mega Decrypt Error: {e}[/red]")
    return None