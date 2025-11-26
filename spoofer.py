#!/usr/bin/env python3
"""
PhantomID - Advanced Hardware ID Spoofer
Main entry point for the spoofer application
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.gui import main

if __name__ == "__main__":
    main()