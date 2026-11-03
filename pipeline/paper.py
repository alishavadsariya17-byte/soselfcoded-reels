"""Minimal 'quote page' Reels in the style of top quote accounts: textured paper / photo backgrounds,
small serif or handwritten text, lots of empty space, short (~7 s), soft background music, no voiceover.

Usage: python3 pipeline/paper.py specs/<file>.json out.mp4

Spec:
{
 "bg": "paper" | "coffee" | "torn" | "solid",
 "paper": [r,g,b]  (paper/solid colour), "specks": 0..1, "mottle": 0..1,
 "x": 120 (left margin, used when align=left), "y": "center" | px, "width": 840,
 "blocks": [ {"text": "...", "font": "garamond", "size": 54, "color": [r,g,b], "align": "left|center",
              "gap": 60 (space before), "t": 0.6 (appear time), "style": "fade|write|highlight",
              "lh": 1.35, "upper": false, "rotate": 0, "underline_last": false, "heart": false} ],
 "duration": 7.5, "music": {"mood": "dreamy|warm|dark", "key": 0, "seed": 1, "volume": 0.5},
 "caption": "..."
}
Inline *word* switches to the italic of the same family (garamond -> garamond_i, tinos -> tinos_i).
"""
import json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts") + "/"
W, H, FPS = 1080, 1920, 30
FONTS = {
    "garamond": "eb-garamond-latin-400-normal.woff", "garamond_i": "eb-garamond-latin-400-italic.woff",
    "tinos": "tinos-latin-400-normal.woff", "tinos_i": "tinos-latin-400-italic.woff",
    "sserif": "source-serif-4-latin-400-normal.woff", "sserif_i": "eb-garamond-latin-400-italic.woff",
    "corm_i": "cormorant-garamond-latin-500-italic.woff", "corm": "cormorant-garamond-latin-600-normal.woff",
    "caveat": "caveat-latin-500-normal.woff", "indie": "indie-flower-latin-400-normal.woff",
    "gaegu": "gaegu-latin-400-normal.woff", "reenie": "reenie-beanie-latin-400-normal.woff",
    "poppins": "Poppins-Light.ttf",
}
ITAL = {"garamond": "garamond_i", "tinos": "tinos_i", "sserif": "sserif_i"}
_fc = {}


def font(k, s):
    if (k, s) not in _fc:
        _fc[(k, s)] = ImageFont.truetype(FD + FONTS[k], s)
    return _fc[(k, s)]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def blurnoise(rng, w, h, sigma):
    from scipy.ndimage import gaussian_filter
    n = gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), sigma, mode="wrap")
    return n / (n.std() + 1e-6)


# ------------------------------------------------------------------ backgrounds
def bg_paper(s, rng):
    col = np.array(s.get("paper", [233, 231, 226]), np.float32)
    mott = s.get("mottle", 0.5)
    img = np.ones((H, W, 3), np.float32) * col
    img += (blurnoise(rng, W, H, 60) * 4.5 * mott + blurnoise(rng, W, H, 8) * 2.0 * mott)[..., None]
    img += rng.normal(0, 3.2 * s.get("fiber", 1.0), (H, W, 1)).astype(np.float32)
    # gentle vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.06 * (((xx - W / 2) / W) ** 2 * 4 + ((yy - H / 2) / H) ** 2 * 4) * s.get("vignette", 1.0)
    img *= v[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    sp = s.get("specks", 0.3)
    if sp:
        d = ImageDraw.Draw(im)
        scol = tuple(s.get("speck_color", [120, 110, 105]))
        for _ in range(int(2600 * sp)):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            r = rng.choice([0.6, 0.8, 1.0, 1.4, 2.0], p=[.4, .3, .17, .1, .03])
            a = int(rng.uniform(40, 160))
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * (1 - a / 400) + 0) for c in scol))
    return im


