"""Song-like background tracks with real instrument sounds (FluidR3 GM soundfont, MIT licence) via fluidsynth.
Each style is a small arranged piece (intro-less, starts on the hook) with a melody, chords, bass and
optional drums, so it feels like a song that supports the words rather than a loop of chords.

Usage: python3 pipeline/songs.py out.wav seconds style [key] [seed]
Styles (pick to match the words):
  tender_piano   - soft hopeful piano ballad + cello + strings      (self-love, gentle reminders)
  heartbreak     - slow minor piano + strings, sad but warm          (letting go, loss, people leaving)
  hopeful_guitar - fingerpicked nylon guitar + light glockenspiel     (new chapters, growth, mornings)
  music_box      - music box + harp + pad, nostalgic lullaby          (inner child, healing, softness)
  lofi           - electric piano, bass, laid-back drums, vinyl       (relatable, everyday, coffee, chill)
  cinematic      - strings swell + low piano + timpani                (discipline, strength, comeback)
  playful        - pizzicato + marimba + claps                        (funny, light, sassy truths)
  night_rain     - rhodes + warm pad + soft rain noise, slow          (2am thoughts, overthinking, loneliness)
"""
import os, subprocess, sys, tempfile, random
import mido

SF = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
TPB = 480

# chord = (root midi note in octave 4 region, quality)
Q = {"maj": [0, 4, 7], "min": [0, 3, 7], "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "dom7": [0, 4, 7, 10],
     "add9": [0, 4, 7, 14], "sus2": [0, 2, 7], "min9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14]}

STYLES = {
    "tender_piano":   dict(bpm=72, prog=[(60, "add9"), (55, "maj"), (57, "min7"), (53, "maj7")],
                           inst={"chords": 0, "melody": 0, "bass": 42, "pad": 49}, pattern="arp8", drums=None, swing=0),
    "heartbreak":     dict(bpm=66, prog=[(57, "min"), (53, "maj7"), (60, "maj"), (55, "sus2")],
                           inst={"chords": 0, "melody": 0, "bass": 42, "pad": 49}, pattern="arp_slow", drums=None, swing=0),
    "hopeful_guitar": dict(bpm=92, prog=[(60, "maj"), (57, "min7"), (53, "maj7"), (55, "maj")],
                           inst={"chords": 24, "melody": 9, "bass": 32, "pad": 89}, pattern="travis", drums="shaker", swing=0),
    "music_box":      dict(bpm=84, prog=[(60, "maj"), (64, "min"), (53, "maj"), (55, "maj")],
                           inst={"chords": 46, "melody": 10, "bass": 46, "pad": 89}, pattern="arp8", drums=None, swing=0),
    "lofi":           dict(bpm=80, prog=[(62, "min9"), (55, "dom7"), (60, "maj7"), (57, "min7")],
                           inst={"chords": 4, "melody": 11, "bass": 33, "pad": None}, pattern="block_lofi", drums="lofi", swing=0.12),
    "cinematic":      dict(bpm=70, prog=[(57, "min"), (53, "maj"), (60, "maj"), (55, "maj")],
                           inst={"chords": 48, "melody": 48, "bass": 0, "pad": 49}, pattern="swell", drums="timpani", swing=0),
    "playful":        dict(bpm=108, prog=[(60, "maj"), (65, "maj"), (55, "maj"), (60, "maj")],
                           inst={"chords": 45, "melody": 12, "bass": 45, "pad": None}, pattern="pizz", drums="claps", swing=0),
    "night_rain":     dict(bpm=64, prog=[(57, "min9"), (53, "maj9"), (55, "add9"), (52, "min7")],
                           inst={"chords": 4, "melody": 4, "bass": 32, "pad": 89}, pattern="block_slow", drums=None, swing=0),
}


class Song:
    def __init__(self, bpm):
        self.mid = mido.MidiFile(ticks_per_beat=TPB)
        self.ev = {}  # ch -> list of (tick, msg)
        self.bpm = bpm

    def prog(self, ch, program, vol=100, reverb=70, chorus=10, pan=64):
        e = self.ev.setdefault(ch, [])
        if program is not None and ch != 9:
            e.append((0, mido.Message("program_change", channel=ch, program=program)))
        for cc, v in ((7, vol), (91, reverb), (93, chorus), (10, pan)):
            e.append((0, mido.Message("control_change", channel=ch, control=cc, value=v)))

    def note(self, ch, n, beat, dur, vel, rng, jitter=0.02):
        t0 = max(0, int((beat + rng.uniform(-jitter, jitter)) * TPB))
        t1 = t0 + max(10, int(dur * TPB))
        vel = int(max(1, min(127, vel + rng.randint(-7, 7))))
        e = self.ev.setdefault(ch, [])
        e.append((t0, mido.Message("note_on", channel=ch, note=int(n), velocity=vel)))
        e.append((t1, mido.Message("note_off", channel=ch, note=int(n), velocity=0)))

    def cc(self, ch, beat, ctl, val):
        self.ev.setdefault(ch, []).append((int(beat * TPB), mido.Message("control_change", channel=ch, control=ctl, value=int(val))))

    def save(self, path):
        tr = mido.MidiTrack(); self.mid.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm)))
        allev = sorted([x for v in self.ev.values() for x in v], key=lambda x: (x[0], 0 if x[1].type != "note_on" else 1))
        last = 0
        for t, m in allev:
            tr.append(m.copy(time=t - last)); last = t
        self.mid.save(path)


