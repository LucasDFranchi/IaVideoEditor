#!/usr/bin/env python3
"""Launcher for IAVideoEditor - supports both CLI and GUI modes."""

import sys
from pathlib import Path

def main():
    """Main launcher entry point."""
    if len(sys.argv) > 1:
        # CLI mode - use original main.py
        from src.main import main as cli_main
        cli_main()
    else:
        # GUI mode - use gui.py
        from src.gui import main as gui_main
        gui_main()

if __name__ == "__main__":
    main()