def bg_solid(s, rng):
    col = np.array(s.get("paper", [104, 22, 24]), np.float32)
    img = np.ones((H, W, 3), np.float32) * col
    img += (blurnoise(rng, W, H, 90) * 1.0)[..., None]
    img += rng.normal(0, 1.6, (H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def bg_coffee(s, rng):
    """Top-down glass cup of coffee on black."""
    cx, cy, R = 600, 860, 600
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot(xx - cx, yy - cy)
    img = np.ones((H, W, 3), np.float32) * 9
    img += (blurnoise(rng, W, H, 50) * 2)[..., None]
    # liquid
    Rl = R - 62
    tt = np.clip(r / Rl, 0, 1)
    swirl = blurnoise(rng, W, H, 70) * 0.7 + blurnoise(rng, W, H, 25) * 0.15
    ang = np.arctan2(yy - cy, xx - cx)
    swirl2 = np.sin(ang * 2 + r / 140 + swirl * 1.5)
    base = np.stack([92 - 34 * tt, 56 - 22 * tt, 36 - 15 * tt], -1)
    crema = (np.clip(swirl2 * 0.5 + swirl * 0.6, -1, 1) * 0.5 + 0.5)[..., None]
    liquid = base * (0.88 + 0.22 * crema) + np.array([12, 7, 3]) * crema
    liquid *= (1 - 0.45 * np.clip((r - Rl * 0.82) / (Rl * 0.18), 0, 1) ** 1.5)[..., None]
    inside = (r < Rl)[..., None]
    img = np.where(inside, liquid, img)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    # foam bubbles near top edge
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(520):
        a = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
        rr = Rl * (1 - abs(rng.normal(0, 0.12)))
        if rr > Rl - 6:
            continue
        bx, by = cx + rr * math.cos(a), cy + rr * math.sin(a)
        br = abs(rng.normal(0, 4.5)) + 2
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(40, 24, 14, 200), outline=(130, 92, 64, 150))
    # glass rim + handle
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glass)
    g.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(190, 196, 204, 42), width=58)
    g.ellipse([cx - Rl - 4, cy - Rl - 4, cx + Rl + 4, cy + Rl + 4], outline=(220, 225, 230, 120), width=5)
    g.ellipse([cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6], outline=(235, 238, 240, 90), width=4)
    hx = cx - R * 0.72
    glass = glass.rotate(-35, center=(hx, cy + R * 0.6), resample=Image.BICUBIC) if False else glass
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).arc([cx - R + 20, cy - R + 20, cx + R - 20, cy + R - 20], 195, 250, fill=(255, 255, 255, 140), width=10)
    hl = hl.filter(ImageFilter.GaussianBlur(4))
    glass = glass.filter(ImageFilter.GaussianBlur(1.5))
    im.alpha_composite(glass); im.alpha_composite(hl)
    return im.convert("RGB")


