"""Short text-only Reel formats (no voiceover, no music). Usage:
    python3 pipeline/formats.py specs/examples/<name>.json out.mp4
Spec: {"format": "minimal|pov|discipline|notes|readthis", ...format fields}
Renders PIL frames at 30 fps and encodes 1080x1920 H.264 with a silent AAC track.
"""
import json, os, subprocess, sys, tempfile, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textfx import FONTS, W, H, _wrap, _tw  # noqa: E402

FPS = 30
CREAM, ESPRESSO, TERRA, MUTED = (243, 236, 226), (43, 30, 24), (166, 90, 58), (120, 104, 94)
INK, BONE = (14, 13, 12), (240, 236, 230)
_font_cache = {}


def font(key, size):
    k = (key, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(FONTS[key], size)
    return _font_cache[k]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def bg_soft(color, vignette=0.10, grain_seed=0):
    img = Image.new("RGB", (W, H), color)
    # gentle radial vignette
    mask = Image.radial_gradient("L").resize((W, H))
    dark = Image.new("RGB", (W, H), tuple(int(c * (1 - vignette * 2)) for c in color))
    return Image.composite(dark, img, mask.point(lambda p: int(p * 0.6)))


def draw_lines(img, lines, f, y, color, alpha=1.0, align="center", lh=1.25, x=None, dy=0):
    """Draw pre-wrapped lines with alpha onto img; returns bottom y."""
    if alpha <= 0:
        return y + int(f.size * lh) * len(lines)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = int(f.size * lh)
    for i, l in enumerate(lines):
        lw = d.textlength(l, font=f)
        xx = (W - lw) / 2 if align == "center" else x
        d.text((xx, y + dy + i * step), l, font=f, fill=color + (int(255 * alpha),))
    img.paste(layer, (0, 0), layer)
    return y + step * len(lines)


def wrap(text, f, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    return _wrap(d, text, f, maxw, 0)


def handle(img, color, t, start=0.0, y=H - 300):
    f = font("sans_r", 30)
    a = ease((t - start) / 0.6)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = "S O . S E L F . C O D E D"
    d.text(((W - d.textlength(s, font=f)) / 2, y), s, font=f, fill=color + (int(200 * a),))
    img.paste(lay, (0, 0), lay)


# ---------------------------------------------------------------- formats
def f_minimal(s):
    """One quote, word-by-word reveal on cream; optional terracotta last line."""
    base = bg_soft(CREAM)
    fq = font("serif_i", s.get("size", 84))
    fl = font("serif_i", s.get("size", 84))
    qlines = wrap(s["quote"], fq, 900)
    words = s["quote"].split()
    dur = s.get("duration", 9.0)
    per = s.get("word_time", 0.22)
    last = s.get("last", "")
    llines = wrap(last, fl, 900) if last else []
    total_h = int(fq.size * 1.25) * (len(qlines) + len(llines)) + (70 if last else 0)
    y0 = (H - total_h) // 2 - 80
    t_last = 0.5 + per * len(words) + 0.6

    def frame(t):
        img = base.copy()
        # word reveal: compute how many words visible + partial alpha
        n = (t - 0.4) / per
        y = y0
        wi = 0
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        step = int(fq.size * 1.25)
        for li, l in enumerate(qlines):
            ws = l.split()
            lw = d.textlength(l, font=fq)
            x = (W - lw) / 2
            for w in ws:
                a = ease(n - wi)
                if a > 0:
                    d.text((x, y + li * step + (1 - a) * 14), w, font=fq, fill=ESPRESSO + (int(255 * a),))
                x += d.textlength(w + " ", font=fq)
                wi += 1
        img.paste(lay, (0, 0), lay)
        if last:
            a = ease((t - t_last) / 0.7)
            draw_lines(img, llines, fl, y0 + step * len(qlines) + 70, TERRA, a, dy=(1 - a) * 16)
        if s.get("footer"):
            a = ease((t - t_last - 1.0) / 0.6)
            draw_lines(img, [s["footer"]], font("sans_l", 34), H - 420, MUTED, a)
        handle(img, MUTED, t, 0.2)
        return img
    return frame, dur


def f_pov(s):
    """'POV:' label + setup line, then short lines stacking in, last in accent."""
    base = bg_soft(CREAM)
    fpov, fset, fl = font("sans_m", 40), font("serif_i", 76), font("serif_i", 64)
    setup = wrap(s["setup"], fset, 900)
    items = s["lines"]
    dur = s.get("duration", 11.0)
    step_set, step_l = int(76 * 1.22), int(64 * 1.5)
    total = 60 + step_set * len(setup) + 90 + step_l * len(items)
    y0 = (H - total) // 2 - 60
    t0 = 2.2

    def frame(t):
        img = base.copy()
        a = ease((t - 0.1) / 0.4)
        draw_lines(img, [s.get("label", "POV:")], fpov, y0, TERRA, a)
        a = ease((t - 0.3) / 0.6)
        y = draw_lines(img, setup, fset, y0 + 70, ESPRESSO, a, lh=1.22, dy=(1 - a) * 18)
        y += 90
        for i, l in enumerate(items):
            ti = t0 + i * s.get("gap", 1.3)
            a = ease((t - ti) / 0.5)
            col = TERRA if i == len(items) - 1 and s.get("accent_last", True) else ESPRESSO
            draw_lines(img, [l], fl, y + i * step_l, col, a, dy=(1 - a) * 14)
        handle(img, MUTED, t, 0.2)
        return img
    return frame, dur


def f_discipline(s):
    """Dark, bold uppercase, one hard-cut line at a time; accent word in terracotta."""
    fb = font("sans_m", s.get("size", 104))
    beats = s["beats"]  # list of [text, seconds]
    dur = sum(b[1] for b in beats) + s.get("tail", 1.5)
    accent = set(w.upper() for w in s.get("accent", []))
    base = Image.new("RGB", (W, H), INK)

    def frame(t):
        img = base.copy()
        acc = 0
        idx = len(beats) - 1
        for i, b in enumerate(beats):
            if t < acc + b[1]:
                idx = i
                break
            acc += b[1]
        if t >= sum(b[1] for b in beats):
            idx, acc = len(beats) - 1, sum(b[1] for b in beats[:-1])
        text = beats[idx][0].upper()
        lines = wrap(text, fb, 920)
        local = t - acc
        sc = 1.0 + 0.04 * ease(local / 0.25)  # tiny punch-in
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        step = int(fb.size * 1.12)
        y = (H - step * len(lines)) // 2 - 60
        for li, l in enumerate(lines):
            x = (W - d.textlength(l, font=fb)) / 2
            for w in l.split():
                col = TERRA if w.strip(".,!?") in accent else BONE
                d.text((x, y + li * step), w, font=fb, fill=col + (255,))
                x += d.textlength(w + " ", font=fb)
        if abs(sc - 1) > 1e-3:
            lay = lay.resize((int(W * sc), int(H * sc)), Image.BICUBIC)
            lay = lay.crop(((lay.width - W) // 2, (lay.height - H) // 2, (lay.width - W) // 2 + W, (lay.height - H) // 2 + H))
        img.paste(lay, (0, 0), lay)
        handle(img, (130, 124, 118), t, 0.0)
        return img
    return frame, dur


def f_notes(s):
    """Notes-app style card; title then list items typed in one by one."""
    base = bg_soft((233, 225, 214))
    ft, fi, fd = font("sans_m", 52), font("sans_r", 42), font("sans_l", 28)
    items = s["items"]
    cps = s.get("chars_per_sec", 34)
    gap = s.get("gap", 0.55)
    card_x, card_w = 90, W - 180
    wrapped = [wrap(it, fi, card_w - 140) for it in items]
    starts, t = [], 1.4
    for it in items:
        starts.append(t)
        t += len(it) / cps + gap
    dur = t + s.get("tail", 2.5)
    step = int(42 * 1.45)
    body_h = sum(len(w) * step + 34 for w in wrapped)
    card_h = 220 + body_h + 80
    card_y = (H - card_h) // 2 - 40

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, card_w - 1, card_h - 1], 44, fill=(252, 250, 246, 255))
    shadow = Image.new("RGBA", (card_w + 120, card_h + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([60, 74, card_w + 60, card_h + 74], 44, fill=(60, 40, 30, 50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    base = base.convert("RGBA")
    base.alpha_composite(shadow, (card_x - 60, card_y - 60))
    base.alpha_composite(card, (card_x, card_y))
    bd = ImageDraw.Draw(base)
    bd.text((card_x + 70, card_y + 60), s.get("date", "Notes"), font=fd, fill=MUTED)
    bd.text((card_x + 70, card_y + 104), s["title"], font=ft, fill=ESPRESSO)
    base = base.convert("RGB")

    def frame(t):
        img = base.copy()
        d = ImageDraw.Draw(img)
        y = card_y + 220
        for i, it in enumerate(items):
            n = int(max(0, (t - starts[i])) * cps)
            shown = it[:n]
            cnt = 0
            for li, l in enumerate(wrapped[i]):
                seg = shown[cnt:cnt + len(l) + 1].rstrip()
                cnt += len(l) + 1
                pre = "–  " if li == 0 else "    "
                col = TERRA if (i == len(items) - 1 and s.get("accent_last", True)) else ESPRESSO
                if seg:
                    d.text((card_x + 70, y + li * step), pre + seg, font=fi, fill=col)
            # cursor
            if starts[i] <= t < (starts[i + 1] if i + 1 < len(items) else dur) and int(t * 2) % 2 == 0:
                lw = len(wrapped[i]) - 1
                # place cursor after last typed char roughly
                lines_done = 0; rem = n; acc = 0
                for li, l in enumerate(wrapped[i]):
                    if rem <= len(l):
                        lines_done = li; break
                    rem -= len(l) + 1; lines_done = li
                cx = card_x + 70 + d.textlength(("–  " if lines_done == 0 else "    ") + wrapped[i][lines_done][:max(0, rem)], font=fi)
                d.rectangle([cx + 4, y + lines_done * step + 6, cx + 8, y + lines_done * step + 50], fill=TERRA)
            y += len(wrapped[i]) * step + 34
        handle(img, MUTED, t, 0.2, y=H - 260)
        return img
    return frame, dur


def f_readthis(s):
    """Big opener ('Read this if…'), then 3 permission lines fade in under it."""
    base = bg_soft(CREAM)
    fh, fl, fs = font("serif_i", 92), font("serif_i_light", 62), font("sans_l", 34)
    head = wrap(s["opener"], fh, 920)
    items = [wrap(x, fl, 880) for x in s["lines"]]
    dur = s.get("duration", 12.0)
    step_h, step_l = int(92 * 1.15), int(62 * 1.3)
    total = step_h * len(head) + 110 + sum(len(w) * step_l + 46 for w in items)
    y0 = (H - total) // 2 - 70

    def frame(t):
        img = base.copy()
        a = ease((t - 0.1) / 0.5)
        y = draw_lines(img, head, fh, y0, ESPRESSO, a, lh=1.15, dy=(1 - a) * 18)
        # thin terracotta rule
        a2 = ease((t - 0.9) / 0.5)
        d = ImageDraw.Draw(img)
        if a2 > 0:
            w = int(120 * a2)
            d.line([(W // 2 - w // 2, y + 50), (W // 2 + w // 2, y + 50)], fill=TERRA, width=3)
        y += 110
        for i, w in enumerate(items):
            ti = 2.0 + i * s.get("gap", 1.8)
            a = ease((t - ti) / 0.6)
            col = TERRA if i == len(items) - 1 else ESPRESSO
            y = draw_lines(img, w, fl, y, col, a, lh=1.3, dy=(1 - a) * 14) + 46
        if s.get("footer"):
            a = ease((t - (dur - 2.2)) / 0.6)
            draw_lines(img, [s["footer"]], fs, H - 420, MUTED, a)
        handle(img, MUTED, t, 0.2)
        return img
    return frame, dur


FORMATS = {"minimal": f_minimal, "pov": f_pov, "discipline": f_discipline,
           "notes": f_notes, "readthis": f_readthis}


def build(spec_path, out):
    s = json.load(open(spec_path))
    frame, dur = FORMATS[s["format"]](s)
    n = int(round(dur * FPS))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    p.wait()
    # cover = last frame
    frame(dur - 0.05).convert("RGB").save(out.rsplit(".", 1)[0] + "_cover.jpg", quality=92)
    print(f"built {out} ({dur:.1f}s)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
