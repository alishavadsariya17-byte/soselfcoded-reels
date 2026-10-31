"""SO.SELF.CODED daily Reel builder.

Usage:  python3 pipeline/make_day.py specs/<day>.json out/<day>.mp4

Builds the approved "Let Them, Let Me" template (light cream, Oct 30 2026):
  9:16 1080x1920, 28.5 s, cover as first frame (0.5 s) fading into the hook,
  text framed inside Instagram's visible area, soft female voiceover (Kokoro af_heart),
  original soft dreamy piano kept low under the voice, loudness -14 LUFS.

Timeline (seconds, before the 0.5 s cover is prepended):
  hook 0-2.45 | pair 2.55-5.65 | beat1 5.8-8.9 | beat2 9.05-12.15 | beat3 12.3-15.7
  pause (screen dims, no text) 15.7-17.4 | turn 17.5-20.85 | heading 21.0-24.3 (+3 lines)
  closer 24.5-28.0 (+ book credit)
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textfx import overlay_graph, W, H, FONTS  # noqa: E402

D = 28.0
C = (42, 32, 28, 255); M = (110, 96, 86, 240); G = (150, 92, 58, 255)
SIG = (70, 58, 50, 200)
UP = 170  # shift so text centres in Instagram's visible area (top 14% / bottom 35% are covered by UI)


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- background
def background(path):
    bw, bh = 1200, 2134
    y = np.linspace(0, 1, bh)[:, None]; x = np.linspace(0, 1, bw)[None, :]
    top = np.array([0.955, 0.925, 0.875]); bot = np.array([0.900, 0.860, 0.800])
    base = np.broadcast_to(top * (1 - y[..., None]) + bot * y[..., None], (bh, bw, 3)).copy()
    glow = np.exp(-(((x - 0.5) / 0.45) ** 2 + ((y - 0.36) / 0.30) ** 2))
    base += glow[..., None] * np.array([0.035, 0.030, 0.020])
    vig = 1 - 0.10 * np.clip(((x - 0.5) / 0.62) ** 2 + ((y - 0.48) / 0.58) ** 2, 0, 1)
    base *= vig[..., None]
    base += gaussian_filter(np.random.default_rng(3).standard_normal((bh, bw)), 2.0)[..., None] * 0.012
    Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).save(path)


# ---------------------------------------------------------------- cover
def cover(spec, path):
    """Cover block sits in the clear zone (y 330-1230) so nothing hides under Instagram's UI."""
    Wc, Hc = 1080, 1920
    y = np.linspace(0, 1, Hc)[:, None]; x = np.linspace(0, 1, Wc)[None, :]
    top = np.array([0.960, 0.930, 0.880]); bot = np.array([0.905, 0.865, 0.805])
    img = np.broadcast_to(top * (1 - y[..., None]) + bot * y[..., None], (Hc, Wc, 3)).copy()
    img += np.exp(-(((x - 0.5) / 0.5) ** 2 + ((y - 0.45) / 0.32) ** 2))[..., None] * np.array([0.03, 0.025, 0.015])
    img *= (1 - 0.12 * np.clip(((x - 0.5) / 0.6) ** 2 + ((y - 0.5) / 0.6) ** 2, 0, 1))[..., None]
    img += gaussian_filter(np.random.default_rng(5).standard_normal((Hc, Wc)), 0.8)[..., None] * 0.012
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    s = 900 / 1120.0; top_y = 330
    cv = spec["cover"]

    def F(key, z):
        return ImageFont.truetype(FONTS[key], int(z * s))

    def fit(key, z, text, maxw=980):
        f = F(key, z)
        while d.textlength(text, font=f) > maxw and z > 40:
            z -= 6; f = F(key, z)
        return f

    def ct(t, font, yy, col, track=0):
        if track:
            w = sum(d.textlength(c, font=font) for c in t) + track * s * (len(t) - 1)
            xx = (Wc - w) / 2
            for c in t:
                d.text((xx, top_y + yy * s), c, font=font, fill=col); xx += d.textlength(c, font=font) + track * s
        else:
            d.text(((Wc - d.textlength(t, font=font)) / 2, top_y + yy * s), t, font=font, fill=col)

    def ln(yy):
        d.line([(Wc / 2 - 60 * s, top_y + yy * s), (Wc / 2 + 60 * s, top_y + yy * s)], fill=(150, 130, 115), width=2)

    ct(cv["label"].upper(), fit("sans_m", 30, cv["label"].upper(), 900), 0, M[:3], 7); ln(70)
    ct(cv["line1"], fit("serif_i", 250, cv["line1"]), 120, C[:3])
    ct(cv["small"], F("serif_i_light", 88), 460, M[:3])
    ct(cv["line2"], fit("serif_i", 250, cv["line2"]), 540, G[:3])
    ln(900); ct(cv["sub"], fit("sans_l", 40, cv["sub"], 900), 940, M[:3], 1)
    ct("SO.SELF.CODED", F("sans_m", 30), 1080, (70, 58, 50), 9)
    im.save(path, quality=95)