def bg_torn(s, rng):
    """Torn piece of paper on a wall, with soft window shadow."""
    wall = np.ones((H, W, 3), np.float32) * np.array([226, 223, 216], np.float32)
    wall += (blurnoise(rng, W, H, 3) * 3)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx * 0.55 + yy * 0.83)
    shade = 0.55 + 0.45 * (0.5 + 0.5 * np.tanh((u - 1250) / 120)) * (0.5 + 0.5 * np.tanh((2050 - u) / 160))
    shade = np.maximum(shade, 0.55 + 0.45 * (0.5 + 0.5 * np.tanh((u - 300) / 140)) * (0.5 + 0.5 * np.tanh((700 - u) / 140)) * 0.6)
    wall *= shade[..., None]
    im = Image.fromarray(np.clip(wall, 0, 255).astype(np.uint8)).convert("RGBA")
    x0, y0, x1, y1 = 150, 560, 940, 1420
    pts = []
    for k in range(40): pts.append((x0 + (x1 - x0) * k / 39, y0 + rng.normal(0, 6)))
    for k in range(50): pts.append((x1 + rng.normal(0, 9) + (8 if k % 3 == 0 else 0), y0 + (y1 - y0) * k / 49))
    for k in range(40): pts.append((x1 - (x1 - x0) * k / 39, y1 + rng.normal(0, 6)))
    for k in range(50): pts.append((x0 + rng.normal(0, 11) - (10 if k % 4 == 0 else 0), y1 - (y1 - y0) * k / 49))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + 18, y + 22) for x, y in pts], fill=(40, 35, 30, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(sh)
    paper = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(paper).polygon(pts, fill=(240, 241, 244, 255))
    edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(edge).polygon(pts, outline=(255, 255, 255, 255), width=5)
    im.alpha_composite(paper); im.alpha_composite(edge.filter(ImageFilter.GaussianBlur(1)))
    # paper fibre + shade the paper with the same light
    a = np.asarray(im.convert("RGB"), np.float32)
    mask = np.asarray(paper.split()[3], np.float32)[..., None] / 255
    a = a * (1 - mask) + mask * (a * (0.7 + 0.3 * shade[..., None]) + rng.normal(0, 2, (H, W, 1)))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


BGS = {"paper": bg_paper, "solid": bg_solid, "coffee": bg_coffee, "torn": bg_torn}


# ------------------------------------------------------------------ text layout
def layout_block(b, width):
    """Return list of lines; each line = list of (word, fontkey, width)."""
    fk = b.get("font", "garamond"); sz = b.get("size", 54)
    text = b["text"].upper() if b.get("upper") else b["text"]
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines = []
    for para in text.split("\n"):
        cur, cw = [], 0
        ital = False
        for w in para.split():
            k = fk
            if w.startswith("*"): ital = True; w = w[1:]
            this_ital = ital
            if w.endswith("*") or w.endswith("*,") or w.endswith("*."):
                w = w.replace("*", ""); ital = False
            if this_ital: k = ITAL.get(fk, fk)
            f = font(k, sz)
            ww = d.textlength(w, font=f)
            sp = d.textlength(" ", font=font(fk, sz)) * b.get("space", 1.0)
            if cur and cw + sp + ww > width:
                lines.append(cur); cur, cw = [], 0
            cur.append((w, k, ww)); cw += (sp if len(cur) > 1 else 0) + ww
        lines.append(cur)
    return lines


def render_text(s):
    """Pre-render each block to its own RGBA layer and return [(layer, bbox rows, block)]."""
    width = s.get("width", 840)
    x_left = s.get("x", 120)
    blocks = s["blocks"]
    laid = []
    total = 0
    for b in blocks:
        lines = layout_block(b, b.get("width", width))
        lh = int(b.get("size", 54) * b.get("lh", 1.35))
        gap = b.get("gap", 0) if laid else 0
        laid.append((b, lines, lh, gap))
        total += gap + lh * len(lines)
    y = (H - total) // 2 + s.get("y_offset", -60) if s.get("y", "center") == "center" else s["y"]
    out = []
    d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for b, lines, lh, gap in laid:
        y += gap
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        col = tuple(b.get("color", [28, 26, 24]))
        sz = b.get("size", 54)
        rows = []
        rowlays = []
        for li, ln in enumerate(lines):
            rl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rl); rowlays.append(rl)
            sp = d0.textlength(" ", font=font(b.get("font", "garamond"), sz)) * b.get("space", 1.0)
            lw = sum(w for _, _, w in ln) + sp * max(0, len(ln) - 1)
            align = b.get("align", s.get("align", "left"))
            x = x_left + b.get("indent", 0) if align == "left" else (W - lw) / 2
            x0 = x
            for w, k, ww in ln:
                d.text((x, y + li * lh), w, font=font(k, sz), fill=col)
                rd.text((x, y + li * lh), w, font=font(k, sz), fill=col)
                x += ww + sp
            rows.append((x0, y + li * lh, x0 + lw, sz))
        if b.get("underline_last") and rows:
            ln = lines[-1]; w_last = ln[-1][2]
            x1 = rows[-1][2]; yb = rows[-1][1] + sz * 1.08
            d.line([(x1 - w_last, yb), (x1 + 4, yb - 3)], fill=col, width=max(3, sz // 18))
            ImageDraw.Draw(rowlays[-1]).line([(x1 - w_last, yb), (x1 + 4, yb - 3)], fill=col, width=max(3, sz // 18))
        if b.get("heart"):
            hx, hy, r = (rows[-1][0] + rows[-1][2]) / 2, rows[-1][1] + lh + 10, sz * 0.32
            pts = [(hx + r * 16 * math.sin(t) ** 3 / 16, hy - r * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16)
                   for t in np.linspace(0, 2 * math.pi, 60)]
            d.line(pts + [pts[0]], fill=col, width=max(3, sz // 20), joint="curve")
            hl_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rowlays.append(hl_)
            ImageDraw.Draw(hl_).line(pts + [pts[0]], fill=col, width=max(3, sz // 20), joint="curve")
            rows.append((hx - r, hy - r, hx + r, sz))
        if b.get("rotate"):
            cxy = ((rows[0][0] + rows[-1][2]) / 2, (rows[0][1] + rows[-1][1]) / 2)
            lay = lay.rotate(b["rotate"], center=cxy, resample=Image.BICUBIC)
            rowlays = [r.rotate(b["rotate"], center=cxy, resample=Image.BICUBIC) for r in rowlays]
        y += lh * len(lines)
        out.append((lay, rows, b, rowlays))
    return out


def build(spec_path, out):
    s = json.load(open(spec_path))
    rng = np.random.default_rng(s.get("seed", 4))
    bg = BGS[s.get("bg", "paper")](s, rng)
    layers = render_text(s)
    dur = s.get("duration", 7.5)
    hl_col = np.array(s.get("highlight_color", [236, 226, 40]), np.float32) / 255
    bg_np = np.asarray(bg, np.float32)
    # highlight masks
    hl = []
    for lay, rows, b, *_ in layers:
        if b.get("style") == "highlight":
            for x0, y0, x1, sz in rows:
                m = Image.new("L", (W, H), 0)
                md = ImageDraw.Draw(m)
                top, bot = y0 + sz * 0.12, y0 + sz * 1.15
                pts = [(x0 - 10, top + rng.normal(0, 2))] + [(x0 - 10 + (x1 - x0 + 20) * k / 10, top + rng.normal(0, 2.4)) for k in range(11)]
                pts += [(x1 + 10 - (x1 - x0 + 20) * k / 10, bot + rng.normal(0, 2.4)) for k in range(11)]
                md.polygon(pts, fill=215)
                hl.append((np.asarray(m.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255, x0 - 12, x1 + 12, b))
    zoom = s.get("zoom", [1.0, 1.035])
    layers_rl = {id(L[2]): L[3] for L in layers}

    def frame(t):
        a = bg_np
        if hl:
            a = a.copy()
            by_block = {}
            for m, xa, xb, b in hl:
                by_block.setdefault(id(b), []).append((m, xa, xb, b))
            for rows in by_block.values():
                b = rows[0][3]
                p = (t - b.get("t_hl", b.get("t", 0.5) + 0.7)) / b.get("sweep", 1.1)
                for i, (m, xa, xb, _) in enumerate(rows):
                    pr = p * len(rows) - i
                    if pr <= 0: continue
                    xe = int(xa + (xb - xa) * min(1, smooth(pr)))
                    mm = m.copy(); mm[:, xe:] = 0
                    a = a * (1 - mm[..., None] * (1 - hl_col))
        img = Image.fromarray(a.astype(np.uint8))
        for lay, rows, b, *_ in layers:
            t0 = b.get("t", 0.4)
            st = b.get("style", "fade")
            if st == "write":
                cps = b.get("cps", 22)
                chars = [max(1, (r[2] - r[0]) / (b.get("size", 54) * 0.5)) for r in rows]
                tt = t - t0
                rowlays = layers_rl[id(b)]
                cxy = ((rows[0][0] + rows[-1][2]) / 2, (rows[0][1] + rows[-1][1]) / 2)
                for (x0, y0, x1, sz), c, rl in zip(rows, chars, rowlays):
                    dl = c / cps
                    p = min(1, max(0, tt / dl))
                    if p > 0:
                        m = Image.new("L", (W, H), 0)
                        ImageDraw.Draw(m).rectangle([0, 0, x0 + (x1 - x0) * p + 6, H], fill=255)
                        if b.get("rotate"):
                            m = m.rotate(b["rotate"], center=cxy)
                        alpha = Image.fromarray((np.asarray(rl.split()[3], np.float32) * (np.asarray(m, np.float32) / 255)).astype(np.uint8))
                        img.paste(rl, (0, 0), alpha)
                    tt -= dl + 0.12
                    if tt < 0: break
            else:
                al = ease((t - t0) / b.get("fade", 0.7))
                if al <= 0: continue
                alpha = lay.split()[3].point(lambda p: int(p * al))
                img.paste(lay, (0, 0), alpha)
        z = zoom[0] + (zoom[1] - zoom[0]) * smooth(t / dur)
        if abs(z - 1) > 1e-4:
            cw, ch = W / z, H / z
            img = img.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        g = np.random.default_rng(int(t * FPS)).integers(-3, 4, (H // 2, W // 2), dtype=np.int16).repeat(2, 0).repeat(2, 1)
        return Image.fromarray(np.clip(np.asarray(img, np.int16) + g[..., None], 0, 255).astype(np.uint8))

    final = frame(dur - 0.05)
    if out.endswith(".png"):  # quick still preview of the final frame (= the cover / grid thumbnail)
        final.save(out); print("still", out); return
    # Cover-first: hold the finished design (this frame becomes the Reel thumbnail and makes the loop seamless),
    # dissolve to the start of the animation, then rebuild it.
    ic, xf = s.get("intro_cover", 0.7), s.get("intro_fade", 0.35)
    total = ic + xf + dur

    def out_frame(T):
        if T < ic:
            return final
        if T < ic + xf:
            return Image.blend(final, frame(0.0), smooth((T - ic) / xf))
        return frame(T - ic - xf)

    mu = s.get("music", {})
    wk = tempfile.mkdtemp()
    wav = os.path.join(wk, "m.wav")
    if mu.get("style"):
        subprocess.run([sys.executable, os.path.join(HERE, "songs.py"), wav, str(total), mu["style"],
                        str(mu.get("key", 0)), str(mu.get("seed", 1))], check=True, stdout=subprocess.DEVNULL)
    else:
        subprocess.run([sys.executable, os.path.join(HERE, "lofi.py"), wav, str(total), mu.get("mood", "dreamy"),
                        str(mu.get("key", 0)), str(mu.get("seed", 7))], check=True, stdout=subprocess.DEVNULL)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-filter:a", f"volume={mu.get('volume', 1.0 if mu.get('style') else 0.6)}", "-c:v", "libx264",
           "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(round(total * FPS))):
        p.stdin.write(out_frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    final.save(out.rsplit(".", 1)[0] + "_cover.jpg", quality=92)
    # 3:4 grid preview (what the profile grid shows)
    final.crop((0, 240, W, 1680)).resize((540, 720)).save(out.rsplit(".", 1)[0] + "_grid.jpg", quality=88)
    print(f"built {out} ({total:.1f}s)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
