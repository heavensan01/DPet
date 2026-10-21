"""Turn the 4-frame walking sheet into pixel frames (assets/grids.json: walk0..walk3).
Usage: python tools/make_walk.py path/to/walk_sheet.png"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from make_sprites import PAL as _PAL, WEIGHT as _W, cleanup  # noqa: E402

PAL = dict(_PAL)
PAL["E"] = (232, 204, 168)          # shaded cream (belly underside)
WEIGHT = dict(_W)
WEIGHT["E"] = 1.0
WEIGHT["P"] = 1.15
KEYS = list(PAL)
PARR = np.array([PAL[k] for k in KEYS], float)

CELL = 7.2
EYE_GUESS = [(308, 458), (682, 458), (1057, 460), (1425, 460)]
BOX = (-280, -130, 85, 190)          # relative to the eye: left, up, right, down


def eye_anchor(a, guess):
    gx, gy = guess
    dark = a.sum(2) < 60
    lab, _ = ndi.label(dark)
    ids = np.unique(lab[gy - 18:gy + 18, gx - 18:gx + 18])
    ids = [i for i in ids if i]
    best = max(ids, key=lambda i: (lab == i).sum())
    ys, xs = np.where(lab == best)
    return int(xs.mean()), int(ys.mean())


def frame_grid(a, anchor):
    ax, ay = anchor
    x0, y0 = ax + BOX[0], ay + BOX[1]
    x1, y1 = ax + BOX[2], ay + BOX[3]
    crop = a[y0:y1, x0:x1]
    fg = crop.sum(2) > 95                     # black background and dark shadow are dropped
    fg = ndi.binary_opening(fg, iterations=1)
    lab, n = ndi.label(fg)
    if n > 1:                                 # keep the biggest blob (the hamster)
        sizes = ndi.sum(fg, lab, range(1, n + 1))
        fg = lab == (1 + int(np.argmax(sizes)))
    fg = ndi.binary_fill_holes(fg)
    d = ((crop[:, :, None, :] - PARR[None, None, :, :]) ** 2).sum(3)
    cls = d.argmin(2)
    h, w = fg.shape
    rows, cols = int(np.ceil(h / CELL)), int(np.ceil(w / CELL))
    g = [["."] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            ya, yb = int(r * CELL), int((r + 1) * CELL)
            xa, xb = int(c * CELL), int((c + 1) * CELL)
            m = fg[ya:yb, xa:xb]
            if m.size == 0 or m.mean() < 0.5:
                continue
            blk = cls[ya:yb, xa:xb][m]
            score = {k: (blk == i).sum() * WEIGHT[k] for i, k in enumerate(KEYS)}
            k = max(score, key=score.get)
            if k == "O":                      # sheet has no outline: dark edge = fur shadow
                k = "D"
            if (blk == KEYS.index("W")).sum() >= 0.1 * len(blk) and \
                    (blk == KEYS.index("K")).sum() >= 0.2 * len(blk):
                k = "W"
            g[r][c] = k
    return g


def add_outline(g):
    h, w = len(g), len(g[0])
    pad = [["."] * (w + 2) for _ in range(h + 2)]
    for y in range(h):
        for x in range(w):
            pad[y + 1][x + 1] = g[y][x]
    out = [r[:] for r in pad]
    for y in range(h + 2):
        for x in range(w + 2):
            if pad[y][x] == ".":
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h + 2 and 0 <= nx < w + 2 and pad[ny][nx] not in ".":
                        out[y][x] = "O"
                        break
    return out


if __name__ == "__main__":
    a = np.array(Image.open(sys.argv[1]).convert("RGB")).astype(float)
    grids = []
    for guess in EYE_GUESS:
        anc = eye_anchor(a, guess)
        grids.append(cleanup(add_outline(frame_grid(a, anc))))
    # common bounding box so frames keep their relative positions
    H = max(len(g) for g in grids)
    W = max(len(g[0]) for g in grids)
    boxes = []
    for g in grids:
        ys = [y for y, r in enumerate(g) if any(ch != "." for ch in r)]
        xs = [x for r in g for x, ch in enumerate(r) if ch != "."]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    out = [[r[x0:x1 + 1] for r in g[y0:y1 + 1]] for g in grids]
    path = Path(__file__).resolve().parent.parent / "assets" / "grids.json"
    data = json.loads(path.read_text())
    for i, g in enumerate(out):
        data[f"walk{i}"] = ["".join(r) for r in g]
    path.write_text(json.dumps(data))
    print("frames", len(out[0][0]), "x", len(out[0]))
