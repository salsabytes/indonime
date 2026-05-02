import os
import sys
import shutil
import subprocess
from rich.console import Console
from rich.panel import Panel

console = Console()
EXE_NAME = "Indonime"
DIST_PATH = os.path.join("dist", "main.dist")

def build():
  cmd = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--follow-imports",
    "--include-package=rich",
    "--include-package=playwright",
    "--include-package=bs4",
    "--include-package=requests",
    "--include-module=megadec",
    "--output-dir=dist",
    f"--output-filename={EXE_NAME}",
    "--experimental=terminal-is-ansi",
    "main.py"
  ]

  console.print(Panel("[bold blue]Nuitka Build System[/bold blue]\n[white]Compiling main.py into standalone executable...[/white]"))
  
  try:
    subprocess.run(cmd, check=True)
  except subprocess.CalledProcessError:
    console.print("[red]Error: Build process failed.[/red]")
    return

  if os.path.exists(DIST_PATH):
    resources = ["plugins", "mpv"]
    for res in resources:
      if os.path.exists(res):
        dest = os.path.join(DIST_PATH, res)
        if os.path.exists(dest): shutil.rmtree(dest)
        shutil.copytree(res, dest)
        console.print(f"[green]DONE:[/green] Resource '{res}' synchronized.")

    console.print(Panel(f"[bold green]Build Successful[/bold green]\nLocation: {DIST_PATH}", border_style="green"))
  else:
    console.print("[red]FATAL: Distribution path not found.[/red]")

if __name__ == "__main__":
  build()