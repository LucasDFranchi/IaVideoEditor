#!/usr/bin/env python3
"""
GUI Launcher for IAVideoEditor
Run this to open the GUI application
"""

import sys
from pathlib import Path

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from src.gui import main as gui_main
    gui_main()
