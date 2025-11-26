import sys
import os
from pathlib import Path

_root = Path(__file__).resolve().parent
_src_candidates = [
    _root / 'src',
    Path.cwd() / 'src',
]
for p in _src_candidates:
    if p.exists():
        sys.path.insert(0, str(p))

try:
    from ui.gui import main
except ImportError:
    try:
        from src.ui.gui import main  # namespace package fallback
    except Exception as e:
        raise ImportError(f"Failed to import GUI module: {e}")

if __name__ == "__main__":
    main()

