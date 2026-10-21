"""Shared drawing helpers: sprite grids -> QImage -> crisp (or supersampled) painting."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

import sprites

_RGBA = {k: QColor(v).rgba() for k, v in sprites.PAL.items()}


def grid_to_image(g):
    img = QImage(len(g[0]), len(g), QImage.Format_ARGB32)
    img.fill(0)
    for y, row in enumerate(g):
        for x, ch in enumerate(row):
            if ch != "." and ch in _RGBA:
                img.setPixel(x, y, _RGBA[ch])
    return img


def draw_image(p, img, target, scale):
    """Paint a one-pixel-per-cell image at `scale` screen pixels per cell."""
    if abs(scale - round(scale)) < 0.01:              # whole number: crisp pixels
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        p.drawImage(target, img)
    else:                                              # e.g. 1.5: supersample, then shrink
        big = img.scaled(img.width() * 4, img.height() * 4,
                         Qt.IgnoreAspectRatio, Qt.FastTransformation)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(target, big)
