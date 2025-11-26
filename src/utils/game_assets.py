import os
from typing import Optional, List
from pathlib import Path
try:
    from PySide6.QtGui import QPixmap, QImage, QPainter, QLinearGradient, QColor
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtGui import QFont
except Exception:
    QPixmap = None
    QImage = None
    QPainter = None
    QLinearGradient = None
    QColor = None
    QSvgRenderer = None
    QFont = None

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
        os.path.join(base_dir, f"{game_name}.jpeg"),
        os.path.join(base_dir, f"{game_name}.webp"),
        os.path.join(base_dir, f"{game_name}.svg"),
        os.path.join(base_dir, f"{game_name.lower()}.png"),
        os.path.join(base_dir, f"{game_name.lower()}.jpg"),
        os.path.join(base_dir, f"{game_name.lower()}.jpeg"),
        os.path.join(base_dir, f"{game_name.lower()}.webp"),
        os.path.join(base_dir, f"{game_name.lower()}.svg"),
    ]
    return candidates

def _rasterize_svg_to_pixmap(svg_path: str, width: int = 512, height: int = 256) -> Optional['QPixmap']:
    if QSvgRenderer is None or QImage is None or QPainter is None:
        return None
    try:
        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            return None
        img = QImage(width, height, QImage.Format.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        renderer.render(painter)
        painter.end()
        pm = QPixmap.fromImage(img)
        return pm if (pm and not pm.isNull()) else None
    except Exception:
        return None

def _fallback_gradient_pixmap(width: int = 512, height: int = 256) -> Optional['QPixmap']:
    if QPixmap is None or QPainter is None or QLinearGradient is None or QColor is None:
        return None
    pm = QPixmap(width, height)
    pm.fill(QColor(30, 34, 41))
    painter = QPainter(pm)
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(102, 126, 234))
    grad.setColorAt(1.0, QColor(118, 75, 162))
    painter.fillRect(0, 0, width, height, grad)
    painter.end()
    return pm

def _pixmap_from_bytes(data: bytes) -> Optional['QPixmap']:
    if QPixmap is None:
        return None
    try:
        pm = QPixmap()
        if pm.loadFromData(data):
            return pm if not pm.isNull() else None
    except Exception:
        return None
    return None

def _generate_text_logo_pixmap(game_name: str, width: int = 512, height: int = 256) -> Optional['QPixmap']:
    if QPixmap is None or QPainter is None or QFont is None or QColor is None:
        return _fallback_gradient_pixmap(width, height)
    pm = QPixmap(width, height)
    pm.fill(QColor(30, 34, 41))
    painter = QPainter(pm)
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(102, 126, 234))
    grad.setColorAt(1.0, QColor(118, 75, 162))
    painter.fillRect(0, 0, width, height, grad)
    font = QFont("Segoe UI", 44)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(0, 0, 0, 220))
    text = game_name.upper()
    rect = pm.rect()
    painter.drawText(rect, 0x84, text)  # Qt.AlignCenter (0x84)
    painter.end()
    return pm

def get_text_logo_pixmap(game_name: str, width: int = 512, height: int = 256) -> Optional['QPixmap']:
    return _generate_text_logo_pixmap(game_name, width, height)

def get_game_bg_pixmap(game_name: str) -> Optional['QPixmap']:
    if QPixmap is None:
        return None
    for path in _candidate_paths(game_name):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            if path.lower().endswith('.svg'):
                pm = _rasterize_svg_to_pixmap(path)
                if pm is not None:
                    return pm
            else:
                pix = QPixmap(path)
                if not pix.isNull():
                    return pix
    urls_map: dict[str, List[str]] = {
        'FiveM': [
            'https://upload.wikimedia.org/wikipedia/commons/5/5a/FiveM-Logo.png',
        ],
        'Fortnite': [
            'https://upload.wikimedia.org/wikipedia/commons/7/7c/Fortnite_F_lettermark_logo.png',
        ],
        'Valorant': [
            'https://freelogopng.com/images/all_img/1664302686valorant-icon-png.png',
        ],
        'Minecraft': [
            'https://cdn.freebiesupply.com/logos/large/2x/minecraft-1-logo-svg-vector.svg',
        ],
        'Roblox': [
            'https://upload.wikimedia.org/wikipedia/commons/7/7e/Roblox_Logo_2022.jpg',
        ],
        'CS:GO': [
            'https://cdn2.steamgriddb.com/icon/01063bcf7624297fbb408495bcb62904/8/512x512.png',
        ],
    }
    candidates = urls_map.get(game_name, [])
    if not candidates:
        return None
    import urllib.request, re
    headers = {'User-Agent': 'PhantomID/1.0', 'Accept': 'image/*', 'Referer': 'https://www.google.com'}
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                ctype = resp.info().get_content_type()
                if not (ctype.startswith('image/')):
                    continue
                data = resp.read()
            # Try loading directly from bytes; if successful, cache as PNG
            pm = _pixmap_from_bytes(data)
            if pm is not None:
                base_dir = Path(PROJECT_ROOT) / 'assets' / 'images' / 'games'
                base_dir.mkdir(parents=True, exist_ok=True)
                safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", game_name)
                out_path = base_dir / f"{safe_name}.png"
                try:
                    pm.save(str(out_path), 'PNG')
                except Exception:
                    pass
                return pm
            # If content is SVG and QtSvg is available, cache and rasterize
            if 'svg' in ctype:
                base_dir = Path(PROJECT_ROOT) / 'assets' / 'images' / 'games'
                base_dir.mkdir(parents=True, exist_ok=True)
                safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", game_name)
                out_path = base_dir / f"{safe_name}.svg"
                with open(out_path, 'wb') as f:
                    f.write(data)
                pm2 = _rasterize_svg_to_pixmap(str(out_path))
                if pm2 is not None:
                    return pm2
        except Exception:
            continue
    # Final fallback: generate a themed text logo
    pm_fallback = _generate_text_logo_pixmap(game_name)
    if pm_fallback is not None:
        try:
            base_dir = Path(PROJECT_ROOT) / 'assets' / 'images' / 'games'
            base_dir.mkdir(parents=True, exist_ok=True)
            out_path = base_dir / f"{game_name}.png"
            pm_fallback.save(str(out_path), 'PNG')
        except Exception:
            pass
        return pm_fallback
    return _fallback_gradient_pixmap()