# ---------------------------------------------------------------- text track
def elements(spec):
    E = []

    def add(**k):
        k.setdefault("shadow", 0)
        if k.get("text") != "SO.SELF.CODED":
            k["y"] -= UP
        E.append(k)

    add(text=spec["hook"], font="sans_m", size=64, color=C, y=820, maxw=820, lh=1.3,
        start=0.0, end=2.45, fin=0.25, drift=0)
    add(text=spec["pair"][0], font="serif_i", size=92, color=C, y=760, maxw=900, start=2.55, end=5.65)
    add(text=spec["pair"][1], font="serif_i", size=92, color=C, y=880, maxw=900, start=3.6, end=5.65)
    for (s, e), (setup, punch) in zip([(5.8, 8.9), (9.05, 12.15), (12.3, 15.7)], spec["beats"]):
        add(text=setup, font="sans_l", size=54, color=M, y=780, maxw=880, start=s, end=e)
        psize = 150 if len(punch) <= 12 else 116 if len(punch) <= 18 else 92
        add(text=punch, font="serif_i", size=psize, color=C, y=870, maxw=940, start=s + 0.9, end=e)
    add(text=spec["turn"], font="serif_i", size=96, color=C, y=800, maxw=820, lh=1.1,
        start=17.5, end=20.85, fin=0.9)
    add(text=spec["heading"], font="serif_i", size=190 if len(spec["heading"]) <= 9 else 140, color=G,
        y=600, maxw=960, start=21.0, end=24.3, fin=0.5)
    for i, l in enumerate(spec["lines"]):
        add(text=l, font="sans_l", size=58, color=C, y=900 + i * 110, maxw=940, start=21.9 + i * 0.8,
            end=24.3, track=2)
    add(text=spec["closer"], font="serif_i", size=104, color=C, y=720, maxw=860, lh=1.08,
        start=24.5, end=28.0, fin=0.8, fout=0)
    add(text=f"a lesson from {spec['book']} — {spec['author']}", font="sans_l", size=32, color=M,
        y=1130, maxw=1000, start=25.6, end=28.0, fout=0, drift=0)
    add(text="SO.SELF.CODED", font="sans_m", size=30, color=SIG, y=1190, track=9,
        start=0.0, end=28.0, fin=0.2, fout=0, drift=0)
    return E


def render_video(spec, wk, out):
    background(f"{wk}/bg.png")
    args = ["-loop", "1", "-framerate", "30", "-t", str(D), "-i", f"{wk}/bg.png",
            "-f", "lavfi", "-t", str(D), "-i", "color=black:s=1080x1920:r=30"]
    fl = [f"[0:v]scale=w='1200*(1+0.05*t/{D})':h=-2:eval=frame,crop=1080:1920,noise=alls=7:allf=t,format=rgba[bg0]",
          "[1:v]format=rgba,colorchannelmixer=aa=0.22,fade=in:st=15.6:d=0.5:alpha=1,fade=out:st=17.0:d=0.6:alpha=1[dim]",
          "[bg0][dim]overlay=0:0[bg1]"]
    targs, tfl, last = overlay_graph("bg1", elements(spec), wk, 2)
    fl += tfl + [f"[{last}]fade=in:st=0:d=0.25,fade=out:st={D - 0.7}:d=0.7,format=yuv420p[v]"]
    run(["ffmpeg", "-y", "-loglevel", "error", *args, *targs, "-filter_complex", ";".join(fl),
         "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", "30", "-t", str(D), out])


