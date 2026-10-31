"""Text layers (cropped PNGs) + ffmpeg overlay graph with fade / drift animation."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
import os
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
GF = FD
FONTS = {
    "serif_i": FD + "cormorant-garamond-latin-500-italic.woff",
    "serif_i_light": FD + "cormorant-garamond-latin-400-italic.woff",
    "serif": FD + "cormorant-garamond-latin-600-normal.woff",
    "play_i": FD + "playfair-display-latin-400-italic.woff",
    "sans_l": GF + "Poppins-Light.ttf",
    "sans_r": GF + "Poppins-Regular.ttf",
    "sans_m": GF + "Poppins-Medium.ttf",
}


def _wrap(d, text, f, maxw, track):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if _tw(d, t, f, track) <= maxw:
                cur = t
            else:
                out.append(cur); cur = w
        out.append(cur)
    return out


def _tw(d, s, f, track):
    if not track:
        return d.textlength(s, font=f)
    return sum(d.textlength(c, font=f) for c in s) + track * max(0, len(s) - 1)


def render(el, path):
    """el: text,font,size,color,(x|'center'),y(top),align,track,maxw,lh,shadow,upper"""
    f = ImageFont.truetype(FONTS[el["font"]], el["size"])
    text = el["text"].upper() if el.get("upper") else el["text"]
    track = el.get("track", 0)
    maxw = el.get("maxw", W - 180)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = _wrap(tmp, text, f, maxw, track)
    lh = int(el["size"] * el.get("lh", 1.15))
    bw = int(max(_tw(tmp, l, f, track) for l in lines)) + 80
    bh = lh * len(lines) + int(el["size"] * 0.5) + 80
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    align = el.get("align", "center")
    for i, l in enumerate(lines):
        lw = _tw(d, l, f, track)
        x = 40 if align == "left" else (bw - lw) / 2 if align == "center" else bw - 40 - lw
        y = 40 + i * lh
        if track:
            for c in l:
                d.text((x, y), c, font=f, fill=el["color"]); x += d.textlength(c, font=f) + track
        else:
            d.text((x, y), l, font=f, fill=el["color"])
    sh = el.get("shadow", 0.55)
    if sh:
        a = img.split()[3].filter(ImageFilter.GaussianBlur(el.get("shadow_blur", 10)))
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow.putalpha(a.point(lambda v: int(v * sh)))
        img = Image.alpha_composite(shadow, img)
    img.save(path)
    # position on canvas
    if el.get("x", "center") == "center":
        X = (W - bw) // 2
    else:
        X = el["x"] - 40
    return X, el["y"] - 40


def overlay_graph(base_label, elements, workdir, first_input_index):
    """Returns (input_args, filter_lines, final_label)."""
    args, fl, prev = [], [], base_label
    for k, el in enumerate(elements):
        p = os.path.join(workdir, f"t{k:02d}.png")
        X, Y = render(el, p)
        st, en = el["start"], el["end"]
        fin = el.get("fin", 0.6); fout = el.get("fout", 0.45)
        args += ["-loop", "1", "-framerate", "30", "-t", f"{en + 0.1:.2f}", "-i", p]
        idx = first_input_index + k
        chain = f"[{idx}:v]format=rgba,fade=in:st={st}:d={fin}:alpha=1"
        if fout > 0:
            chain += f",fade=out:st={en - fout:.3f}:d={fout}:alpha=1"
        fl.append(chain + f"[tx{k}]")
        drift = el.get("drift", 22)
        yexpr = f"{Y}+{drift}*max(0\\,1-(t-{st})/{max(fin,0.3)+0.4})" if drift else f"{Y}"
        xd = el.get("xdrift", 0)
        xexpr = f"{X}+{xd}*max(0\\,1-(t-{st})/{fin+0.4})" if xd else f"{X}"
        out = f"ov{k}"
        fl.append(f"[{prev}][tx{k}]overlay=x='{xexpr}':y='{yexpr}':eof_action=pass:"
                  f"enable='between(t,{st},{en})'[{out}]")
        prev = out
    return args, fl, prev