def chord_notes(root, q, key):
    return [root + key + i for i in Q[q]]


def make_motif(rng, bars=2):
    """Rhythm (beats) + scale-degree steps for a 2-bar singable motif."""
    rhythms = [[1, .5, .5, 1, 1], [1.5, .5, 1, 1], [.5, .5, 1, 1, 1], [1, 1, 1.5, .5], [2, .5, .5, 1]]
    r1, r2 = rng.choice(rhythms), rng.choice(rhythms)
    contour = [rng.choice([-2, -1, 0, 1, 2]) for _ in range(len(r1) + len(r2))]
    return [r1, r2], contour


def scale_for(key, minor):
    base = [0, 2, 4, 5, 7, 9, 11]
    return base


def nearest_scale(n, key):
    sc = [0, 2, 4, 5, 7, 9, 11]
    while (n - key) % 12 not in sc:
        n += 1
    return n


def render(out_wav, seconds, style, key=0, seed=1):
    S = STYLES[style]
    rng = random.Random(seed)
    bpm = S["bpm"]
    beats_total = seconds * bpm / 60 + 4
    bar = 4
    song = Song(bpm)
    I = S["inst"]
    song.prog(0, I["chords"], vol=92, reverb=80, chorus=20, pan=58)
    song.prog(1, I["melody"], vol=100, reverb=85, chorus=15, pan=70)
    song.prog(2, I["bass"], vol=82, reverb=50, pan=64)
    if I.get("pad") is not None:
        song.prog(3, I["pad"], vol=58, reverb=100, chorus=40, pan=64)
    song.prog(9, None, vol=78, reverb=40)
    prog = S["prog"][:]
    rot = rng.randint(0, 3) if style not in ("cinematic", "heartbreak") else 0
    prog = prog[rot:] + prog[:rot]
    rhythm, contour = make_motif(rng)
    nbars = int(beats_total // bar) + 1
    sw = S["swing"]
    mel_hi = 72
    for b in range(nbars):
        root, q = prog[b % len(prog)]
        cn = chord_notes(root, q, key)
        bb = b * bar
        intensity = min(1.0, 0.75 + 0.08 * b)  # gently builds
        p = S["pattern"]
        # ---- chords
        if p == "arp8":
            order = [0, 1, 2, 3 % len(cn), 2, 1, 0, 2] if len(cn) > 3 else [0, 1, 2, 1, 0, 1, 2, 1]
            for k in range(8):
                n = cn[order[k] % len(cn)] - 12 + (12 if k in (3, 4) else 0)
                song.note(0, n, bb + k * .5, .9, 58 * intensity + (8 if k == 0 else 0), rng)
        elif p == "arp_slow":
            for k, i in enumerate([0, 2, 1, 2]):
                song.note(0, cn[i % len(cn)] - 12 + (12 if k == 2 else 0), bb + k, 1.8, 54 * intensity, rng)
        elif p == "travis":
            for k in range(8):
                n = (cn[0] - 12) if k % 2 == 0 else cn[[1, 2, 1, 2][k // 2 % 4] % len(cn)]
                song.note(0, n, bb + k * .5, .8, (62 if k % 2 == 0 else 50) * intensity, rng, 0.015)
        elif p == "block_lofi":
            for st, d in ((0, 1.6), (2 + sw, 0.9), (3.5 + sw, 0.4)):
                for i, n in enumerate(cn):
                    song.note(0, n - 12, bb + st + i * 0.012, d, 50, rng, 0.01)
        elif p == "block_slow":
            for i, n in enumerate(cn):
                song.note(0, n - 12, bb + i * 0.03, 3.8, 48, rng, 0.01)
        elif p == "swell":
            for i, n in enumerate(cn[:3]):
                song.note(0, n - 12, bb, 4.0, 60 * intensity, rng, 0)
            song.cc(0, bb, 11, 50); song.cc(0, bb + 1.5, 11, 110); song.cc(0, bb + 3.6, 11, 70)
        elif p == "pizz":
            for k in range(4):
                song.note(0, cn[[0, 2, 1, 2][k] % len(cn)], bb + k + .5, .3, 64, rng, 0.01)
        # ---- bass
        bass = cn[0] - 24
        if p in ("pizz", "travis"):
            song.note(2, bass, bb, .9, 70, rng); song.note(2, bass + 7, bb + 2, .9, 62, rng)
        elif p == "block_lofi":
            song.note(2, bass, bb, 1.4, 78, rng); song.note(2, bass, bb + 2.5 + sw, .5, 64, rng); song.note(2, bass + 7, bb + 3 + sw, .8, 60, rng)
        elif p == "swell":
            song.note(2, bass, bb, 3.9, 70, rng); song.note(2, bass - 12 if bass - 12 > 24 else bass, bb, 3.9, 62, rng)
        else:
            song.note(2, bass, bb, 3.9, 64, rng)
        # ---- pad
        if I.get("pad") is not None:
            for n in cn[:3]:
                song.note(3, n, bb, 4.0, 46, rng, 0)
        # ---- melody: motif (2 bars), answered with variation
        half = b % 2
        rh = rhythm[half]
        cpos = 0
        prev = nearest_scale(mel_hi + key + (cn[0] - 60) % 12 - (12 if (cn[0] - 60) % 12 > 6 else 0), key)
        for k, d in enumerate(rh):
            step = contour[(k + half * len(rhythm[0])) % len(contour)]
            if b % 4 >= 2 and k == len(rh) - 1:
                step = -abs(step) - 1  # answer phrase resolves downward
            target = prev + step * 2
            # pull strong beats onto chord tones
            if cpos in (0, 2):
                pcs = [(n - target) % 12 for n in cn]
                best = min(cn, key=lambda n: min(abs((n % 12) - (target % 12)), 12 - abs((n % 12) - (target % 12))))
                target = target + (((best % 12) - (target % 12) + 6) % 12 - 6)
            target = nearest_scale(target, key)
            target = max(mel_hi - 7 + key, min(mel_hi + 9 + key, target))
            if p == "pizz" or style == "music_box" or rng.random() > 0.08:
                song.note(1, target, bb + cpos + (sw if cpos % 1 else 0), d * 0.92, 70 + (8 if cpos == 0 else 0), rng)
            prev = target
            cpos += d
            if cpos >= 4: break
        # ---- drums
        dr = S["drums"]
        if dr == "lofi":
            for q4 in range(4):
                if q4 in (0,) or (q4 == 2 and b % 2): song.note(9, 36, bb + q4 + (0.5 if q4 == 2 else 0), .2, 82, rng, 0.01)
                if q4 in (1, 3): song.note(9, 37, bb + q4, .2, 70, rng, 0.01)
                for e in (0, .5 + sw):
                    song.note(9, 42, bb + q4 + e, .1, 44 if e else 54, rng, 0.01)
        elif dr == "shaker":
            for k in range(8):
                song.note(9, 70, bb + k * .5, .1, 36 if k % 2 else 48, rng, 0.01)
        elif dr == "claps" and b >= 1:
            song.note(9, 39, bb + 1, .1, 64, rng); song.note(9, 39, bb + 3, .1, 64, rng)
            for k in range(4): song.note(9, 42, bb + k + .5, .1, 40, rng)
        elif dr == "timpani" and b % 2 == 0:
            song.note(9, 41, bb, 1, 70, rng); song.note(9, 41, bb + 3.5, .5, 50, rng)
    wk = tempfile.mkdtemp()
    mid = os.path.join(wk, "s.mid"); raw = os.path.join(wk, "raw.wav")
    song.save(mid)
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.55", "-r", "44100", "-F", raw, SF, mid], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    af = [f"atrim=0:{seconds}", "afade=t=in:d=0.08", f"afade=t=out:st={max(0, seconds - 1.2)}:d=1.2"]
    extra_in = []
    if style == "lofi":
        af = ["lowpass=f=5500", "acrusher=bits=12:mix=0.15"] + af
    fil = ",".join(af + ["loudnorm=I=-16:TP=-1.5:LRA=9"])
    if style in ("lofi", "night_rain"):
        noise = "pink" if style == "night_rain" else "brown"
        amp = 0.035 if style == "night_rain" else 0.012
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw, "-f", "lavfi", "-i", f"anoisesrc=c={noise}:a={amp}:d={seconds + 1}",
               "-filter_complex", f"[1]highpass=f=1500,lowpass=f=7000[n];[0][n]amix=inputs=2:weights=1 1:normalize=0,{fil}",
               "-ar", "44100", "-ac", "2", out_wav]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", fil, "-ar", "44100", "-ac", "2", out_wav]
    subprocess.run(cmd, check=True)
    return out_wav


if __name__ == "__main__":
    out, secs, style = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    key = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    render(out, secs, style, key, seed)
    print("ok", out)
