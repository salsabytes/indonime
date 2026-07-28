"""Rich UI helpers — banner, tables, styles, components."""
from InquirerPy.utils import get_style
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeElapsedColumn,
    SpinnerColumn, TaskProgressColumn, DownloadColumn,
)
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, HEAVY_HEAD, MINIMAL, SQUARE
from rich.style import Style

console = Console()

# ── Color palette ────────────────────────────────────────────────
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

# ── Banner ────────────────────────────────────────────────────────
BANNER_ART = r"""
   ▄▄▄▄▄▄▄    ▄▄▄▄▄▄   ▄▄▄▄▄▄▄   ▄       ▄
   ██▀▀▀▀▀██  ██▀▀▀▀██  ██▀▀▀▀▀▀  ██       ██
   ██    ██   ██    ██  ██         ██       ██
   ██████▀    ███████   ███████    ██       ██
   ██         ██   ▀██  ██         ██       ██
   ██         ██    ██  ██▄▄▄▄▄▄  ██▄▄▄▄▄▄██
   ▀▀         ▀▀    ▀▀  ▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀
"""


def _gradient_text(text: str, colors: list[str] = None) -> Text:
    """Multi-color gradient across text lines."""
    if colors is None:
        colors = ["#00d4ff", "#2dd4bf", "#a855f7"]
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
                # pick segment
                seg = t * (len(colors) - 1)
                seg_i = int(seg)
                seg_t = seg - seg_i
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


# ── Cached banner ─────────────────────────────────────────────────
_BANNER_PANEL = None

def print_banner():
    """Clear screen and show the gradient banner."""
    global _BANNER_PANEL
    console.clear()
    if _BANNER_PANEL is None:
        gradient = _gradient_text(BANNER_ART)
        subtitle = Text("  Subtitle Indonesia Anime Searcher", style=f"italic {Palette.muted}")
        version = Text("  v1.0", style=f"dim {Palette.dim}")
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


# ── Section header ────────────────────────────────────────────────
def print_header(title: str, icon: str = ""):
    """Section header with styled rule."""
    console.print()
    label = f"  {icon}  {title}" if icon else f"    {title}"
    console.print(Rule(title=Text(label, style=f"bold {Palette.accent}"), style=Palette.border))
    console.print()


# ── Status & messages ────────────────────────────────────────────
def styled_status(message: str) -> str:
    """Return a styled status spinner message."""
    return f"[bold {Palette.primary}]{message}[/bold {Palette.primary}]"


def print_step(msg: str):
    """Progress step with arrow indicator."""
    console.print(f"  [bold {Palette.primary}]➜[/bold {Palette.primary}]  [dim]{msg}[/dim]")


def print_success(msg: str):
    """Green success message."""
    console.print(f"  [bold {Palette.success}]✓[/bold {Palette.success}]  {msg}")


def print_error(msg: str):
    """Red error message."""
    console.print(f"  [bold {Palette.error}]✘[/bold {Palette.error}]  {msg}")


def print_warning(msg: str):
    """Yellow warning message."""
    console.print(f"  [bold {Palette.warning}]⚠[/bold {Palette.warning}]  {msg}")


def print_info(msg: str):
    """Info message in muted style."""
    console.print(f"  [bold {Palette.muted}]ℹ[/bold {Palette.muted}]  [italic]{msg}[/italic]")


def print_separator():
    """A faint horizontal rule."""
    console.print()
    console.print(Rule(style=Palette.surface))
    console.print()


# ── Episode Table ─────────────────────────────────────────────────
_LAST_TABLE_EPS = None
_LAST_TABLE = None

def make_episode_table(episode_list) -> Table:
    """Create a polished Rich Table for episode display. Cached per list identity."""
    global _LAST_TABLE_EPS, _LAST_TABLE
    if _LAST_TABLE_EPS is episode_list:
        return _LAST_TABLE

    table = Table(
        box=SQUARE,
        border_style=Palette.border,
        header_style=Style(color=Palette.primary, bold=True),
        title=f"[bold]📋  Episode List  —  [dim]{len(episode_list)} eps[/dim][/bold]",
        title_style=Palette.muted,
        padding=(0, 2),
        show_edge=True,
        show_lines=True,
        expand=True,
    )
    table.add_column(" EP", style=Palette.secondary, width=7, no_wrap=True, justify="center")
    table.add_column("Title", style=Palette.text, ratio=1)
    table.add_column("", style=Palette.dim, width=3, justify="center")

    for i, ep in enumerate(episode_list):
        ep_num = f"EP{i+1:02d}"
        title = (ep["title"][:58] + "…") if len(ep["title"]) > 60 else ep["title"]
        table.add_row(ep_num, title, "▶")

    _LAST_TABLE_EPS = episode_list
    _LAST_TABLE = table
    return table


# ── Post-play command menu ───────────────────────────────────────
def make_postplay_actions(current_idx: int, total: int) -> list[str]:
    """Build context-aware post-play command list."""
    actions = []
    if current_idx + 1 < total:
        actions.append("▶  NEXT")
    if current_idx > 0:
        actions.append("◀  PREV")
    # always available
    if "▶  NEXT" not in actions:
        # last episode, offer 'replay' as main action
        actions.insert(0, "↺  REPLAY")
    actions.append("⚙  QUALITY")
    actions.append("✖  QUIT")
    return actions


# ── Footer ────────────────────────────────────────────────────────
def make_footer():
    """Print a clean centered footer."""
    console.print()
    text = Text.assemble(
        ("  ✦  ", f"italic dim {Palette.dim}"),
        ("Indonime", f"italic bold {Palette.secondary}"),
        ("  —  made with love for anime fans  ✦", f"italic dim {Palette.dim}"),
    )
    console.print(Align.center(text))


def make_style():
    """Return InquirerPy custom style."""
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


# ── Download Progress Bar ────────────────────────────────────────
def make_progress_bar(transient=True, show_size=False):
    """Create a beautifully styled download progress bar.

    Usage:
        with make_progress_bar() as progress:
            task = progress.add_task("🌀 Downloading...", total=100)
            progress.update(task, completed=N)
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