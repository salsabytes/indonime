# Banner, headers, status messages — tuiko-based; loading bar juga dari tuiko.
import sys

from tuiko import grad, progress, sep, strip_ansi, style, term_width, theme

# Windows pipes default to cp1252 which can't encode emoji — force UTF-8 so
# plain print() never crashes (real console + tuiko frames are unaffected).
for _s in (sys.stdout, sys.stderr):
  if hasattr(_s, "reconfigure"):
    try:
      _s.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):  # io.UnsupportedOperation: can't change encoding
      pass

class Palette:
  primary = 117   # sky cyan
  accent = 220   # gold
  error = 203   # red
  warning = 214   # orange
  secondary = theme.accent_bright   # bright pink/purple
  success = theme.success
  muted = theme.muted
  border = theme.border
  text = theme.text
  dim = theme.faint
  surface = theme.dim_bg

BANNER_TITLE = "INDONIME"
BANNER_SUB = "Subtitle Indonesia Anime Searcher — cari · tonton · nikmati"


# Header tuple for tuiko select/prompt frames (gradient title + subtitle).
def banner_header():
  return (BANNER_TITLE, style(f"  {BANNER_SUB}", theme.muted))


# Centered gradient banner outside interactive frames.
def print_banner():
  w = term_width()
  title = grad(f"  {BANNER_TITLE}  ", theme.grad)
  print()
  print(" " * max((w - len(strip_ansi(title))) // 2, 0) + title)
  print(" " * max((w - len(BANNER_SUB)) // 2, 0) + style(BANNER_SUB, Palette.muted))
  print()


# Styled section header.
def print_header(title: str, icon: str = ""):
  print()
  label = f"  {icon}  {title}" if icon else f"  {title}"
  print(style(label, 1, Palette.accent))
  print(sep(max(term_width() - 2, 10), color=Palette.border))
  print()


# Status messages
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


# Faint horizontal rule.
def print_separator():
  print()
  print(sep(max(term_width() - 2, 10), color=Palette.surface))
  print()


# Post-play menu: context-aware command list.
def make_postplay_actions(current_idx: int, total: int) -> list[str]:
  actions = []
  if current_idx + 1 < total:
    actions.append("▶  NEXT")
  if current_idx > 0:
    actions.append("◀  PREV")
  actions.append("↺  REPLAY")
  actions.append("⚙  QUALITY")
  actions.append("✖  QUIT")
  return actions


# Clean centered footer.
def make_footer():
  print()
  w = term_width()
  line = f"  ✦  {style('Indonime', 1, Palette.secondary)}  —  made with love for anime fans  ✦"
  print(" " * max((w - len(strip_ansi(line))) // 2, 0) + line)
  print()
