# Cross-platform mpv installer.
import os
import sys
import shutil
import subprocess
import urllib.request
from pathlib import Path
from rich.console import Console
from rich.progress import (
  Progress, BarColumn, DownloadColumn,
  TransferSpeedColumn, TimeRemainingColumn,
)

console = Console()

if sys.platform == "win32":
  BASE = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "Indonime"
else:
  BASE = Path.home() / ".local" / "share" / "indonime"
MPV_DIR = BASE / "mpv"


def _download(url, dest, desc="Downloading"):
  dest = Path(dest)
  try:
    resp = urllib.request.urlopen(url)
    total = int(resp.headers.get("content-length", 0))
    with Progress(
      "[progress.description]{task.description}", BarColumn(),
      DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
      console=console,
    ) as p:
      task = p.add_task(f"[cyan]{desc}", total=total)
      with open(dest, "wb") as f:
        for chunk in iter(lambda: resp.read(64 * 1024), b""):
          f.write(chunk)
          p.update(task, advance=len(chunk))
    return True
  except Exception as e:
    console.print(f"[red]✘ Download failed: {e}[/red]")
    return False


def _install_windows():
  # Download mpv.7z, extract via 7zr.exe (standalone).
  BASE.mkdir(parents=True, exist_ok=True)
  mpv_url = "https://github.com/salsa-ram/indonime/releases/download/v1.0.0-mpv/mpv.7z"
  mpv_7z = BASE / "mpv.7z"

  if not _download(mpv_url, mpv_7z, "Downloading MPV"):
    return False

  console.print("[cyan]Extracting...[/cyan]")
  MPV_DIR.mkdir(exist_ok=True)

  for exe, args in [
    (r"C:\Program Files\7-Zip\7z.exe", [r"C:\Program Files\7-Zip\7z.exe", "x", str(mpv_7z), f"-o{MPV_DIR}", "-y"]),
  ]:
    if os.path.exists(exe):
      subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      if (MPV_DIR / "mpv.exe").exists():
        break
  else:
    console.print("[cyan]Downloading 7-Zip standalone extractor...[/cyan]")
    if not _download("https://www.7-zip.org/a/7zr.exe", BASE / "7zr.exe"):
      return False
    subprocess.run([str(BASE / "7zr.exe"), "x", str(mpv_7z), f"-o{MPV_DIR}", "-y"],
             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (BASE / "7zr.exe").unlink(missing_ok=True)  # ponytail: BCJ2 archive, needs 7z

  mpv_7z.unlink(missing_ok=True)
  ok = (MPV_DIR / "mpv.exe").exists()
  console.print("[green]✓ mpv installed[/green]" if ok else "[red]✘ Extraction failed[/red]")
  return ok


def main():
  console.print("[bold cyan]📺 Indonime - MPV Setup[/bold cyan]\n")

  if shutil.which("mpv"):
    console.print("[green]✓ mpv already in PATH[/green]")
    return

  if sys.platform == "win32":
    ok = _install_windows()
  else:
    console.print("[yellow]Install mpv manually: apt install mpv / brew install mpv[/yellow]")
    ok = False

  if not ok:
    console.print("\n[yellow]Install mpv manually:[/yellow]")
    console.print("  Windows: https://mpv.io/installation/")
    console.print("  macOS:   brew install mpv")
    console.print("  Linux:   apt install mpv")
    sys.exit(1)

  console.print("[bold green]✓ Setup complete![/bold green]")


if __name__ == "__main__":
  main()
