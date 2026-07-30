"""Banner, tables, styles, components."""
from InquirerPy.utils import get_style
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
import pyfiglet
from rich.rule import Rule
from rich.progress import (
  Progress, BarColumn, TextColumn, TimeElapsedColumn,
  SpinnerColumn, TaskProgressColumn, DownloadColumn,
)
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, HEAVY_HEAD, MINIMAL, SQUARE
from rich.padding import Padding
from rich.console import Group
from rich.style import Style

console = Console()

class Palette:
  primary   = "#00d4ff"   # cyan electric
  secondary = "#a855f7"   # purple
  accent    = "#f97316"   # orange
  success   = "#22c55e"   # green
  error     = "#ef4444"   # red
  warning   = "#eab308"   # yellow
  muted     = "#6b7280"   # gray
  border    = "#374151"   # dark gray
  text      = "#d1d5db"   # light gray
  dim       = "#4b5563"   # dim gray
  surface   = "#1f2937"   # dark surface
  highlight = "#2dd4bf"   # teal

BANNER_FONT = "big"  # ponytail: swap font string to change style

def _pyfiglet_gradient(text: str, font: str = BANNER_FONT) -> Text:
  """Pyfiglet + Rich gradient."""
  colors = ["#00d4ff", "#2dd4bf", "#a855f7"]
  art = pyfiglet.figlet_format(text, font=font)
  lines = art.splitlines()
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
        seg = t * (len(colors) - 1)
        seg_i, seg_t = int(seg), seg - int(seg)
        c1 = colors[min(seg_i, len(colors) - 1)]
        c2 = colors[min(seg_i + 1, len(colors) - 1)]
        result.append(ch, style=_lerp_color(c1, c2, seg_t))
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


_BANNER_PANEL = None

def print_banner():
  """Clear screen and show gradient banner."""
  global _BANNER_PANEL
  console.clear()
  if _BANNER_PANEL is None:
    gradient = _pyfiglet_gradient("INDONIME")
    subtitle = Text("  Subtitle Indonesia Anime Searcher", style=f"italic {Palette.muted}")
    content = Text.assemble(gradient, "\n", subtitle)
    _BANNER_PANEL = Panel(
      Align.center(content),
      box=ROUNDED,
      border_style=Palette.primary,
      padding=(1, 3),
      subtitle="✦  cari · tonton · nikmati  ✦",
      subtitle_align="center",
    )
  console.print(_BANNER_PANEL)


# ── Section header ────────────────────────
def print_header(title: str, icon: str = ""):
  """Styled section header."""
  console.print()
  label = f"  {icon}  {title}" if icon else f"    {title}"
  console.print(Rule(title=Text(label, style=f"bold {Palette.accent}"), style=Palette.border))
  console.print()


# ── Status messages ───────────────────────
def styled_status(message: str) -> str:
  """Styled spinner message."""
  return f"[bold {Palette.primary}]{message}[/bold {Palette.primary}]"


def print_step(msg: str):
  """Progress step."""
  console.print(f"  [bold {Palette.primary}]➜[/bold {Palette.primary}]  [dim]{msg}[/dim]")


def print_success(msg: str):
  """Green success."""
  console.print(f"  [bold {Palette.success}]✓[/bold {Palette.success}]  {msg}")


def print_error(msg: str):
  """Red error."""
  console.print(f"  [bold {Palette.error}]✘[/bold {Palette.error}]  {msg}")


def print_warning(msg: str):
  """Yellow warning."""
  console.print(f"  [bold {Palette.warning}]⚠[/bold {Palette.warning}]  {msg}")


def print_info(msg: str):
  """Info in muted style."""
  console.print(f"  [bold {Palette.muted}]ℹ[/bold {Palette.muted}]  [italic]{msg}[/italic]")


def print_separator():
  """Faint horizontal rule."""
  console.print()
  console.print(Rule(style=Palette.surface))
  console.print()


# ── Episode table ─────────────────────────
_LAST_TABLE_KEY = None
_LAST_TABLE = None

