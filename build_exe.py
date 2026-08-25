#!/usr/bin/env python3
# Build Indonime.exe with PyInstaller --onefile.
#
# Usage:
#   pip install pyinstaller
#   python build_exe.py
import sys
import struct
import shutil
import subprocess
from pathlib import Path

UI_DIST = Path("app/dist")
if not (UI_DIST / "index.html").exists():
  print("❌ app/dist tidak ada. Build dulu: cd app && npx expo export --platform web")
  sys.exit(1)

if not shutil.which("pyinstaller"):
  print("❌ PyInstaller not found. Install: pip install pyinstaller")
  sys.exit(1)

# Remove stale output and use --clean: PyInstaller's analysis cache keeps files
# that no longer exist (e.g. removed modules), which breaks the built EXE.
for d in ['dist', 'build']:
  shutil.rmtree(d, ignore_errors=True)

# Wrap app/assets/icon.png in an ICO container (Vista+ renders PNG-compressed
# icon entries). Stdlib only — no Pillow needed.
ICON_PNG = Path("app/assets/icon.png")
ICO = Path("build/Indonime.ico")
if ICON_PNG.exists():
  png = ICON_PNG.read_bytes()
  ICO.parent.mkdir(exist_ok=True)
  ICO.write_bytes(struct.pack('<HHH', 0, 1, 1)
                  + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22)
                  + png)

PYINSTALLER_ARGS = [
  sys.executable, "-m", "PyInstaller",
  "--clean",
  "--onefile",
    "--noconsole",
    "--name", "Indonime",
    *(["--icon", str(ICO)] if ICO.exists() else []),
  # dynamic imports — PyInstaller can't auto-detect these
  "--hidden-import", "cryptography",  # try/except import
  "--hidden-import", "indonime.plugins.otakudesu",
  "--hidden-import", "indonime.plugins.anoboy",
  "--hidden-import", "indonime.ext.pdrain",
  "--hidden-import", "indonime.ext.megaNZ",
  "--hidden-import", "indonime.server",
  "--hidden-import", "indonime.app",
  "--hidden-import", "webview.platforms.edgechromium",
  # RN web build (react-native-web; static files diserve indonime.server)
  "--add-data", f"{UI_DIST};app/dist",
  "indonime/app.py"
]

if __name__ == "__main__":
  print("⚙ Building Indonime.exe with PyInstaller...")
  subprocess.run(PYINSTALLER_ARGS, check=True)
  exe = Path("dist/Indonime.exe")
  if exe.exists():
    size_mb = exe.stat().st_size / 1_000_000
    print(f"\n✅ {exe} ({size_mb:.1f} MB)")
  else:
    print("\n⚠ Build selesai tapi file gak ditemukan. Cek dist/")
