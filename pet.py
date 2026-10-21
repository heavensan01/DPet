import math  # noqa: F401
import random
import time
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QAction, QGuiApplication
from PySide6.QtWidgets import QWidget, QMenu

import bubble
import props
import render
import sprites
from render import grid_to_image  # noqa: F401  (used by main.py)

WHEEL = props.DATA["wheel"]
BOTTLE = props.DATA["bottle"]


def rand_range(pair):
    lo, hi = pair
    return random.uniform(lo, hi)


class PetWindow(QWidget):
    BUBBLE_SPACE = 50

    def __init__(self, cfg, tray=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.cfg = cfg
        self.tray = tray
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._apply_scale(float(cfg.get("scale", 1.5)))

        self.dir = 1
        self.speed = float(cfg.get("speed", 1.2))
        self.vy = 0.0
        self.state = "walk"          # walk / idle / eat / nap / sleep / inter
        self.anim_t = 0
        self.state_until = 0.0
        self.happy_until = 0.0
        self.msg = ""
        self.msg_kind = "hello"
        self.dragging = False
        self.moved = False
        self.drag_off = None
        self.goal = None             # walking to the wheel / bottle
        self.inter = None            # climbing / drinking in progress
        self.queue = None            # next thing to do after leaving the wheel / bottle

        now = time.monotonic()
        self.next_activity = now + rand_range(cfg["activity_gap_seconds"])
        self.next_jump = now + rand_range(cfg["jump_gap_seconds"])
        self.next_visit = {"wheel": now + random.uniform(40, 80),
                           "bottle": now + random.uniform(90, 140)}
        wall = datetime.now()
        self.last_water = wall
        self.last_study = wall
        self.sleep_fired_on = None

        geo = self._geo()
        self.fx = float(random.randint(geo.left(), max(geo.left(), geo.right() - self.W)))
        self.move(int(self.fx), self._ground())

        self.wheel = props.PropWindow("wheel", cfg, self)
        self.bottle = props.PropWindow("bottle", cfg, self)

        self.msg_timer = QTimer(self, singleShot=True)
        self.msg_timer.timeout.connect(self._clear_msg)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)
        self.rem_timer = QTimer(self)
        self.rem_timer.timeout.connect(self.check_reminders)
        self.rem_timer.start(20000)

    def show_all(self):
        if self.cfg.get("wheel_on", True):
            self.wheel.show()
        if self.cfg.get("bottle_on", True):
            self.bottle.show()
        self.show()
        self.raise_()

    # ------------------------------------------------------------ layout
    def _apply_scale(self, s):
        self.S = max(1.0, s)
        self.sw = int(sprites.CW * self.S)
        self.sh = int(sprites.CH * self.S)
        self.W = max(150, self.sw + 26)
        self.H = self.sh + self.BUBBLE_SPACE
        self.resize(self.W, self.H)

    def set_scale(self, s):
        self.cfg["scale"] = s
        self.cfg.save()
        self._abort_inter()
        self.goal = None
        self._apply_scale(s)
        self.move(int(self.fx), self._ground())
        self.wheel.apply_scale(self.S)
        self.bottle.apply_scale(self.S)

    def _geo(self):
        return QGuiApplication.primaryScreen().availableGeometry()

    def _ground(self):
        return self._geo().bottom() - self.H + 1

    # ------------------------------------------------------------ speech
    def say(self, text, kind="hello", ms=4500, notify=False):
        if len(text) > 42:
            text = text[:39] + "..."
        self.msg, self.msg_kind = text, kind
        self.msg_timer.start(ms)
        if notify and self.tray:
            self.tray.showMessage(self.cfg.get("pet_name", "Dpet"), text)
        self.update()

    def _clear_msg(self):
        self.msg = ""
        self.update()

    # ------------------------------------------------------------ props
    def _prop_for(self, kind):
        return self.wheel if kind == "wheel" else self.bottle

    def _prop_ready(self, kind):
        p = self._prop_for(kind)
        if not p.isVisible() or p.dragging or not p.settled:
            return False
        if kind == "bottle" and p.level < 0.12:
            return False
        return True

    def on_prop_grabbed(self, prop):
        if self.goal and self.goal["prop"] is prop:
            self.goal = None
        if self.inter and self.inter["prop"] is prop:
            self._abort_inter()

    def on_prop_released(self, prop):
        self.raise_()

    def on_prop_settled(self, prop):
        self.raise_()
        # the user just put it down: the hamster goes to try it out soon
        self.next_visit[prop.kind] = time.monotonic() + random.uniform(2.5, 4.5)

    def set_prop_enabled(self, kind, on):
        prop = self._prop_for(kind)
        self.cfg[kind + "_on"] = bool(on)
        self.cfg.save()
        if not on:
            if self.goal and self.goal["prop"] is prop:
                self.goal = None
            if self.inter and self.inter["prop"] is prop:
                self._abort_inter()
            prop.hide()
        else:
            prop.place_from_config()
            prop.show()
            self.raise_()

    def refill_water(self):
        self.bottle.level = 1.0
        self.cfg["water_level"] = 1.0
        self.cfg.save()
        self.say("Fresh water!", "nice", 3000)

    def start_goal(self, kind):
        if self.inter or not self._prop_ready(kind):
            return False
        prop = self._prop_for(kind)
        mirror = (self.fx + self.W / 2.0) > (prop.x() + prop.width() / 2.0)
        if kind == "bottle":
            mirror = prop.faces_right()   # nozzle points toward the screen centre: stand on that side
        start_idx = 1
        seq = WHEEL["seq"] if kind == "wheel" else BOTTLE["seq"]
        self.goal = {"kind": kind, "prop": prop, "mirror": mirror,
                     "first": seq[start_idx], "start_idx": start_idx}
        self.dir = -1 if mirror else 1
        return True

    def go_run(self):
        self._command("wheel")

    def go_drink(self):
        self._command("bottle")

    def _command(self, kind):
        """User asked: go to the wheel / bottle now (finish whatever it is doing first)."""
        prop = self._prop_for(kind)
        if not prop.isVisible():
            self.say("Show it first!", "okay", 3000)
            return
        if kind == "bottle" and prop.level < 0.12:
            self.say("Bottle empty!", "sorry", 4000)
            return
        if self.inter:
            if self.inter["kind"] == kind:
                return
            self.queue = kind                 # climb out / step away first, then go
            self.inter["stop"] = True
            self.say("Okay, one sec!", "okay", 2500)
            return
        if self.state in ("sleep", "nap", "idle", "eat"):
            self.set_state("walk")
        self.goal = None
        if self.start_goal(kind):
            self.say("Let's go!", "go", 2500)
        else:
            self.say("Not now!", "worry", 2500)

    def _check_visits(self, now):
        """Automatic visits: every few minutes it goes to run / drink by itself."""
        if self.inter or self.goal or self.dragging or self.state == "sleep":
            return
        for kind, gap_key in (("wheel", "wheel_gap_minutes"), ("bottle", "drink_gap_minutes")):
            if now < self.next_visit[kind]:
                continue
            self.next_visit[kind] = now + rand_range(self.cfg[gap_key]) * 60.0
            prop = self._prop_for(kind)
            if not prop.isVisible():
                continue
            if kind == "bottle" and prop.level < 0.12:
                self.say("Bottle empty!", "sorry", 4000)
                continue
            if not self._prop_ready(kind):
                self.next_visit[kind] = now + 5.0
                continue
            if self.state in ("idle", "eat", "nap"):
                self.set_state("walk")
            self.start_goal(kind)
            return

    # --- where the walking hamster must stop so the climb / drink frames line up
    def _goal_target_fx(self):
        g = self.goal
        prop = g["prop"]
        if prop.dragging or not prop.settled or not prop.isVisible():
            return None
        S = self.S
        data = g["first"]
        w = len(data["grid"][0])
        ox = data["ox"]
        x0w = (sprites.CW - sprites.WALK_W) // 2
        base = (self.W - self.sw) / 2.0
        if not g["mirror"]:
            edge = prop.x() + (ox + w) * S
            off = base + (x0w + sprites.WALK_W) * S
        else:
            edge = prop.x() + (prop.cw - (ox + w)) * S
            off = base + x0w * S
        return edge - off

    # ------------------------------------------------------------ interaction
    def _seq(self, kind):
        return WHEEL["seq"] if kind == "wheel" else BOTTLE["seq"]

    def _begin_inter(self):
        g = self.goal
        self.goal = None
        prop = g["prop"]
        prop.flip = g["mirror"]
        prop.update()
        self.inter = {"kind": g["kind"], "prop": prop, "m": g["mirror"],
                      "phase": "in", "t": 0, "cur": g["first"], "shown": None,
                      "run_phase": 0.0, "stop": False,
                      "pos": (self.fx, float(self.y())), "from": (self.fx, float(self.y())),
                      "tw": 0}
        self.vy = 0.0
        self.set_state("inter")
        self.msg_timer.stop()
        self.msg = ""
        self.raise_()

    def _inter_target(self, prop, data):
        S = self.S
        grid = data["grid"]
        w, h = len(grid[0]), len(grid)
        m = self.inter["m"]
        left_cells = (prop.cw - (data["ox"] + w)) if m else data["ox"]
        left_px = prop.x() + left_cells * S
        bottom_px = prop.y() + (data["oy"] + h) * S
        x0 = (sprites.CW - w) // 2
        return (left_px - ((self.W - self.sw) / 2.0 + x0 * S), bottom_px - self.H)

    def _start_exit(self, I, prop):
        """Step out on the free side; if the wheel is against a screen edge, turn round."""
        geo = self._geo()
        extent = props.EXIT_EXTENT * self.S
        room = (prop.x() - geo.left()) if I["m"] else (geo.right() - (prop.x() + prop.width()))
        if room < extent * 0.9:
            I["m"] = not I["m"]
        I["phase"], I["t"] = "exit", 0

    def _step_wheel(self, I, prop):
        seq = WHEEL["seq"]
        t = I["t"]
        ph = I["phase"]
        if ph == "in":
            k = 1 + t // 5
            if k > 9:
                if I["stop"]:
                    I["phase"], I["t"] = "down", 0
                else:
                    I["phase"], I["t"] = "run", 0
                    I["run_ticks"] = int(rand_range(self.cfg.get("wheel_run_seconds", [12, 25])) / 0.03)
                    prop.target_speed = props.MAX_SPEED
                return seq[9]
            return seq[k]
        if ph in ("run", "down"):
            ratio = prop.speed / props.MAX_SPEED
            I["run_phase"] += 0.07 + 0.27 * ratio
            if ph == "run" and (t >= I["run_ticks"] or (I["stop"] and t > 20)):
                I["phase"], I["t"] = "down", 0
                prop.target_speed = 0.0
            elif ph == "down":
                prop.target_speed = 0.0
                if prop.speed <= 0.01 and t > 24:
                    self._start_exit(I, prop)
            if prop.speed < 0.3:
                return seq[9]                       # standing in the wheel, ready to step out
            return seq[10 + int(I["run_phase"]) % 10]
        ex = WHEEL["exit"]                          # reaching the exit -> moving away
        k = t // 7
        if k >= len(ex):
            return None
        return ex[k]

    def _step_drink(self, I, prop):
        seq = BOTTLE["seq"]
        t = I["t"]
        ph = I["phase"]
        if ph == "in":                              # reach, grab the nozzle, start to drink
            k = 1 + t // 6
            if k > 3:
                I["phase"], I["t"] = "drink", 0
                I["loops"] = random.randint(3, 5)
                return seq[4]
            return seq[k]
        if ph == "drink":                           # frames 5-12 loop, water level falls
            prop.level = max(0.0, prop.level - 0.00028)
            cyc = t // 5
            at_boundary = cyc % 8 == 0 and cyc > 0
            if prop.level <= 0.005 or (at_boundary and (I["stop"] or cyc >= I["loops"] * 8)):
                I["phase"], I["t"] = "out", 0
                return seq[12]
            return seq[4 + cyc % 8]
        k = 12 + t // 6                             # lifts head, steps back, walks away
        if k > 14:
            return None
        return seq[k]

    def _tick_inter(self):
        I = self.inter
        prop = I["prop"]
        if not prop.isVisible():
            self._abort_inter()
            return
        I["t"] += 1
        data = self._step_wheel(I, prop) if I["kind"] == "wheel" else self._step_drink(I, prop)
        if data is None:
            self._leave_inter(keep_y=False)
            return
        if data is not I["shown"]:                  # new pose: glide from where we are now
            I["shown"] = data
            I["from"] = I["pos"]
            I["tw"] = 0
        I["cur"] = data
        tx, ty = self._inter_target(prop, data)
        I["tw"] += 1
        e = min(1.0, I["tw"] / 4.0)
        e = e * e * (3.0 - 2.0 * e)
        fx0, fy0 = I["from"]
        x = fx0 + (tx - fx0) * e
        y = fy0 + (ty - fy0) * e
        I["pos"] = (x, y)
        self.fx = x
        self.move(int(round(x)), int(round(y)))

    def _leave_inter(self, keep_y):
        I = self.inter
        if not I:
            return
        prop = I["prop"]
        if I["kind"] == "bottle":
            self.cfg["water_level"] = round(prop.level, 3)
            self.cfg.save()
        else:
            prop.target_speed = 0.0
        d = I["cur"]
        w = len(d["grid"][0])
        left_cells = (prop.cw - (d["ox"] + w)) if I["m"] else d["ox"]
        cx = prop.x() + (left_cells + w / 2.0) * self.S
        self.fx = cx - self.W / 2.0
        y = self.y() if keep_y else self._ground()
        self.move(int(self.fx), int(y))
        if I["kind"] == "wheel":                    # stepped out facing the exit side
            self.dir = -1 if I["m"] else 1
        else:                                       # walked away from the bottle
            self.dir = 1 if I["m"] else -1
        kind = I["kind"]
        self.inter = None
        self.vy = 0.0
        self.set_state("walk")
        now = time.monotonic()
        gap_key = "wheel_gap_minutes" if kind == "wheel" else "drink_gap_minutes"
        self.next_visit[kind] = now + rand_range(self.cfg[gap_key]) * 60.0
        self.next_activity = now + rand_range(self.cfg["activity_gap_seconds"])
        self.next_jump = max(self.next_jump, now + 12)
        if self.queue:                              # e.g. "now go and drink!" while it was running
            nxt, self.queue = self.queue, None
            if self._prop_ready(nxt):
                self.start_goal(nxt)

    def _abort_inter(self):
        if self.inter:
            self.queue = None
            self._leave_inter(keep_y=True)

    # ------------------------------------------------------------ behaviour
    def set_state(self, state):
        self.state = state
        self.anim_t = 0

    def start_activity(self, now):
        act = random.choices(["idle", "eat", "nap"], [3, 3, 1])[0]
        self.set_state(act)
        if act == "nap":
            self.state_until = now + random.uniform(40, 80)
        elif act == "eat":
            self.state_until = now + sprites.EAT_TICKS * 0.03 + 0.4
            if random.random() < 0.5:
                self.say("Yum!", "yay", 2500)
        else:
            self.state_until = now + random.uniform(10, 16)
            if random.random() < 0.5:
                self.say("Hmm...", "think", 3500)

    def finish_activity(self, now):
        self.set_state("walk")
        self.dir = random.choice([-1, 1])
        self.next_activity = now + rand_range(self.cfg["activity_gap_seconds"])
        self.next_jump = max(self.next_jump, now + 10)

    def feed(self):
        if self.inter:
            return
        self.goal = None
        now = time.monotonic()
        self.set_state("eat")
        self.state_until = now + sprites.EAT_TICKS * 0.03 + 0.4
        self.say("Yum!", "yay", 2500)

    def go_sleep(self):
        if self.inter:
            self._abort_inter()
        self.goal = None
        self.set_state("sleep")
        self.say("Good Night!", "night", 3000)

    def wake(self):
        now = time.monotonic()
        self.set_state("walk")
        self.next_activity = now + rand_range(self.cfg["activity_gap_seconds"])
        self.say("Good Morning!", "morning", 3000)

    def _tick_walk(self, now, geo, on_ground):
        lo = geo.left() - int(self.W * 0.2)
        hi = geo.right() - self.W + int(self.W * 0.2)
        if self.goal:
            tgt = self._goal_target_fx()
            if tgt is None:
                self.goal = None
                return
            if self.goal["kind"] == "bottle":        # walk to the nozzle side, whichever side we start
                self.dir = 1 if tgt >= self.fx else -1
                if abs(tgt - self.fx) <= self.speed * 2.0:
                    if on_ground:
                        self.dir = -1 if self.goal["mirror"] else 1   # face the nozzle
                        self._begin_inter()
                    return
            else:
                self.dir = -1 if self.goal["mirror"] else 1
                if (self.dir > 0 and self.fx >= tgt) or (self.dir < 0 and self.fx <= tgt):
                    if on_ground:
                        self._begin_inter()
                    return
            self.fx += self.dir * self.speed * 2.0
            if (self.dir < 0 and self.fx < lo) or (self.dir > 0 and self.fx > hi):
                self.fx = min(max(self.fx, lo), hi)  # target not reachable
                self.goal = None
            return
        self.fx += self.dir * self.speed
        if self.fx < lo:
            self.fx, self.dir = lo, 1
        elif self.fx > hi:
            self.fx, self.dir = hi, -1
        if on_ground:
            if now >= self.next_jump:
                self.vy = -7.0
                self.next_jump = now + rand_range(self.cfg["jump_gap_seconds"])
            elif now >= self.next_activity:
                self.start_activity(now)

    def tick(self):
        now = time.monotonic()
        self.anim_t += 1
        self.wheel.tick()
        self.bottle.tick()
        if self.dragging:
            self.update()
            return
        if self.state == "inter":
            self._tick_inter()
            self.update()
            return
        geo = self._geo()
        ground = self._ground()
        y = self.y()
        on_ground = y >= ground and self.vy == 0

        if self.state == "walk":
            self._tick_walk(now, geo, on_ground)
        elif self.state in ("idle", "eat", "nap"):
            if now >= self.state_until:
                self.finish_activity(now)
        if self.state == "inter":                # arrived this tick
            self.update()
            return
        self._check_visits(now)

        if y < ground or self.vy < 0:
            self.vy += 0.55
            y += self.vy
            if y >= ground:
                y, self.vy = ground, 0
        elif y > ground:
            y = ground
        self.move(int(self.fx), int(y))
        self.update()

    def check_reminders(self):
        if not self.cfg.get("reminders_enabled", True) or self.state in ("sleep", "nap"):
            return
        now = datetime.now()
        if now - self.last_water >= timedelta(minutes=self.cfg["water_minutes"]):
            self.last_water = now
            if self.bottle.isVisible() and self.bottle.level < 0.12:
                self.say("Bottle empty!", "sorry", 9000, True)
            else:
                self.say("Drink some water!", "water", 9000, True)
                self.next_visit["bottle"] = 0.0
        elif now - self.last_study >= timedelta(minutes=self.cfg["study_minutes"]):
            self.last_study = now
            self.say("Stretch time!", "go", 9000, True)
        try:
            hh, mm = map(int, self.cfg["sleep_time"].split(":"))
        except Exception:
            return
        if (now.hour, now.minute) == (hh, mm) and self.sleep_fired_on != now.date():
            self.sleep_fired_on = now.date()
            self.say("Good Night!", "night", 12000, True)

    # ------------------------------------------------------------ painting
    def _sprite_state(self):
        if self.dragging:
            return "surprised"
        if time.monotonic() < self.happy_until:
            return "happy"
        if self.vy != 0 or self.y() < self._ground() - 2:
            return "surprised"
        if self.state in ("sleep", "nap"):
            return "sleep"
        return self.state

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        if self.state == "inter" and self.inter:
            g = sprites.prop_frame(self.inter["cur"]["grid"], self.inter["m"])
        else:
            at = self.anim_t * 7 // 4 if (self.goal and self.state == "walk") else self.anim_t
            g = sprites.frame(self._sprite_state(), at, self.dir)
        img = render.grid_to_image(g)
        target = QRectF((self.W - self.sw) / 2, self.H - self.sh, self.sw, self.sh)
        render.draw_image(p, img, target, self.S)
        if self.msg:
            top = next((j for j, r in enumerate(g) if any(c != "." for c in r)), 0)
            head_top = self.H - self.sh + top * self.S
            bubble.draw_bubble(p, self.msg, self.msg_kind, self.W / 2, head_top, self.W)
        p.end()

    # ------------------------------------------------------------ mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.inter:
                self._abort_inter()
            self.goal = None
            self.dragging = True
            self.moved = False
            self.drag_off = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self.dragging:
            target = e.globalPosition().toPoint() - self.drag_off
            if (target - self.pos()).manhattanLength() > 4:
                self.moved = True
            self.move(target)
            self.fx = float(target.x())
            self.vy = 0

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = False
            self.fx = float(self.x())
            if not self.moved:
                self.on_click()

    def on_click(self):
        if self.state in ("sleep", "nap"):
            self.wake()
            return
        self.happy_until = time.monotonic() + 2.5
        self.vy = -5.0
        kind, text = random.choice([("yay", "Yay!"), ("nice", "Nice!"), ("hello", "Hello!")])
        self.say(text, kind, 2500)

    # ------------------------------------------------------------ actions
    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("Feed", self.feed)
        asleep = self.state in ("sleep", "nap")
        m.addAction("Wake up" if asleep else "Sleep", self.wake if asleep else self.go_sleep)
        m.addSeparator()
        w = QAction("Spinning wheel", m, checkable=True)
        w.setChecked(self.wheel.isVisible())
        w.triggered.connect(lambda on: self.set_prop_enabled("wheel", on))
        m.addAction(w)
        b = QAction("Water bottle", m, checkable=True)
        b.setChecked(self.bottle.isVisible())
        b.triggered.connect(lambda on: self.set_prop_enabled("bottle", on))
        m.addAction(b)
        m.addAction("Go run on the wheel", self.go_run)
        m.addAction("Go drink water", self.go_drink)
        m.addAction("Refill water", self.refill_water)
        m.addSeparator()
        size = m.addMenu("Size")
        for label, val in (("Tiny", 1.25), ("Small", 1.5), ("Medium", 2), ("Large", 3)):
            a = QAction(label, size, checkable=True)
            a.setChecked(abs(float(self.cfg.get("scale", 1.5)) - val) < 0.01)
            a.triggered.connect(lambda _=False, v=val: self.set_scale(v))
            size.addAction(a)
        r = QAction("Reminders on", m, checkable=True)
        r.setChecked(self.cfg.get("reminders_enabled", True))
        r.triggered.connect(self._toggle_rem)
        m.addAction(r)
        m.addSeparator()
        m.addAction("Quit", QGuiApplication.quit)
        m.exec(e.globalPos())

    def _toggle_rem(self, on):
        self.cfg["reminders_enabled"] = on
        self.cfg.save()
