"""Build pixel sprites from the character sheet (run once; output goes to assets/).
Usage: python tools/make_sprites.py path/to/Hamster_Pixel-Art_Character_Sheet.png
Requires: pillow, numpy, scipy"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

CELL = 7.5   # source pixels per sprite pixel
BG = np.array([253, 247, 234])
PAL = {
    "O": (92, 48, 16),     # outline
    "K": (34, 16, 8),      # eye black
    "G": (248, 169, 81),   # ginger
    "D": (226, 140, 56),   # darker ginger
    "C": (253, 245, 228),  # cream
    "P": (250, 168, 164),  # pink
    "W": (255, 255, 255),  # highlight
}
WEIGHT = {"O": 1.5, "K": 1.8, "G": 1.0, "D": 1.0, "C": 1.0, "P": 1.4, "W": 1.2}
KEYS = list(PAL)
PARR = np.array([PAL[k] for k in KEYS], float)

BOXES = {  # name: (x0, y0, x1, y1) in the sheet
    "front": (37, 115, 293, 404), "back": (338, 118, 597, 406),
    "left": (637, 122, 900, 408), "right": (947, 122, 1210, 409),
    "three": (785, 495, 1092, 785),
}


def grid_from_crop(im, box):
    x0, y0, x1, y1 = box
    a = np.array(im.crop(box).convert("RGB")).astype(float)
    h, w, _ = a.shape
    diff = np.abs(a - BG).sum(2)
    bgish = diff < 28
    lab, _ = ndi.label(bgish)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    border.discard(0)
    outside = np.isin(lab, list(border))
    # soft shadow under the feet is "bg-like but not quite": drop pale greyish pixels too
    shadow = (~outside) & (diff < 70) & (a[:, :, 2] < a[:, :, 0] - 12) & (a[:, :, 0] > 215) \
        & (a[:, :, 1] > 205)
    # only count shadow if connected to outside region
    lab2, _ = ndi.label(shadow | outside)
    bl = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]]))); bl.discard(0)
    outside = np.isin(lab2, list(bl))
    # class per pixel
    d = ((a[:, :, None, :] - PARR[None, None, :, :]) ** 2).sum(3)
    cls = d.argmin(2)
    ys, xs = np.where(~outside)
    ty0, ty1, tx0, tx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rows = int(np.ceil((ty1 - ty0) / CELL)); cols = int(np.ceil((tx1 - tx0) / CELL))
    g = [["."] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            ya, yb = int(ty0 + r * CELL), int(ty0 + (r + 1) * CELL)
            xa, xb = int(tx0 + c * CELL), int(tx0 + (c + 1) * CELL)
            blk_out = outside[ya:yb, xa:xb]
            if blk_out.size == 0 or blk_out.mean() > 0.5:
                continue
            blk = cls[ya:yb, xa:xb][~blk_out]
            score = {k: (blk == i).sum() * WEIGHT[k] for i, k in enumerate(KEYS)}
            k = max(score, key=score.get)
            n = len(blk)
            # keep eye highlights alive
            if (blk == KEYS.index("W")).sum() >= 0.1 * n and (blk == KEYS.index("K")).sum() >= 0.2 * n:
                k = "W"
            g[r][c] = k
    return g


def cleanup(g):
    h, w = len(g), len(g[0])
    def at(y, x):
        return g[y][x] if 0 <= y < h and 0 <= x < w else "."
    N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
    N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
    # 1) stray pink / white specks inside fur become the surrounding colour
    for _ in range(2):
        new = [r[:] for r in g]
        for y in range(h):
            for x in range(w):
                k = g[y][x]
                if k in "P":
                    same = sum(at(y + dy, x + dx) == k for dy, dx in N8)
                    if same < 2:
                        nb = [at(y + dy, x + dx) for dy, dx in N8 if at(y + dy, x + dx) not in ".OKPW"]
                        if nb:
                            new[y][x] = max(set(nb), key=nb.count)
        g = new
    # 2) silhouette edge is always outline
    new = [r[:] for r in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] not in ".OP" and any(at(y + dy, x + dx) == "." for dy, dx in N4):
                new[y][x] = "O"
    g = new
    # 3) lonely transparent holes inside the body
    for y in range(h):
        for x in range(w):
            if g[y][x] == "." and all(at(y + dy, x + dx) != "." for dy, dx in N4):
                nb = [at(y + dy, x + dx) for dy, dx in N4]
                g[y][x] = max(set(nb), key=nb.count)
    return g


def save_png(g, path):
    h, w = len(g), len(g[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            k = g[y][x]
            if k != ".":
                img.putpixel((x, y), PAL[k] + (255,))
    img.save(path)


if __name__ == "__main__":
    src = sys.argv[1]
    im = Image.open(src)
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    grids = {}
    for name, box in BOXES.items():
        grids[name] = cleanup(grid_from_crop(im, box))
        save_png(grids[name], out / f"{name}.png")
        print(name, len(grids[name][0]), "x", len(grids[name]))
    json.dump({k: ["".join(r) for r in v] for k, v in grids.items()},
              open(out / "grids.json", "w"))
