import os
from typing import Optional

try:
    from PySide6.QtGui import QPixmap
except Exception:
    QPixmap = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _candidate_paths(game_name: str):
    base_dir = os.path.join(PROJECT_ROOT, 'assets', 'images', 'games')
    candidates = [
        os.path.join(base_dir, f"{game_name}.png"),
        os.path.join(base_dir, f"{game_name}.jpg"),
        os.path.join(base_dir, f"{game_name.lower()}.png"),
        os.path.join(base_dir, f"{game_name.lower()}.jpg"),
    ]
    return candidates

def get_game_bg_pixmap(game_name: str) -> Optional['QPixmap']:
    if QPixmap is None:
        return None
    for path in _candidate_paths(game_name):
        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                return pix
    return None