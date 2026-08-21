#!/usr/bin/env python3
"""Pre-render the key artwork as PNGs and emit them as a TypeScript module.

    python3 scripts/render-tiles.py

# Why PNG, and why at build time

Stream Deck's setImage takes "a base64 encoded string with the mime type
declared, or an SVG string". On this deck the SVG forms do not work: raw markup,
base64 SVG and a charset=utf8 data URI were all accepted without error and none
ever appeared, leaving the manifest's default image on the key -- which is why
the tiles showed a green dot for so long and looked like the plugin was doing
nothing. Base64 PNG works, so that is what we ship.

Rendering happens here rather than in the plugin because Node has no image
library and the alternative is a hand-rolled PNG encoder. The artwork is a fixed
set: a bar per status colour, a gauge at 5% steps, and the product marks. The
changing part -- the label and the value -- is the key's title, which Stream Deck
draws itself and which has always worked.
"""
import base64
import io
import json
import math
import os
import re

from PIL import Image, ImageDraw

SIZE = 144
SS = 4  # supersample, then downscale: PIL has no anti-aliasing on arcs

# Phew Blue tokens (brand/tokens/colors.json).
AQUA = "#1de9b6"
GOLD = "#ffd166"
CORAL = "#ff6e6e"
SKY = "#40c4ff"
GREY = "#8c929a"
BG = "#16181b"
TRACK = "#393e46"

ACCENTS = {"aqua": AQUA, "gold": GOLD, "coral": CORAL, "sky": SKY, "grey": GREY}
GAUGE_ACCENTS = ("aqua", "gold", "coral", "grey")
GAUGE_STEPS = 21          # 0, 5, 10 ... 100 percent
GAUGE_START, GAUGE_SWEEP = 135, 270


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def canvas():
    im = Image.new("RGB", (SIZE * SS, SIZE * SS), rgb(BG))
    return im, ImageDraw.Draw(im)


def finish(im):
    im = im.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def bar(accent):
    """A band of the status colour across the top; the rest is the value's."""
    im, d = canvas()
    d.rectangle([0, 0, SIZE * SS, 12 * SS], fill=rgb(accent))
    return finish(im)


def gauge(accent, fraction):
    """A dial, for readings that genuinely run 0-100."""
    im, d = canvas()
    pad, width = 14 * SS, 12 * SS
    box = [pad, pad, SIZE * SS - pad, SIZE * SS - pad]
    d.arc(box, GAUGE_START, GAUGE_START + GAUGE_SWEEP, fill=rgb(TRACK), width=width)
    if fraction > 0:
        d.arc(box, GAUGE_START, GAUGE_START + GAUGE_SWEEP * fraction,
              fill=rgb(accent), width=width)
    return finish(im)


# --- product marks -----------------------------------------------------------
# Simple Icons paths (CC0), lifted from the badges this cluster's own kromgo
# renders. Each is a 24x24 path; only M/L/H/V/C/Q/A/Z are handled, which is all
# these use, and curves are flattened because PIL draws polygons.
def parse_path(d):
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    polys, cur = [], []
    i = 0
    x = y = sx = sy = 0.0
    cmd = None
    px = py = 0.0

    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v

    def bez(p0, p1, p2, p3, n=14):
        for k in range(1, n + 1):
            t = k / n
            mt = 1 - t
            bx = (mt**3 * p0[0] + 3 * mt * mt * t * p1[0]
                  + 3 * mt * t * t * p2[0] + t**3 * p3[0])
            by = (mt**3 * p0[1] + 3 * mt * mt * t * p1[1]
                  + 3 * mt * t * t * p2[1] + t**3 * p3[1])
            cur.append((bx, by))

    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            if cur: polys.append(cur); cur = []
            nx, ny = num(), num()
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            sx, sy = x, y
            cur.append((x, y))
            cmd = "l" if rel else "L"
        elif c == "L":
            nx, ny = num(), num()
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            cur.append((x, y))
        elif c == "H":
            nx = num(); x = x + nx if rel else nx; cur.append((x, y))
        elif c == "V":
            ny = num(); y = y + ny if rel else ny; cur.append((x, y))
        elif c in "CS":
            if c == "C":
                x1, y1, x2, y2, nx, ny = (num() for _ in range(6))
                if rel: x1, y1, x2, y2, nx, ny = x + x1, y + y1, x + x2, y + y2, x + nx, y + ny
            else:
                x2, y2, nx, ny = (num() for _ in range(4))
                if rel: x2, y2, nx, ny = x + x2, y + y2, x + nx, y + ny
                x1, y1 = 2 * x - px, 2 * y - py
            bez((x, y), (x1, y1), (x2, y2), (nx, ny))
            px, py = x2, y2
            x, y = nx, ny
        elif c in "QT":
            if c == "Q":
                x1, y1, nx, ny = (num() for _ in range(4))
                if rel: x1, y1, nx, ny = x + x1, y + y1, x + nx, y + ny
            else:
                nx, ny = num(), num()
                if rel: nx, ny = x + nx, y + ny
                x1, y1 = 2 * x - px, 2 * y - py
            bez((x, y), (x1, y1), (x1, y1), (nx, ny))
            px, py = x1, y1
            x, y = nx, ny
        elif c == "A":
            # Arc: flatten crudely to its endpoint. The marks use arcs only for
            # small rounded details, where a straight segment is invisible at
            # 144px.
            for _ in range(5): num()
            nx, ny = num(), num()
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            cur.append((x, y))
        elif c == "Z":
            if cur: cur.append((sx, sy)); polys.append(cur); cur = []
            x, y = sx, sy
    if cur: polys.append(cur)
    return polys


def logo(path_d, accent, scale=0.62):
    im, d = canvas()
    n = SIZE * SS
    span = n * scale
    off_x = (n - span) / 2
    off_y = (n - span) / 2
    k = span / 24.0
    for poly in parse_path(path_d):
        if len(poly) < 3:
            continue
        pts = [(off_x + px * k, off_y + py * k) for px, py in poly]
        d.polygon(pts, fill=rgb(accent))
    return finish(im)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    icons = json.load(open(os.path.join(here, "logo-paths.json")))

    out = {}
    for name, hexv in ACCENTS.items():
        out[f"bar-{name}"] = bar(hexv)
    for name in GAUGE_ACCENTS:
        for step in range(GAUGE_STEPS):
            pct = step * 100 // (GAUGE_STEPS - 1)
            out[f"gauge-{name}-{pct}"] = gauge(ACCENTS[name], pct / 100)
    for product, spec in icons.items():
        for name in ("aqua", "gold", "coral", "grey"):
            out[f"logo-{product}-{name}"] = logo(spec["d"], ACCENTS[name])

    dst = os.path.join(here, "..", "plugin", "src", "artwork.ts")
    with open(dst, "w") as f:
        f.write("// GENERATED by scripts/render-tiles.py -- do not edit.\n")
        f.write("//\n")
        f.write("// Base64 PNG key artwork. PNG rather than SVG because Stream Deck\n")
        f.write("// silently ignores every SVG form we tried, leaving the manifest's\n")
        f.write("// default image on the key. Regenerate with:\n")
        f.write("//   python3 scripts/render-tiles.py\n")
        f.write("export const ART: Record<string, string> = {\n")
        for k in sorted(out):
            f.write(f'  "{k}": "data:image/png;base64,{out[k]}",\n')
        f.write("};\n")
    total = sum(len(v) for v in out.values())
    print(f"wrote {len(out)} images, {total // 1024}KB of base64 -> plugin/src/artwork.ts")


if __name__ == "__main__":
    main()
