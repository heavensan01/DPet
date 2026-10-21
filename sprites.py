"""Animation frames for the hamster, built from the pixel sprites in assets/grids.json
(traced from the character sheet). Qt-free: frame() returns a grid of colour keys."""
import json
from pathlib import Path

_G = json.loads((Path(__file__).parent / "assets" / "grids.json").read_text())

PAL = {"O": "#5C3010", "K": "#220F08", "G": "#F8A951", "D": "#E28C38", "C": "#FDF5E4",
       "P": "#FAA8A4", "W": "#FFFFFF", "S": "#8A8F99", "L": "#D9DCE3",
       "E": "#E8CCA8", "N": "#D69E24", "Z": "#6F8FB8", "H": "#E8506E", "Y": "#FFC83D"}
CW, CH = 50, 52          # canvas size in sprite pixels
STATES = ("walk", "idle", "eat", "sleep", "happy", "surprised")

try:                                   # colours for the wheel / bottle sprites
    _PROPS = json.loads((Path(__file__).parent / "assets" / "props.json").read_text())
    for _k, _v in _PROPS["palette"].items():
        PAL[_k] = "#%02X%02X%02X" % tuple(_v)
except Exception:
    _PROPS = None


WALK_W = len(_G["walk0"][0])


def _g(name):
    return [list(r) for r in _G[name]]


def _stamp(g, pat, r0, c0):
    for j, row in enumerate(pat):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= r0 + j < len(g) and 0 <= c0 + i < len(g[0]):
                g[r0 + j][c0 + i] = ch


# ---------------------------------------------------------------- front faces
def _front(face="open", mouth="closed"):
    g = _g("front")
    for r in range(10, 16):                       # wipe the traced eyes
        for c in list(range(9, 14)) + list(range(19, 25)):
            if g[r][c] in "KWDO":
                g[r][c] = "G"
    if face == "open":
        for c0 in (10, 20):
            _stamp(g, ["KKK", "KWK", "KKK", ".K."], 11, c0)
    elif face == "big":
        for c0 in (10, 20):
            _stamp(g, [".KK.", "KWKK", "KKKK", "KKKK", ".KK."], 10, c0)
    elif face == "closed":
        for c0 in (10, 20):
            _stamp(g, ["OOO"], 13, c0)
    elif face == "happy":
        for c0 in (10, 20):
            _stamp(g, [".O.", "O.O"], 12, c0)
    if mouth == "open":
        _stamp(g, ["OKKO", ".PP."], 18, 15)
    elif mouth == "o":
        _stamp(g, ["KK", "KK"], 18, 16)
    return g


def _stretch(s, delta, row=28):
    s = [r[:] for r in s]
    for _ in range(-delta if delta < 0 else 0):
        del s[row]
    for _ in range(delta if delta > 0 else 0):
        s.insert(row, s[row][:])
    return s


def _blit(c, spr, bottom, dx=0):
    h, w = len(spr), len(spr[0])
    x0 = (CW - w) // 2 + dx
    top = bottom - h + 1
    for j, row in enumerate(spr):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= top + j < CH and 0 <= x0 + i < CW:
                c[top + j][x0 + i] = ch


def _put(c, x, y, ch):
    if 0 <= x < CW and 0 <= y < CH:
        c[y][x] = ch


def _glyph(c, x, y, rows, ch):
    for j, row in enumerate(rows):
        for i, v in enumerate(row):
            if v != ".":
                _put(c, x + i, y + j, ch)


Z_GLYPH = ["ZZZZ", "..Z.", ".Z..", "ZZZZ"]
HEART = [".H.H.", "HHHHH", ".HHH.", "..H.."]

# eating sheet: 1 notices food, 2 sniffs, 3 picks up, 4 bites, 5 chews, 6 pauses,
# 7 licks paws, 8 done (happy).  (frame index, ticks of 30 ms)
EAT_TIMELINE = ([(0, 40), (1, 50), (2, 35)] + [(3, 14), (4, 14), (5, 10)] * 4
                + [(6, 12), (5, 8)] * 3 + [(7, 70)])
EAT_TICKS = sum(n for _, n in EAT_TIMELINE)


def _eat_index(t):
    for idx, n in EAT_TIMELINE:
        if t < n:
            return idx
        t -= n
    return 7


def _ticks(c, cx, top, t):
    if (t // 5) % 2:
        return
    for cells in ([(-9, 0), (-8, -1), (-7, -2)], [(0, -2), (0, -3), (0, -4)], [(9, 0), (8, -1), (7, -2)]):
        for dx, dy in cells:
            _put(c, cx + dx, top + dy, "Y")


# ---------------------------------------------------------------- walking
# 4-frame walk cycle traced from the walking sheet (faces right, mirrored for left)
def _walk(t, d):
    c = [["."] * CW for _ in range(CH)]
    spr = _g("walk%d" % ((t // 7) % 4))
    if d < 0:
        spr = [r[::-1] for r in spr]
    _blit(c, spr, CH - 1)
    return c


# ---------------------------------------------------------------- frames
def frame(state, t, d=1):
    if state == "walk":
        return _walk(t, d)
    c = [["."] * CW for _ in range(CH)]
    ground = CH - 1
    cx = CW // 2

    if state == "idle":
        phase = (t // 200) % 3
        if phase == 1:                            # look around (3/4 view)
            s = _g("three")
        else:
            blink = (t + 60) % 110 < 4
            s = _front("closed" if blink else "open")
        s = _stretch(s, -1 if (t // 45) % 2 else 0)
        _blit(c, s, ground)

    elif state == "eat":
        idx = _eat_index(t)
        spr = _g("eat%d" % idx)
        lift = 0
        if idx == 1:
            lift = (t // 8) % 2                  # sniff sniff
        elif idx in (3, 4):
            lift = (t // 4) % 2                  # munch munch
        _blit(c, spr, ground - lift)
        if idx == 7:                             # done! happy heart
            _glyph(c, 40, 0, HEART, "H")

    elif state == "sleep":
        s = _front("closed")
        s = _stretch(s, -3 if (t // 40) % 2 else -2)
        _blit(c, s, ground)
        k = (t // 7) % 14
        _glyph(c, 36, 14 - k, Z_GLYPH, "Z")
        _glyph(c, 40, 14 - (k + 7) % 14, Z_GLYPH, "Z")

    elif state == "happy":
        bob = (t // 6) % 2
        s = _front("happy", "open")
        _blit(c, s, ground - (2 if bob else 0))
        _ticks(c, cx, ground - 37 - (2 if bob else 0), t)

    else:                                         # surprised (jumping / dragged)
        s = _stretch(_front("big", "o"), 2)
        _blit(c, s, ground)
        _ticks(c, cx, ground - 39, t)
    return c


def prop_frame(grid, mirror=False):
    """Canvas with an interaction sprite (hamster at the wheel / bottle) bottom-centred."""
    c = [["."] * CW for _ in range(CH)]
    spr = [list(r) for r in grid]
    if mirror:
        spr = [r[::-1] for r in spr]
    _blit(c, spr, CH - 1)
    return c


def prop_canvas_x0(w):
    return (CW - w) // 2
