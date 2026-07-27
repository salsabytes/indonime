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

# Cache resolved mpv path after first successful lookup
_mpv_path = None


def play_with_mpv(video_target, is_temp_file=False):
    global current_mpv_process, _mpv_path
    if current_mpv_process and current_mpv_process.poll() is None:
        current_mpv_process.terminate()

    if _mpv_path is None:
        _mpv_path = _find_mpv()
    if _mpv_path is None:
        return False

    mpv_args = [str(_mpv_path), video_target,
                '--title=Indonime Player', '--force-window=yes',
                '--ontop', '--really-quiet']
    try:
        if is_temp_file:
            subprocess.run(mpv_args)
            if os.path.exists(video_target):
                os.remove(video_target)
        else:
            current_mpv_process = subprocess.Popen(mpv_args)
        return True
    except Exception as e:
        console.print(f"[red]✘ Error: {e}[/red]")
        return False


def _find_mpv():
    """Locate mpv binary. Cache first successful result."""
    mpv_name = "mpv.exe" if sys.platform == "win32" else "mpv"
    path_mpv = (BASE_DIR / "mpv" / mpv_name).resolve()
    if path_mpv.exists():
        return path_mpv

    alt_path = Path(sys.argv[0]).parent / "mpv" / mpv_name
    if alt_path.exists():
        return alt_path

    in_path = shutil.which("mpv")
    if in_path:
        return Path(in_path)

    console.print("[yellow]⚠ mpv not found. Installing automatically...[/yellow]")
    import setup_mpv
    setup_mpv.main()

    path_mpv = (BASE_DIR / "mpv" / mpv_name).resolve()
    if path_mpv.exists():
        return path_mpv

    in_path = shutil.which("mpv")
    if in_path:
        return Path(in_path)

    console.print("[red]✘ mpv installation failed. Install manually.[/red]")
    return None
