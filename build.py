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
  if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

  cmd = [
    sys.executable, "-m", "nuitka",
    "--onefile",
    "--standalone",
    "--follow-imports",
    "--include-package=rich",
    "--include-package=playwright",
    "--include-package=bs4",
    "--include-package=requests",
    "--include-module=megadec",
    "--include-package=plugins",
    f"--output-dir={OUTPUT_DIR}",
    f"--output-filename={EXE_NAME}",
    "--experimental=terminal-is-ansi",
    "--include-data-dir=./mpv=mpv",
    "main.py"
  ]

  console.print(Panel(
    f"[bold blue]Nuitka Build[/bold blue]\n"
    f"[white]File: {EXE_NAME}.exe[/white]",
    expand=False
  ))
    
  try:
    subprocess.run(cmd, check=True)
    
    source_exe = os.path.join(OUTPUT_DIR, f"{EXE_NAME}.exe")
    destination_exe = os.path.join(ROOT_DIR, f"{EXE_NAME}.exe")
        
    if os.path.exists(source_exe):
      console.print("[yellow]Moving executable to root...[/yellow]")
      if os.path.exists(destination_exe):
        os.remove(destination_exe)
      shutil.move(source_exe, destination_exe)

      console.print("[dim]Cleaning build artifacts...[/dim]")
      shutil.rmtree(OUTPUT_DIR)

      console.print(Panel(
        f"[bold green]Build Completed Successfully[/bold green]\n"
        f"Location: [cyan]{destination_exe}[/cyan]",
        expand=False
      ))
                
  except subprocess.CalledProcessError:
    console.print("[red]Error: Nuitka compilation failed.[/red]")
  except Exception as e:
    console.print(f"[red]Error during cleanup: {e}[/red]")

if __name__ == "__main__":
  build()