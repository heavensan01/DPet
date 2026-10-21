"""One small, simple speech bubble used for every message above the hamster."""
from PySide6.QtCore import Qt, QRect, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF

OUTLINE = QColor("#3A2218")
TEXT = QColor("#3A2218")
FILL = QColor("#FFF6E5")


def _fit(fm, text, max_w, max_lines=2):
    """Wrap to at most max_lines; add '...' if the text is still too long."""
    flags = int(Qt.TextWordWrap)
    line_h = fm.height()
    while True:
        r = fm.boundingRect(QRect(0, 0, max_w, 1000), flags, text)
        if r.height() <= line_h * max_lines or len(text) <= 3:
            return text, r
        text = text[:-4].rstrip() + "..."


def draw_bubble(p, text, kind, cx, bottom, win_w):
    """Draw the bubble centred on cx with its tail tip just above `bottom` (top of the head).
    `kind` is accepted for compatibility; every message uses the same style."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, False)
    font = QFont("Consolas")
    font.setStyleHint(QFont.Monospace)
    font.setPixelSize(10)
    font.setBold(True)
    p.setFont(font)
    fm = p.fontMetrics()
    pad_x, pad_y, tail_h = 6, 3, 5
    max_w = max(40, min(win_w - 6, 130)) - 2 * pad_x
    text, r = _fit(fm, text, max_w)
    w = r.width() + 2 * pad_x + 2
    h = r.height() + 2 * pad_y + 2
    x = int(min(max(cx - w / 2, 2), win_w - w - 2))
    y = int(max(1, bottom - h - tail_h - 1))

    path = QPainterPath()                                    # box with notched corners
    c = 2
    path.moveTo(x + c, y)
    path.lineTo(x + w - c, y)
    path.lineTo(x + w - c, y + 1)
    path.lineTo(x + w - 1, y + 1)
    path.lineTo(x + w - 1, y + c)
    path.lineTo(x + w, y + c)
    path.lineTo(x + w, y + h - c)
    path.lineTo(x + w - 1, y + h - c)
    path.lineTo(x + w - 1, y + h - 1)
    path.lineTo(x + w - c, y + h - 1)
    path.lineTo(x + w - c, y + h)
    path.lineTo(x + c, y + h)
    path.lineTo(x + c, y + h - 1)
    path.lineTo(x + 1, y + h - 1)
    path.lineTo(x + 1, y + h - c)
    path.lineTo(x, y + h - c)
    path.lineTo(x, y + c)
    path.lineTo(x + 1, y + c)
    path.lineTo(x + 1, y + 1)
    path.lineTo(x + c, y + 1)
    path.closeSubpath()
    p.setPen(QPen(OUTLINE, 1.5, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin))
    p.setBrush(FILL)
    p.drawPath(path)

    tx = int(min(max(cx - 4, x + 5), x + w - 13))            # little tail pointing at the hamster
    p.drawPolygon(QPolygonF([QPointF(tx, y + h), QPointF(tx + 8, y + h), QPointF(tx + 3, y + h + tail_h)]))
    p.setPen(Qt.NoPen)                                       # hide the seam between box and tail
    p.setBrush(FILL)
    p.drawRect(tx + 1, y + h - 1, 7, 2)

    p.setPen(TEXT)
    p.drawText(QRect(x + pad_x + 1, y + pad_y + 1, w - 2 * pad_x - 2, h - 2 * pad_y - 2),
               int(Qt.AlignCenter) | int(Qt.TextWordWrap), text)
    p.restore()
