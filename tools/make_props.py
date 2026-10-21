"""Build the wheel / bottle sprites and the hamster-with-prop sequences from the 4 sheets.
Usage: python tools/make_props.py climb.png wheel.png bottle.png drink.png exit.png
Writes assets/props.json.  Requires pillow, numpy, scipy."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from make_sprites import PAL as _HP, cleanup  # noqa: E402
from make_walk import add_outline  # noqa: E402

HAM = dict(_HP)
HAM["E"] = (232, 204, 168)
HAM_W = {"O": 1.5, "K": 1.8, "G": 1.0, "D": 1.0, "C": 1.0, "P": 1.15, "W": 1.2, "E": 1.0}
HKEYS = list(HAM)
HARR = np.array([HAM[k] for k in HKEYS], float)

PROP = {  # blue wheel / bottle palette (from the sheets)
    "a": (5, 27, 125), "b": (10, 73, 186), "c": (21, 122, 235), "d": (66, 161, 249),
    "e": (132, 192, 246), "f": (196, 224, 245),
    "h": (119, 207, 252), "j": (86, 187, 252), "i": (41, 146, 245),
    "z": (14, 14, 24), "x": (116, 113, 118), "y": (188, 185, 180), "v": (64, 50, 57),
}
PKEYS = list(PROP)
PARR = np.array([PROP[k] for k in PKEYS], float)


def load(path):
    return np.array(Image.open(path).convert("RGB")).astype(float)


# ---------------------------------------------------------------- generic sampling
def sample(a, fg, x0, y0, cell, i0, j0, i1, j1, arr, keys, weights=None, force_near_black=False):
    """Grid of palette keys for lattice cells [i0,i1) x [j0,j1) (origin x0,y0, size cell)."""
    d = ((a[:, :, None, :] - arr[None, None, :, :]) ** 2).sum(3)
    cls = d.argmin(2)
    H, W = fg.shape
    g = [["."] * (i1 - i0) for _ in range(j1 - j0)]
    for j in range(j0, j1):
        for i in range(i0, i1):
            xa, xb = int(round(x0 + i * cell)), int(round(x0 + (i + 1) * cell))
            ya, yb = int(round(y0 + j * cell)), int(round(y0 + (j + 1) * cell))
            xa, xb, ya, yb = max(xa, 0), min(max(xb, xa + 1), W), max(ya, 0), min(max(yb, ya + 1), H)
            if xa >= xb or ya >= yb:
                continue
            m = fg[ya:yb, xa:xb]
            if m.mean() < 0.5:
                continue
            blk = cls[ya:yb, xa:xb][m]
            score = {}
            for k_i, k in enumerate(keys):
                w = (weights or {}).get(k, 1.0)
                score[k] = (blk == k_i).sum() * w
            g[j - j0][i - i0] = max(score, key=score.get)
    return g


def trim(g):
    ys = [y for y, r in enumerate(g) if any(c != "." for c in r)]
    xs = [x for r in g for x, c in enumerate(r) if c != "."]
    if not ys:
        return g, 0, 0
    return [r[min(xs):max(xs) + 1] for r in g[min(ys):max(ys) + 1]], min(xs), min(ys)


# ---------------------------------------------------------------- hamster masks
def ham_mask(a, near=26):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = ((R - B) > 12) & ((R + G + B) > 60)
    m = ndi.binary_closing(m, iterations=2)
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    big = int(np.argmax(sizes)) + 1
    bigmask = lab == big
    zone = ndi.binary_dilation(bigmask, iterations=near)
    keep = bigmask.copy()
    for i in range(1, n + 1):
        if i != big and sizes[i - 1] >= 30 and (zone & (lab == i)).any():
            keep |= lab == i
    return keep


def ham_grid(a, fg, x0, y0, cell):
    ys, xs = np.where(fg)
    i0 = int(np.floor((xs.min() - x0) / cell)) - 1
    i1 = int(np.ceil((xs.max() + 1 - x0) / cell)) + 1
    j0 = int(np.floor((ys.min() - y0) / cell)) - 1
    j1 = int(np.ceil((ys.max() + 1 - y0) / cell)) + 1
    g = sample(a, fg, x0, y0, cell, i0, j0=j0, i1=i1, j1=j1, arr=HARR, keys=HKEYS, weights=HAM_W)
    # fur shading: dark edge pixels are fur, eyes stay black
    for r in g:
        for c in range(len(r)):
            if r[c] == "O":
                r[c] = "D"
    near_black = a.sum(2) < 105
    for j in range(j0, j1):
        for i in range(i0, i1):
            xa, xb = int(round(x0 + i * cell)), int(round(x0 + (i + 1) * cell))
            ya, yb = int(round(y0 + j * cell)), int(round(y0 + (j + 1) * cell))
            xa, ya = max(xa, 0), max(ya, 0)
            if xb > xa and yb > ya and g[j - j0][i - i0] != "." and \
                    (near_black[ya:yb, xa:xb] & fg[ya:yb, xa:xb]).mean() >= 0.16:
                g[j - j0][i - i0] = "K"
    g = add_outline(g)           # adds a 1-cell border all round
    g = cleanup(g)
    g, tx, ty = trim(g)
    # add_outline padded by one cell; trimmed grid starts at (i0-1+tx, j0-1+ty)
    return g, i0 - 1 + tx, j0 - 1 + ty


def droplets(a, bottle_comp_ids, lab_all, region):
    pass


# ---------------------------------------------------------------- wheel
def find_hub(img):
    """Hub centre = the point about which the wheel looks the same after a 45 degree turn."""
    arr = np.array(img).astype(float)
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    best = None
    for cy in range(int(h * 0.40), int(h * 0.50)):
        for cx in range(int(w * 0.46), int(w * 0.54)):
            disk = ((xx - cx) ** 2 + (yy - cy) ** 2) <= (0.30 * w) ** 2
            rot = np.array(img.rotate(45, resample=Image.BILINEAR, center=(cx, cy),
                                      fillcolor=(255, 255, 255))).astype(float)
            err = np.abs(rot - arr)[disk].mean()
            if best is None or err < best[0]:
                best = (err, cx, cy)
    print("wheel hub", best[1], best[2], "of", w, h)
    return (best[1], best[2])


def wheel_boxes_sheet2(a):
    nonwhite = a.min(2) < 225
    lab, n = ndi.label(ndi.binary_dilation(nonwhite, iterations=3))
    res = []
    for sl in ndi.find_objects(lab):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if h * w > 20000 and h < 300:
            res.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    res.sort(key=lambda r: (r[1] // 200, r[0]))
    return res


def climb_wheels(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    blue = (B > R + 60) & (B > 120)
    lab, n = ndi.label(ndi.binary_dilation(blue, iterations=2))
    res = []
    for sl in ndi.find_objects(lab):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if h > 110 and w > 100:
            res.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    res.sort(key=lambda r: (r[1] // 230, r[0]))
    return res


def build_wheel(climb, wheel_sheet):
    wb = climb_wheels(climb)
    assert len(wb) == 20, len(wb)
    # hamster length from the first (approach) frame -> lattice cell size
    x0, y0, x1, y1 = wb[0]
    reg = climb[y0 - 10:y1 + 20, max(x0 - 200, 0):x0 - 5]
    m = ham_mask(reg)
    ys, xs = np.where(m)
    ham_len = xs.max() - xs.min()
    cell = ham_len / 42.0
    print("wheel: hamster length px", ham_len, "cell", round(cell, 2))
    ref_w = float(np.median([b[2] - b[0] for b in wb[:10]]))
    ref_h = float(np.median([b[3] - b[1] for b in wb[:10]]))
    PW, PH = int(round(ref_w / cell)), int(round(ref_h / cell))
    # --- spinning wheel: take the clean frame 1 and rotate only the spokes + hub.
    #     Spokes repeat every 45 degrees, so 12 frames cover one full period (3.75 deg each).
    boxes2 = [b for b in wheel_boxes_sheet2(wheel_sheet) if b[3] - b[1] > 150]
    assert len(boxes2) == 12, len(boxes2)
    bx0, by0, bx1, by1 = boxes2[0]
    base = Image.fromarray(wheel_sheet[by0:by1, bx0:bx1].astype(np.uint8))
    bw, bh = base.size
    hub = find_hub(base)
    r_in = 0.355 * bw
    yy, xx = np.mgrid[0:bh, 0:bw]
    disk = ((xx - hub[0]) ** 2 + (yy - hub[1]) ** 2) <= r_in ** 2
    base_arr = np.array(base)
    frames = []
    NF = 12
    for k in range(NF):
        ang = -k * (45.0 / NF)                     # clockwise
        rot_img = base.rotate(ang, resample=Image.BICUBIC, center=hub, fillcolor=(255, 255, 255))
        rot = np.array(rot_img.filter(ImageFilter.MinFilter(3)))     # keep the spokes bold
        comp = base_arr.copy()
        comp[disk] = rot[disk]
        crop = Image.fromarray(comp).resize((int(PW * cell), int(PH * cell)), Image.LANCZOS)
        arr = np.array(crop).astype(float)
        fgm = arr.min(2) < 228
        g = sample(arr, fgm, 0, 0, cell, 0, 0, PW, PH, PARR, PKEYS)
        frames.append(["".join(r) for r in g])
    # --- hamster frames
    seq = []
    for k, (x0, y0, x1, y1) in enumerate(wb):
        cx = (x0 + x1) / 2.0
        lat_x0 = cx - PW * cell / 2.0
        lat_y0 = y1 - PH * cell
        left_margin = 200 if k < 3 else 28
        rx0, rx1 = int(max(x0 - left_margin, 0)), int(min(x1 + 28, climb.shape[1]))
        ry0, ry1 = int(y0 - 12), int(y1 + 14)
        reg = climb[ry0:ry1, rx0:rx1]
        fg = ham_mask(reg)
        g, oi, oj = ham_grid(reg, fg, lat_x0 - rx0, lat_y0 - ry0, cell)
        seq.append({"grid": ["".join(r) for r in g], "ox": oi, "oy": oj})
    return {"w": PW, "h": PH, "cell": cell, "frames": frames, "seq": seq}


# ---------------------------------------------------------------- bottle
def bottle_comp(a, region, light_bg=False):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    blue = (B > R + 40) & (B > 120)
    gray = (np.abs(R - G) < 25) & (np.abs(G - B) < 35) & (R > 70) & (R < 225)
    m = blue | gray
    return m


def build_bottle(drink, bottle_sheet):
    R, G, B = drink[:, :, 0], drink[:, :, 1], drink[:, :, 2]
    blue = (B > R + 40) & (B > 120)
    lab, n = ndi.label(ndi.binary_dilation(blue, iterations=2))
    comps = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if h > 70 and w > 50 and h > w:
            comps.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, i + 1))
    comps.sort(key=lambda r: (r[1] // 320, r[0]))
    assert len(comps) == 15, len(comps)
    gray = (np.abs(R - G) < 25) & (np.abs(G - B) < 35) & (R > 70) & (R < 225)
    # union bbox of body + spout per frame
    boxes = []
    for (x0, y0, x1, y1, _) in comps:
        reg = np.zeros_like(blue)
        reg[y0 - 6:y1 + 70, x0 - 60:x1 + 10] = True
        m = (blue | gray) & reg
        ys, xs = np.where(m)
        boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    # hamster length from frame 1
    x0, y0, x1, y1, _ = comps[0]
    reg = drink[y0 + 20:y0 + 200, 0:x0 - 15]
    m = ham_mask(reg)
    ys, xs = np.where(m)
    ham_len = xs.max() - xs.min()
    cell = ham_len / 42.0
    print("bottle: hamster length px", ham_len, "cell", round(cell, 2))
    ref_w = float(np.median([b[2] - b[0] for b in boxes[4:13]]))
    ref_h = float(np.median([b[3] - b[1] for b in boxes[4:13]]))
    BW, BH = int(round(ref_w / cell)), int(round(ref_h / cell))
    # --- bottle level frames from sheet 3
    bg = bottle_sheet[5, 5]
    nonbg = np.abs(bottle_sheet - bg).sum(2) > 60
    lab3, n3 = ndi.label(ndi.binary_dilation(nonbg, iterations=4))
    boxes3 = []
    for sl in ndi.find_objects(lab3):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if 15000 < h * w < 80000 and h > 150:
            boxes3.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    boxes3.sort(key=lambda r: (r[1] // 250, r[0]))
    assert len(boxes3) == 12, len(boxes3)
    levels = []
    for (bx0, by0, bx1, by1) in boxes3:
        # the "0.25s" label pill sits just below the bottle: cut it off
        occ = (np.abs(bottle_sheet[by0:by1, bx0:bx1] - bg).sum(2) > 60).any(axis=1)
        runs, start = [], None
        for yy, v in enumerate(occ):
            if v and start is None:
                start = yy
            if not v and start is not None:
                runs.append((start, yy))
                start = None
        if start is not None:
            runs.append((start, len(occ)))
        if len(runs) >= 2:
            by1 = by0 + runs[-2][1]
        by0 = by0 + runs[0][0]
        crop = bottle_sheet[by0:by1, bx0:bx1]
        out_mask = np.abs(crop - bg).sum(2) < 40
        lab_o, _ = ndi.label(out_mask)
        border = set(np.unique(np.concatenate([lab_o[0], lab_o[-1], lab_o[:, 0], lab_o[:, -1]])))
        border.discard(0)
        outside = np.isin(lab_o, list(border))
        fgm = ~outside
        img = Image.fromarray(crop.astype(np.uint8)).resize((int(BW * cell), int(BH * cell)), Image.LANCZOS)
        arr = np.array(img).astype(float)
        fm = np.array(Image.fromarray((fgm * 255).astype(np.uint8)).resize(
            (int(BW * cell), int(BH * cell)), Image.BILINEAR)) > 127
        g = sample(arr, fm, 0, 0, cell, 0, 0, BW, BH, PARR, PKEYS)
        levels.append(["".join(r) for r in g])
    # --- hamster frames; ground = median bottom (cells below bottle top) over frames 6..14
    raw = []
    for k, ((x0, y0, x1, y1, _), (ux0, uy0, ux1, uy1)) in enumerate(zip(comps, boxes)):
        rx0, rx1 = int(max(ux0 - 235, 0)), int(min(ux1 + 30, drink.shape[1]))
        ry0, ry1 = int(uy0 - 8), int(uy0 + 232)
        reg = drink[ry0:ry1, rx0:rx1]
        fg = ham_mask(reg)
        # droplets: cyan specks near the spout
        Rr, Gr, Br = reg[:, :, 0], reg[:, :, 1], reg[:, :, 2]
        cy = (Br > Rr + 60) & (Gr > 140)
        labc, nc = ndi.label(ndi.binary_dilation(cy, iterations=1))
        drop = np.zeros_like(cy)
        for i in range(1, nc + 1):
            comp = labc == i
            if comp.sum() < 160:
                drop |= comp & cy
        g, oi, oj = ham_grid(reg, fg, ux0 - rx0, uy0 - ry0, cell)
        # merge droplets
        if drop.any():
            ys, xs = np.where(drop)
            for yy, xx in zip(ys, xs):
                ci = int((xx - (ux0 - rx0)) // cell) - oi
                cj = int((yy - (uy0 - ry0)) // cell) - oj
                if 0 <= cj < len(g) and 0 <= ci < len(g[0]) and g[cj][ci] == ".":
                    g[cj][ci] = "j"
        raw.append((g, oi, oj))
    G_row = int(np.median([raw[k][2] + len(raw[k][0]) for k in range(4, 13)]))
    seq = []
    for g, oi, oj in raw:
        seq.append({"grid": ["".join(r) for r in g], "ox": oi, "oy": G_row - len(g)})
    return {"w": BW, "h": BH, "ground": G_row, "cell": cell, "levels": levels, "seq": seq}


def build_exit(exit_img, PW, PH):
    """Hamster stepping out of the wheel (5 frames), same lattice as the climb frames."""
    R, G, B = exit_img[:, :, 0], exit_img[:, :, 1], exit_img[:, :, 2]
    blue = (B > R + 60) & (B > 120)
    lab, n = ndi.label(ndi.binary_dilation(blue, iterations=2))
    boxes = []
    for sl in ndi.find_objects(lab):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if h > 150 and w > 150:
            boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    boxes.sort(key=lambda b: b[0])
    assert len(boxes) == 5, len(boxes)
    x0, y0, x1, y1 = boxes[4]
    reg = exit_img[y0 - 10:y1 + 20, x0 + 110:x1 + 180]
    m = ham_mask(reg)
    ys, xs = np.where(m)
    ham_len = xs.max() - xs.min()
    cell = ham_len / 42.0
    print("exit: hamster length px", ham_len, "cell", round(cell, 2))
    out = []
    for k, (x0, y0, x1, y1) in enumerate(boxes):
        cx = (x0 + x1) / 2.0
        lat_x0 = cx - PW * cell / 2.0
        lat_y0 = y1 - PH * cell
        rx0 = int(max(x0 - 20, 0))
        rx1 = int(min(x1 + (20 if k < 2 else 175), exit_img.shape[1]))
        ry0, ry1 = int(y0 - 12), int(y1 + 16)
        reg = exit_img[ry0:ry1, rx0:rx1]
        fg = ham_mask(reg)
        g, oi, oj = ham_grid(reg, fg, lat_x0 - rx0, lat_y0 - ry0, cell)
        if k >= 2:                                   # outside the wheel: feet on the floor
            oj = PH - len(g)
        out.append({"grid": ["".join(r) for r in g], "ox": oi, "oy": oj})
    return out


def settle_feet(wheel):
    """Make the hamster stand ON TOP of the wheel's bottom ring (legs above the ring, never sunk
    into it).  The ring's floor profile = pixels solid in every spin frame (spokes move, ring doesn't).
    Each in-wheel hamster frame is moved vertically until its lowest foot just touches that floor."""
    frames = wheel["frames"]
    ring = np.array([[[c != "." for c in r] for r in f] for f in frames]).all(0)
    edge = {}
    for x in range(wheel["w"]):
        for y in range(44, 62):
            if ring[y:y + 3, x].all():
                edge[x] = y
                break
    def lift(fr):
        best = None
        for j, row in enumerate(fr["grid"]):
            for i, ch in enumerate(row):
                x, y = fr["ox"] + i, fr["oy"] + j
                if ch == "." or y < 48 or not (18 <= x <= 52) or x not in edge:
                    continue
                m = edge[x] - 1 - y
                best = m if best is None else min(best, m)
        if best is not None:
            fr["oy"] += best
    for k in range(7, len(wheel["seq"])):          # inside the wheel: standing / running
        lift(wheel["seq"][k])
    for k in (0, 1):                               # exit frames still inside the wheel
        lift(wheel["exit"][k])
    return wheel


if __name__ == "__main__":
    climb, wheel, bottle, drink, exit_sheet = [load(p) for p in sys.argv[1:6]]
    wheel_data = build_wheel(climb, wheel)
    wheel_data["exit"] = build_exit(exit_sheet, wheel_data["w"], wheel_data["h"])
    settle_feet(wheel_data)
    out = {"palette": PROP, "wheel": wheel_data, "bottle": build_bottle(drink, bottle)}
    path = Path(__file__).resolve().parent.parent / "assets" / "props.json"
    path.write_text(json.dumps(out))
    print("wheel", out["wheel"]["w"], "x", out["wheel"]["h"],
          "| bottle", out["bottle"]["w"], "x", out["bottle"]["h"], "ground", out["bottle"]["ground"])
