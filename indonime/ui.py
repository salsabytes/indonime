"""Banner, headers, status messages — tuiko-based (no rich / InquirerPy / pyfiglet)."""
import sys

from tuiko import grad, sep, strip_ansi, style, term_width, theme
from rich.console import Console
from rich.progress import (BarColumn, DownloadColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn, TimeElapsedColumn)

# Windows pipes default to cp1252 which can't encode emoji — force UTF-8 so
# plain print() never crashes (real console + tuiko frames are unaffected).
for _s in (sys.stdout, sys.stderr):
  if hasattr(_s, "reconfigure"):
    try:
      _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass

class Palette:
  primary   = 117   # sky cyan
  secondary = 213   # bright pink/purple
  accent    = 220   # gold
  success   = 114   # green
  error     = 203   # red
  warning   = 214   # orange
  muted     = 245
  border    = 141
  text      = 255
  dim       = 239
  surface   = 236
  highlight = 122   # teal

BANNER_TITLE = "INDONIME"
BANNER_SUB = "Subtitle Indonesia Anime Searcher — cari · tonton · nikmati"


def banner_header():
  """Header tuple for tuiko select/prompt frames (gradient title + subtitle)."""
  return (BANNER_TITLE, style(f"  {BANNER_SUB}", theme.muted))


def print_banner():
  """Centered gradient banner outside interactive frames."""
  w = term_width()
  title = grad(f"  {BANNER_TITLE}  ", theme.grad)
  print()
  print(" " * max((w - len(strip_ansi(title))) // 2, 0) + title)
  print(" " * max((w - len(BANNER_SUB)) // 2, 0) + style(BANNER_SUB, Palette.muted))
  print()


# ── Section header ────────────────────────
def print_header(title: str, icon: str = ""):
  """Styled section header."""
  print()
  label = f"  {icon}  {title}" if icon else f"  {title}"
  print(style(label, 1, Palette.accent))
  print(sep(max(term_width() - 2, 10), color=Palette.border))
  print()


# ── Status messages ───────────────────────
def _print_msg(icon: str, color: int, msg: str, dim=False):
  print(f"  {style(icon, 1, color)}  {style(msg, Palette.dim) if dim else style(msg, Palette.text)}")


def print_step(msg: str):
  _print_msg("➜", Palette.primary, msg, dim=True)


def print_success(msg: str):
  _print_msg("✓", Palette.success, msg)


def print_error(msg: str):
  _print_msg("✘", Palette.error, msg)


def print_warning(msg: str):
  _print_msg("⚠", Palette.warning, msg)


def print_separator():
  """Faint horizontal rule."""
  print()
  print(sep(max(term_width() - 2, 10), color=Palette.surface))
  print()


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
  print()
  w = term_width()
  line = f"  ✦  {style('Indonime', 1, Palette.secondary)}  —  made with love for anime fans  ✦"
  print(" " * max((w - len(strip_ansi(line))) // 2, 0) + line)
  print()


# ── Loading bar (pre-tuiko rich design) ─────
console = Console()

def make_progress_bar(show_size=False):
  """Styled loading/progress bar — spinner, bar, pct, elapsed.

  Usage:
    with make_progress_bar() as progress:
      task = progress.add_task("...", total=100)
  """
  columns = [
    SpinnerColumn(spinner_name="dots", style="#00d4ff"),
    TextColumn("[progress.description]{task.description}", style="#d1d5db"),
    BarColumn(bar_width=None, style="#1f2937",
              complete_style="#00d4ff", pulse_style="#a855f7"),
  ]
  if show_size:
    columns.append(DownloadColumn(binary_units=True))
  columns.append(TaskProgressColumn(text_format="{task.percentage:>3.0f}%",
                                    style="#d1d5db"))
  columns.append(TimeElapsedColumn())
  return Progress(*columns, console=console, expand=True, transient=True)
