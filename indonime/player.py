import os
import sys
import shutil
import subprocess
from pathlib import Path
from .ui import console

BASE_DIR = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).resolve().parent.parent
if not (BASE_DIR / "mpv" / "mpv.exe").exists():
  BASE_DIR = Path(os.path.dirname(sys.argv[0]))

current_mpv_process = None

def play_with_mpv(video_target, is_temp_file=False):
  global current_mpv_process
  if current_mpv_process and current_mpv_process.poll() is None:
    current_mpv_process.terminate()

  mpv_name = "mpv.exe" if sys.platform == "win32" else "mpv"
  path_mpv = (BASE_DIR / "mpv" / mpv_name).resolve()

  if not path_mpv.exists():
    alt_path = Path(sys.argv[0]).parent / "mpv" / mpv_name
    if alt_path.exists():
      path_mpv = alt_path
    else:
      path_in_path = shutil.which("mpv")
      if path_in_path:
        path_mpv = Path(path_in_path)
      else:
        console.print(f"[yellow]⚠ mpv not found. Installing automatically...[/yellow]")
        import setup_mpv
        setup_mpv.main()
        # ponytail: retry bundled path first — setup_mpv installs to BASE_DIR/mpv/
        path_mpv = (BASE_DIR / "mpv" / mpv_name).resolve()
        if not path_mpv.exists():
          path_in_path = shutil.which("mpv")
          if path_in_path:
            path_mpv = Path(path_in_path)
          else:
            console.print(f"[red]✘ mpv installation failed. Install manually.[/red]")
            return False

  mpv_args = [str(path_mpv), video_target, '--title=Indonime Player', '--force-window=yes', '--ontop', '--really-quiet']

  try:
    if is_temp_file:
      subprocess.run(mpv_args)
      if os.path.exists(video_target): os.remove(video_target)
    else:
      current_mpv_process = subprocess.Popen(mpv_args)
    return True
  except Exception as e:
    console.print(f"[red]✘ Error: {e}[/red]")
    return False
