import os
import sys
import shutil
import subprocess
from pathlib import Path
from tuiko import style
from .ui import Palette
from ._mpv_install import MPV_DIR, main as install_mpv

current_mpv_process = None
_mpv_path = None


def play_with_mpv(video_target, is_temp_file=False, cleanup=True):
  global current_mpv_process, _mpv_path
  if current_mpv_process and current_mpv_process.poll() is None:
    current_mpv_process.terminate()

  _mpv_path = _mpv_path or _find_mpv()
  if _mpv_path is None:
    return False

  mpv_args = [str(_mpv_path), video_target,
        '--title=Indonime Player', '--force-window=yes',
        '--really-quiet', '--no-terminal']
  try:
    if is_temp_file:
      subprocess.run(mpv_args)
      if cleanup and os.path.exists(video_target):
        os.remove(video_target)
    else:
      current_mpv_process = subprocess.Popen(mpv_args)
    return True
  except Exception as e:
    print(style(f"✘ Error: {e}", Palette.error))
    return False


def _find_mpv():
  # Locate mpv binary. Cache first successful result.
  mpv_name = "mpv.com" if sys.platform == "win32" else "mpv"

  appdata_mpv = (MPV_DIR / mpv_name).resolve()
  if appdata_mpv.exists():
    return appdata_mpv

  dev_mpv = (Path(__file__).resolve().parent.parent / "mpv" / mpv_name).resolve()
  if dev_mpv.exists():
    return dev_mpv

  exe_mpv = Path(sys.argv[0]).parent / "mpv" / mpv_name
  if exe_mpv.exists():
    return exe_mpv

  in_path = shutil.which("mpv")
  if in_path:
    return Path(in_path)

  print(style("⚠ mpv not found. Installing automatically...", Palette.warning))
  install_mpv()

  if appdata_mpv.exists():
    return appdata_mpv

  print(style("✘ mpv installation failed. Install manually.", Palette.error))
  return None
