"""Turn the 8-frame eating sheet into pixel frames (assets/grids.json: eat0..eat7).
Usage: python tools/make_eat.py path/to/eating_sheet.png"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from make_sprites import PAL as _PAL, WEIGHT as _W, cleanup  # noqa: E402
from make_walk import add_outline  # noqa: E402

PAL = dict(_PAL)
PAL["E"] = (232, 204, 168)
PAL["Y"] = (250, 204, 70)      # food
PAL["N"] = (214, 158, 36)      # food shade
WEIGHT = dict(_W)
WEIGHT.update({"E": 1.0, "Y": 1.3, "N": 1.2, "P": 1.15})
KEYS = list(PAL)
PARR = np.array([PAL[k] for k in KEYS], float)
BG = np.array([253, 248, 236])
CELL = 8.6
# rough regions of the 8 frames: (x0, y0, x1, y1)
ROUGH = [(20, 110, 360, 470), (380, 110, 740, 470), (780, 110, 1120, 470), (1140, 110, 1450, 470),
         (10, 555, 360, 915), (400, 555, 740, 915), (770, 555, 1100, 915), (1150, 555, 1470, 915)]


def strong_mask(a):
    diff = np.abs(a - BG).sum(2)
    sat = a.max(2) - a.min(2)
    return (diff > 70) | (sat > 52)


def hamster_mask(a):
    m = strong_mask(a)
    m = ndi.binary_closing(m, iterations=4)
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_opening(m, iterations=2)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.zeros_like(m)
    big = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == big)
    bx0, bx1, by1 = xs.min(), xs.max(), ys.max()
    for i in range(1, n + 1):
        if i == big:
            keep |= lab == i
        elif sizes[i - 1] > 700:                      # food on the ground
            yy, xx = np.where(lab == i)
            if bx0 - 40 < xx.mean() < bx1 + 40 and yy.mean() > by1 - 120:
                keep |= lab == i
    ys, xs = np.where(keep)
    return keep, (xs.min() + xs.max()) // 2, ys.max()


def to_grid(a, fg):
    d = ((a[:, :, None, :] - PARR[None, None, :, :]) ** 2).sum(3)
    cls = d.argmin(2)
    near_black = a.sum(2) < 105
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
            if k == "O":
                k = "D"
            if near_black[ya:yb, xa:xb].mean() >= 0.16:
                k = "K"                           # keep the round black eyes
            if (blk == KEYS.index("W")).sum() >= 0.1 * len(blk) and \
                    (blk == KEYS.index("K")).sum() >= 0.2 * len(blk):
                k = "W"
            g[r][c] = k
    return g


if __name__ == "__main__":
    full = np.array(Image.open(sys.argv[1]).convert("RGB")).astype(float)
    PADV = 260
    full = np.pad(full, ((PADV, PADV), (PADV, PADV), (0, 0)), mode="edge")
    H, W = 350, 380
    grids = []
    for (x0, y0, x1, y1) in ROUGH:
        x0, y0, x1, y1 = x0 + PADV, y0 + PADV, x1 + PADV, y1 + PADV
        sub = full[y0:y1, x0:x1]
        _, cx, bottom = hamster_mask(sub)
        cx += x0
        bottom += y0
        bx0, by0 = cx - W // 2, bottom - H + 8
        crop = full[by0:by0 + H, bx0:bx0 + W]
        fg, _, _ = hamster_mask(crop)
        grids.append(cleanup(add_outline(to_grid(crop, fg))))
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
        data[f"eat{i}"] = ["".join(r) for r in g]
    path.write_text(json.dumps(data))
    print("frames", len(out[0][0]), "x", len(out[0]))
