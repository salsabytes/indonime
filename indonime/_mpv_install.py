# Cross-platform mpv installer.
import os
import sys
import shutil
import subprocess
from pathlib import Path
from tuiko import progress, style
from .plugins._base import http_stream
from .ui import Palette

if sys.platform == "win32":
  BASE = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "Indonime"
else:
  BASE = Path.home() / ".local" / "share" / "indonime"
MPV_DIR = BASE / "mpv"


def _download(url, dest, desc="Downloading"):
  dest = Path(dest)
  try:
    with http_stream(url, timeout=60) as resp:
      total = int(resp.headers.get("Content-Length", 0))
      with progress(desc, total=total or None) as up:
        done = 0
        with open(dest, "wb") as f:
          for chunk in iter(lambda: resp.read(64 * 1024), b""):
            f.write(chunk)
            done += len(chunk)
            if total:
              up(done)
    return True
  except Exception as e:
    print(style(f"✘ Download failed: {e}", Palette.error))
    return False


def _install_windows():
  # Download mpv.7z, extract via 7zr.exe (standalone).
  BASE.mkdir(parents=True, exist_ok=True)
  mpv_url = "https://github.com/salsa-ram/indonime/releases/download/v1.0.0-mpv/mpv.7z"
  mpv_7z = BASE / "mpv.7z"

  if not _download(mpv_url, mpv_7z, "Downloading MPV"):
    return False

  print(style("Extracting...", Palette.primary))
  MPV_DIR.mkdir(exist_ok=True)

  z7 = r"C:\Program Files\7-Zip\7z.exe"
  if os.path.exists(z7):
    subprocess.run([z7, "x", str(mpv_7z), f"-o{MPV_DIR}", "-y"],
             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  if not (MPV_DIR / "mpv.exe").exists():
    print(style("Downloading 7-Zip standalone extractor...", Palette.primary))
    if not _download("https://www.7-zip.org/a/7zr.exe", BASE / "7zr.exe"):
      return False
    subprocess.run([str(BASE / "7zr.exe"), "x", str(mpv_7z), f"-o{MPV_DIR}", "-y"],
             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (BASE / "7zr.exe").unlink(missing_ok=True)  # BCJ2 archive, needs 7z

  mpv_7z.unlink(missing_ok=True)
  ok = (MPV_DIR / "mpv.exe").exists()
  print(style("✓ mpv installed" if ok else "✘ Extraction failed",
              Palette.success if ok else Palette.error))
  return ok


def main():
  print(style("📺 Indonime - MPV Setup", 1, Palette.primary))
  print()

  if shutil.which("mpv"):
    print(style("✓ mpv already in PATH", Palette.success))
    return

  if sys.platform == "win32":
    ok = _install_windows()
  else:
    print(style("Install mpv manually: apt install mpv / brew install mpv", Palette.warning))
    ok = False

  if not ok:
    print(style("Install mpv manually:", Palette.warning))
    print("  Windows: https://mpv.io/installation/")
    print("  macOS:   brew install mpv")
    print("  Linux:   apt install mpv")
    sys.exit(1)

  print(style("✓ Setup complete!", 1, Palette.success))


if __name__ == "__main__":
  main()
