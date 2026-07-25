import os
import sys
import shutil
import subprocess
from rich.console import Console
from rich.panel import Panel

console = Console()

EXE_NAME = "Indonime"
OUTPUT_DIR = "out"
ROOT_DIR = os.getcwd()

def build():
  # compile C++ ext dulu
  console.print("[bold yellow]Compiling C++ extension...[/bold yellow]")
  ext_result = subprocess.run(
    [sys.executable, "setup.py", "build_ext", "--inplace"],
    capture_output=True, text=True
  )
  if ext_result.returncode != 0:
    console.print(f"[red]✘ Gagal compile videodec: {ext_result.stderr.strip()}[/red]")
    return

  if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

  cmd = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--follow-imports",
    "--include-package=indonime",
    "--include-package=rich",
    "--include-package=bs4",
    "--include-package=requests",
    "--include-package=plugins",
    "--include-module=videodec",
    "--include-package=ext",
    f"--output-dir={OUTPUT_DIR}",
    f"--output-filename={EXE_NAME}",
    "--experimental=terminal-is-ansi",
    "main.py"
  ]

  console.print(Panel(
    f"[bold blue]Nuitka Build[/bold blue]\n"
    f"[white]File: {EXE_NAME}.exe[/white]",
    expand=False
  ))
    
  try:
    subprocess.run(cmd, check=True)
    
    # Nuitka names .dist folder after input file, not --output-filename
    dist_name = f"{os.path.splitext('main.py')[0]}.dist"
    dist_dir = os.path.join(OUTPUT_DIR, dist_name)
    destination_dir = os.path.join(ROOT_DIR, f"{EXE_NAME}_dist")
    
    if os.path.exists(dist_dir):
      if os.path.exists(destination_dir):
        shutil.rmtree(destination_dir)
      shutil.move(dist_dir, destination_dir)
      console.print("[dim]Cleaning build artifacts...[/dim]")
      shutil.rmtree(OUTPUT_DIR)
      console.print(Panel(
        f"[bold green]Build Completed Successfully[/bold green]\n"
        f"Location: [cyan]{destination_dir}[/cyan]",
        expand=False
      ))
    else:
      console.print("[yellow]⚠ Output folder tidak ditemukan, cek build log.[/yellow]")
                
  except subprocess.CalledProcessError:
    console.print("[red]Error: Nuitka compilation failed.[/red]")
  except Exception as e:
    console.print(f"[red]Error during cleanup: {e}[/red]")

if __name__ == "__main__":
  build()