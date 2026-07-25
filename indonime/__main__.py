from indonime import main

try:
  main()
except KeyboardInterrupt:
  from rich.console import Console
  Console().print(f'\n[yellow]Sayonara![/yellow]')