def make_episode_table(episode_list, start=0, count=25) -> Table:
  """Rich table showing a page of episodes. Cached per (list id, start)."""
  global _LAST_TABLE_KEY, _LAST_TABLE
  key = (id(episode_list), start, count)
  if _LAST_TABLE_KEY == key:
    return _LAST_TABLE

  total = len(episode_list)
  end = min(start + count, total)
  page_info = f"  —  {start+1}–{end} of {total}" if total > count else ""

  table = Table(
    box=SQUARE,
    border_style=Palette.border,
    header_style=Style(color=Palette.primary, bold=True),
    title=f"[bold]📋  Episodes{page_info}[/bold]",
    title_style=Palette.muted,
    padding=(0, 2),
    show_edge=True,
    show_lines=True,
    expand=True,
  )
  table.add_column(" EP", style=Palette.secondary, width=7, no_wrap=True, justify="center")
  table.add_column("Title", style=Palette.text, ratio=1)
  table.add_column("", style=Palette.dim, width=3, justify="center")

  for i in range(start, end):
    ep = episode_list[i]
    ep_num = f"EP{i+1:02d}"
    title = (ep["title"][:58] + "…") if len(ep["title"]) > 60 else ep["title"]
    table.add_row(ep_num, title, "▶")

  _LAST_TABLE_KEY = key
  _LAST_TABLE = table
  return table


def make_episode_page(episode_list, start=0, count=25) -> Group:
  """Header + separator (table removed per user request)."""
  header = Padding(Columns([
    Text(" 🎬 ", style=Palette.primary),
    Text("📋 EPISODES", style=Style(color=Palette.primary, bold=True)),
  ], padding=(0, 1)), pad=(1, 0, 0, 0))
  return Group(
    header,
    Rule(style=Palette.border),
  )


# ── Post-play menu ────────────────────────
def make_postplay_actions(current_idx: int, total: int) -> list[str]:
  """Context-aware post-play command list."""
  actions = []
  if current_idx + 1 < total:
    actions.append("▶  NEXT")
  if current_idx > 0:
    actions.append("◀  PREV")
  actions.append("↺  REPLAY")
  actions.append("⚙  QUALITY")
  actions.append("✖  QUIT")
  return actions


# ── Footer ─────────────────────────────────
def make_footer():
  """Clean centered footer."""
  console.print()
  text = Text.assemble(
    ("  ✦  ", f"italic dim {Palette.dim}"),
    ("Indonime", f"italic bold {Palette.secondary}"),
    ("  —  made with love for anime fans  ✦", f"italic dim {Palette.dim}"),
  )
  console.print(Align.center(text))


def make_style():
  """InquirerPy custom style."""
  return get_style({
    'questionmark': f'{Palette.secondary} bold',
    'question': f'{Palette.text} bold',
    'instruction': f'{Palette.dim} italic',
    'pointer': f'{Palette.primary} bold',
    'answered_pointer': f'{Palette.muted}',
    'answer': f'{Palette.primary}',
    'pager': f'{Palette.primary}',
    'selected': f'{Palette.secondary}',
    'multiselect': f'{Palette.primary}',
    'longlist': f'{Palette.text}',
  }, style_override=False)


# ── Progress bar ──────────────────────────
def make_progress_bar(transient=True, show_size=False):
  """Styled download progress bar.

  Usage:
    with make_progress_bar() as progress:
      task = progress.add_task("...", total=100)
  """
  columns = [
    SpinnerColumn(spinner_name="dots", style=Palette.primary),
    TextColumn(
      "[progress.description]{task.description}",
      style=Palette.text,
    ),
    BarColumn(
      bar_width=None,
      style=Palette.surface,
      complete_style=Palette.primary,
      pulse_style=Palette.secondary,
    ),
  ]
  if show_size:
    columns.append(DownloadColumn(binary_units=True))
  columns.append(TaskProgressColumn(
    text_format="{task.percentage:>3.0f}%",
    style=Palette.text,
  ))
  columns.append(TimeElapsedColumn())

  return Progress(
    *columns,
    console=console,
    expand=True,
    transient=transient,
  )