# ---------------------------------------------------------------- voiceover
VO_SLOTS = [  # (start, latest end)
    ("hook", 0.15, 3.0), ("pair", 3.1, 5.85), ("beat0", 5.9, 9.0), ("beat1", 9.1, 12.3),
    ("beat2", 12.4, 15.6), ("turn", 17.6, 20.8), ("heading", 21.05, 22.2), ("lines", 22.6, 25.35),
    ("closer", 25.45, 27.65)]


def vo_texts(spec):
    b = spec["beats"]
    return {"hook": spec["hook"], "pair": " ".join(spec["pair"]),
            "beat0": f"{b[0][0]}... {b[0][1]}", "beat1": f"{b[1][0]}... {b[1][1]}",
            "beat2": f"{b[2][0]}... {b[2][1]}", "turn": spec["turn"], "heading": spec["heading"],
            "lines": " ".join(spec["lines"]), "closer": spec["closer"]}


def voiceover(spec, out_wav):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    mdir = os.environ.get("KOKORO_DIR", os.path.join(HERE, "..", ".models"))
    k = Kokoro(os.path.join(mdir, "kokoro-v1.0.onnx"), os.path.join(mdir, "voices-v1.0.bin"))
    texts = vo_texts(spec); sr = 24000
    buf = np.zeros(int(28.5 * sr), np.float32); report = []
    for key, st, latest in VO_SLOTS:
        speed = 0.88
        while True:
            a, sr = k.create(texts[key], voice="af_heart", speed=speed, lang="en-us")
            dur = len(a) / sr
            if st + dur <= latest or speed >= 1.2:
                break
            speed = round(speed + 0.04, 2)
        i = int(st * sr); buf[i:i + len(a)] += a[:len(buf) - i]
        report.append(f"{key:8s} {st:5.2f}-{st + dur:5.2f} (limit {latest}) speed {speed}")
    sf.write(out_wav, buf[:int(D * sr)], sr)
    return report


# ---------------------------------------------------------------- assemble
def build(spec_path, out_mp4):
    spec = json.load(open(spec_path))
    wk = tempfile.mkdtemp(prefix="reel_")
    cover(spec, f"{wk}/cover.jpg")
    render_video(spec, wk, f"{wk}/video.mp4")
    music = f"{wk}/music.wav"
    run([sys.executable, os.path.join(HERE, "music.py"), music, str(spec.get("music_key", 0)),
         str(spec.get("music_seed", 33))])
    for line in voiceover(spec, f"{wk}/vo.wav"):
        print("  vo", line)
    vo_chain = ("aresample=44100,highpass=f=90,lowpass=f=9000,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=200,"
                "equalizer=f=3500:t=q:w=1.2:g=-2,volume=1.6,aecho=0.8:0.6:60|120:0.10|0.06,pan=stereo|c0=c0|c1=c0")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wk}/video.mp4", "-i", music, "-i", f"{wk}/vo.wav",
         "-filter_complex",
         f"[2:a]{vo_chain},asplit=2[vo][sc];[1:a]volume=0.30[mus];"
         "[mus][sc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=600[duck];"
         "[duck][vo]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(D), f"{wk}/mix.mp4"])
    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", "0.8", "-i", f"{wk}/cover.jpg",
         "-i", f"{wk}/mix.mp4", "-filter_complex",
         "[0:v]scale=1080:1920,format=yuv420p,setsar=1,fps=30[c];"
         "[1:v]trim=start=0.3,setpts=PTS-STARTPTS,tpad=start_duration=0.3:start_mode=clone,format=yuv420p,setsar=1,fps=30[v];"
         "[c][v]xfade=transition=fade:duration=0.3:offset=0.5,format=yuv420p,setsar=1[vo];"
         "[1:a]adelay=500|500,afade=t=in:st=0.5:d=0.3[ao]",
         "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_mp4])
    cover_out = os.path.splitext(out_mp4)[0] + "_cover.jpg"
    run(["cp", f"{wk}/cover.jpg", cover_out])
    print("built", out_mp4)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
