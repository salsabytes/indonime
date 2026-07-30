#!/usr/bin/env python3
from indonime import main

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    from rich.console import Console
    Console().print(f'\n[yellow]Sayonara![/yellow]')
