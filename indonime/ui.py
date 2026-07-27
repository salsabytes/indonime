from InquirerPy.utils import get_style
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, HEAVY_HEAD

console = Console()

BANNER_ART = r"""
   ___           _             _                 
  |_ _|_ __   __| | ___  _ __ (_)_ __ ___   ___  
   | || '_ \ / _` |/ _ \| '_ \| | '_ ` _ \ / _ \ 
   | || | | | (_| | (_) | | | | | | | | | |  __/ 
  |___|_| |_|\__,_|\___/|_| |_|_|_| |_| |_|\___|
"""


def _gradient_text(text: str, start_color: str = "#00d4ff", end_color: str = "#ff6fd8") -> Text:
  """Apply a horizontal gradient across text."""
  lines = text.splitlines()
  result = Text()
  for li, line in enumerate(lines):
    if not line:
      result.append("\n")
      continue
    n = len(line)
    for ci, ch in enumerate(line):
      if ch == " ":
        result.append(" ")
      else:
        t = ci / max(n - 1, 1)
        result.append(ch, style=_lerp_color(start_color, end_color, t))
    if li < len(lines) - 1:
      result.append("\n")
  return result


def _lerp_color(a: str, b: str, t: float) -> str:
  """Linear interpolate between two hex colors."""
  ah, bh = int(a[1:], 16), int(b[1:], 16)
  ar, ag, ab = (ah >> 16) & 0xFF, (ah >> 8) & 0xFF, ah & 0xFF
  br, bg, bb = (bh >> 16) & 0xFF, (bh >> 8) & 0xFF, bh & 0xFF
  r = int(ar + (br - ar) * t)
  g = int(ag + (bg - ag) * t)
  b = int(ab + (bb - ab) * t)
  return f"#{r:02x}{g:02x}{b:02x}"


def print_banner():
  """Clear screen and show the gradient banner."""
  console.clear()
  gradient = _gradient_text(BANNER_ART, "#00d4ff", "#a855f7")
  subtitle = Text("  Subtitle Indonesia Anime Searcher", style="italic #6b7280")
  panel = Panel(
    Align.center(Text.assemble(gradient, "\n", subtitle)),
    box=ROUNDED,
    border_style="#00d4ff",
    padding=(1, 2),
  )
  console.print(panel)


def print_header(title: str):
  """Section header with a styled rule."""
  console.print()
  console.print(Rule(title=Text(title, style="bold #f97316"), style="#374151"))
  console.print()


def styled_status(message: str):
  """Return a styled status spinner message."""
  return f"[bold #00d4ff]{message}[/bold #00d4ff]"


def print_step(msg: str):
  """Print a progress step indicator."""
  console.print(f"  [bold #00d4ff]➜[/bold #00d4ff]  {msg}")


def print_success(msg: str):
  """Green success message."""
  console.print(f"  [bold green]✓[/bold green]  {msg}")


def print_error(msg: str):
  """Red error message."""
  console.print(f"  [bold red]✘[/bold red]  {msg}")


def print_warning(msg: str):
  """Yellow warning message."""
  console.print(f"  [bold yellow]⚠[/bold yellow]  {msg}")


def print_separator():
  """A faint horizontal rule."""
  console.print(Rule(style="#1f2937"))


def make_episode_table(episode_list) -> Table:
  """Create a Rich Table for episode list display."""
  table = Table(
    box=HEAVY_HEAD,
    border_style="#374151",
    header_style="bold #00d4ff",
    title="[bold]📋 Episode List[/bold]",
    title_style="#6b7280",
    padding=(0, 1),
    show_lines=False,
  )
  table.add_column("#", style="#a855f7", width=6, no_wrap=True)
  table.add_column("Title", style="#d1d5db")
  table.add_column("", style="#4b5563", width=4)

  for i, ep in enumerate(episode_list):
    table.add_row(
      f"EP{str(i + 1).zfill(2)}",
      ep["title"][:60],
      "▶",
    )
  return table


def make_footer():
  """Print a small footer."""
  console.print()
  console.print(
    Align.center(
      Text("✨ made with love for anime fans ✨", style="dim #4b5563 italic")
    )
  )


def make_style():
  return get_style({
    'questionmark': '#a855f7 bold',
    'question': '#d1d5db bold',
    'instruction': '#4b5563 italic',
    'pointer': '#00d4ff bold',
    'answered_pointer': '#6b7280',
    'answer': '#00d4ff',
    'pager': '#00d4ff',
    'selected': '#a855f7',
    'multiselect': '#00d4ff',
    'longlist': '#d1d5db',
  }, style_override=False)
