"""Draggable spinning wheel and water bottle (separate always-on-top windows)."""
import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QMenu, QWidget

import render

DATA = json.loads((Path(__file__).parent / "assets" / "props.json").read_text())
WHEEL_FRAMES = len(DATA["wheel"]["frames"])
BOTTLE_LEVELS = len(DATA["bottle"]["levels"])
MAX_SPEED = 11.0          # wheel degrees per tick (30 ms) at full speed
# how far (in cells) the hamster steps out beyond the wheel's right edge when it leaves
EXIT_EXTENT = max(0, max(len(f["grid"][0]) + f["ox"] for f in DATA["wheel"]["exit"]) - DATA["wheel"]["w"])


class PropWindow(QWidget):
    def __init__(self, kind, cfg, pet):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.kind = kind
        self.cfg = cfg
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground)
        d = DATA[kind]
        self.cw = d["w"]                                   # sprite width in cells
        self.sprite_h = d["h"]                             # sprite height in cells
        self.ch = d["h"] if kind == "wheel" else d["ground"]   # window height in cells
        self.flip = False
        self.dragging = False
        self.settled = True
        self.vy = 0.0
        self.drag_off = None
        self.frame_idx = 0
        self.angle = 0.0
        self.speed = 0.0
        self.target_speed = 0.0
        self.level = float(cfg.get("water_level", 1.0))
        self._cache = {}
        self.fall_timer = QTimer(self)
        self.fall_timer.timeout.connect(self._fall)
        self.apply_scale(pet.S, keep_pos=False)

    # ---------------------------------------------------------- geometry
    def _geo(self):
        return QGuiApplication.primaryScreen().availableGeometry()

    def ground_y(self):
        return self._geo().bottom() - self.height() + 1

    def apply_scale(self, S, keep_pos=True):
        self.S = S
        self._cache.clear()
        self.resize(int(self.cw * S), int(self.ch * S))
        if keep_pos:
            self.place_from_config()
        else:
            self.place_from_config()

    def default_x(self):
        geo = self._geo()
        S = self.S
        wheel_w = int(DATA["wheel"]["w"] * S)
        margin = 6 + int(EXIT_EXTENT * S)             # leave room for the hamster to step out
        if self.kind == "wheel":
            return geo.right() - wheel_w - margin
        return geo.right() - wheel_w - margin - 80 - self.width()

    def _clamp_x(self, x):
        geo = self._geo()
        return min(max(x, geo.left()), geo.right() - self.width())

    def faces_right(self):
        """Bottle on the left half of the screen -> nozzle turns right; right half -> nozzle turns left."""
        geo = self._geo()
        return (self.x() + self.width() / 2.0) < (geo.left() + geo.width() / 2.0)

    def _auto_flip(self):
        if self.kind == "bottle":
            f = self.faces_right()
            if f != self.flip:
                self.flip = f
                self.update()

    def place_from_config(self):
        geo = self._geo()
        frac = self.cfg.get(self.kind + "_x")
        if frac is None:
            x = self.default_x()
        else:
            x = int(geo.left() + float(frac) * geo.width())
        x = self._clamp_x(x)
        self.move(x, self.ground_y())
        self.settled = True
        self._auto_flip()

    def save_pos(self):
        geo = self._geo()
        self.cfg[self.kind + "_x"] = round((self.x() - geo.left()) / max(1, geo.width()), 4)
        self.cfg.save()

    # ---------------------------------------------------------- animation
    def level_index(self):
        return min(BOTTLE_LEVELS - 1, max(0, int(round((1.0 - self.level) * (BOTTLE_LEVELS - 1)))))

    def tick(self):
        if not self.isVisible():
            return
        if self.kind == "wheel":
            if self.speed < self.target_speed:
                self.speed = min(self.target_speed, self.speed + 0.22)
            elif self.speed > self.target_speed:
                self.speed = max(self.target_speed, self.speed - 0.30)
            if self.speed > 0:
                self.angle = (self.angle + self.speed) % 45.0
                idx = int(self.angle / (45.0 / WHEEL_FRAMES)) % WHEEL_FRAMES
                if idx != self.frame_idx:
                    self.frame_idx = idx
                    self.update()
        else:
            idx = self.level_index()
            if idx != self.frame_idx:
                self.frame_idx = idx
                self.update()

    def _image(self):
        key = (self.kind, self.frame_idx)
        img = self._cache.get(key)
        if img is None:
            grids = DATA[self.kind]["frames" if self.kind == "wheel" else "levels"]
            img = render.grid_to_image(grids[self.frame_idx])
            self._cache[key] = img
        return img

    def paintEvent(self, _):
        p = QPainter(self)
        if self.flip:
            p.translate(self.width(), 0)
            p.scale(-1, 1)
        target = QRectF(0, 0, self.cw * self.S, self.sprite_h * self.S)
        render.draw_image(p, self._image(), target, self.S)
        p.end()

    # ---------------------------------------------------------- dragging
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = True
            self.settled = False
            self.fall_timer.stop()
            self.drag_off = e.globalPosition().toPoint() - self.pos()
            self.pet.on_prop_grabbed(self)

    def mouseMoveEvent(self, e):
        if self.dragging:
            self.move(e.globalPosition().toPoint() - self.drag_off)
            self._auto_flip()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            geo = self._geo()
            x = self._clamp_x(self.x())
            self.move(x, self.y())
            self._auto_flip()
            self.vy = 0.0
            self.fall_timer.start(16)
            self.pet.on_prop_released(self)

    def _fall(self):
        ground = self.ground_y()
        y = self.y()
        self.vy += 1.4
        y += self.vy
        if y >= ground:
            y = ground
            self.fall_timer.stop()
            self.settled = True
            self.save_pos()
            self.move(self.x(), int(y))
            self.pet.on_prop_settled(self)
            return
        self.move(self.x(), int(y))

    def contextMenuEvent(self, e):
        m = QMenu(self)
        if self.kind == "bottle":
            m.addAction("Refill water", self.pet.refill_water)
            m.addAction("Hamster, go drink!", self.pet.go_drink)
            m.addAction("Hide bottle", lambda: self.pet.set_prop_enabled("bottle", False))
        else:
            m.addAction("Hamster, go run!", self.pet.go_run)
            m.addAction("Hide wheel", lambda: self.pet.set_prop_enabled("wheel", False))
        m.exec(e.globalPos())
