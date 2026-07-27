from InquirerPy.utils import get_style
from rich.console import Console

console = Console()

def print_banner():
  console.clear()
  console.print(r"""[bold cyan]
 ___           _             _                 
|_ _|_ __   __| | ___  _ __ (_)_ __ ___   ___  
 | || '_ \ / _` |/ _ \| '_ \| | '_ ` _ \ / _ \ 
 | || | | | (_| | (_) | | | | | | | | | |  __/ 
|___|_| |_|\__,_|\___/|_| |_|_|_| |_| |_|\___|
                
    [/bold cyan][italic]Subtitle Indonesia Anime Searcher[/italic]
  """)

def make_style():
  return get_style({
    'questionmark': '#5fafd7 bold',
    'question': '#d1d1d1',
    'instruction': '#454545 italic',
    'pointer': '#5fafd7 bold',
    'answere': '#5fafd7',
  }, style_override=False)
