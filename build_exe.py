#!/usr/bin/env python3
"""Build Indonime.exe with PyInstaller --onefile.

Usage:
  pip install pyinstaller
  python build_exe.py
"""
import sys
import shutil
import subprocess
from pathlib import Path

if not shutil.which("pyinstaller"):
  print("❌ PyInstaller not found. Install: pip install pyinstaller")
  sys.exit(1)

PYINSTALLER_ARGS = [
  sys.executable, "-m", "PyInstaller",
  "--onefile",
  "--console",
  "--name", "Indonime",
  # dynamic imports — PyInstaller can't auto-detect these
  "--collect-data", "pyfiglet",
  "--hidden-import", "cryptography",  # try/except import
  "--hidden-import", "indonime.plugins.otakudesu",
  "--hidden-import", "indonime.plugins.anoboy",
  "--hidden-import", "indonime.ext.pdrain",
  "--hidden-import", "indonime.ext.megaNZ",
  "indonime/__main__.py"
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
