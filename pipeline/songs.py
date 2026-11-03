"""Composed, sample-based background music for the quote Reels (no voiceover).

Real recorded instruments: Salamander Grand Piano (3 velocity layers), cello, violin, harp, nylon and
steel guitar, flute, contrabass (tonejs-instruments). FluidR3 GM via fluidsynth is used for the extra
colours (electric piano, music box, pizzicato, marimba, drums). The samples are fetched by
pipeline/setup.sh into .samples/ (not committed). The sample packages are MIT; credits are in README.md.

Every track is a short composed song cut to fit the Reel: 4 chord "slots" (2 beats each) that form a
complete phrase (question -> answer), then a final chord that rings out and resolves. The tempo is fitted
so the phrase lands exactly on the Reel length, and the melody is hand-written per style (several
variations each), so it sounds like music with a hook, not a random loop.

Usage: python3 pipeline/songs.py out.wav seconds style [key -3..3] [seed]
Styles (choose by the feeling of the words):
  tender_piano   gentle hopeful piano ballad, cello enters later        self-love, soft reminders
  heartbreak     minor piano + cello + violin swell                     letting go, people leaving, closure
  hopeful_guitar fingerpicked nylon guitar + flute melody               growth, new chapters, mornings
  music_box      harp + music box lullaby                               inner child, healing, nostalgia
  lofi           electric piano, soft piano melody, bass, drums, vinyl  relatable, coffee, everyday
  cinematic      string section, low piano, timpani                     discipline, strength, comebacks
  playful        pizzicato + marimba + claps                            funny, sassy, light truths
  night_rain     sparse piano + cello + rain                            2am thoughts, overthinking, loneliness
  ostinato       flowing modern-classical piano figure + cello + violin  deep reflections, book lines, "read this"
  film_score     piano ostinato + full strings + timpani, big ending      empowerment, comebacks, "you made it"
  acoustic_pop   strummed guitar, bass, claps, flute hook                 happy, friendship, love, upbeat mornings
  rnb_soul       neo-soul electric piano, bass, soft groove               confident, sassy, soft-life, self-love
"""
import glob, os, random, re, subprocess, sys, tempfile
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(os.path.dirname(HERE), ".samples")
SR = 44100
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

# --------------------------------------------------------------------------- sample loading
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def name_to_midi(n):
    m = re.match(r"^([A-G])(s|#)?(-?\d)$", n)
    if not m:
        return None
    return 12 * (int(m.group(3)) + 1) + NOTE[m.group(1)] + (1 if m.group(2) else 0)


def decode(path):
    cache = os.path.join(SAMPLES, "cache", re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.relpath(path, SAMPLES)) + ".npy")
    if os.path.exists(cache):
        return np.load(cache)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    nz = np.nonzero(np.abs(a) > 0.002)[0]
    if len(nz):
        a = a[max(0, nz[0] - 30):]  # trim encoder silence, keep the attack
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, a)
    return a


class Instrument:
    def __init__(self, folder_glob, layer=None, max_len=None, release=0.35, attack=0.0):
        self.layers = {}  # layer -> {midi: path}
        for d in glob.glob(os.path.join(SAMPLES, "dl", folder_glob)):
            for f in glob.glob(os.path.join(d, "**", "*.mp3"), recursive=True):
                base = os.path.basename(f)[:-4]
                if " " in base:
                    continue
                m = re.match(r"^(.+?)v(\d+)$", base)
                lay, nm = (int(m.group(2)), m.group(1)) if m else (0, base)
                mi = name_to_midi(nm)
                if mi is not None:
                    self.layers.setdefault(lay, {})[mi] = f
        if not self.layers:
            raise RuntimeError(f"no samples for {folder_glob}; run pipeline/setup.sh")
        self.keys = sorted(self.layers)
        self.max_len, self.release, self.attack = max_len, release, attack
        self._cache = {}

    def sample(self, midi, vel):
        lay = self.keys[min(len(self.keys) - 1, int(vel / 128 * len(self.keys)))]
        notes = self.layers[lay]
        src = min(notes, key=lambda n: (abs(n - midi), n > midi))
        key = (lay, src)
        if key not in self._cache:
            self._cache[key] = decode(notes[src])
        return self._cache[key], src

    def render(self, midi, dur, vel):
        a, src = self.sample(midi, vel)
        ratio = 2 ** ((midi - src) / 12)
        n_out = int(min(len(a) / ratio, (dur + self.release + 0.05) * SR))
        if self.max_len:
            n_out = min(n_out, int(self.max_len * SR))
        idx = np.arange(n_out) * ratio
        out = np.interp(idx, np.arange(len(a)), a).astype(np.float32)
        env = np.ones(n_out, np.float32)
        r0 = int(dur * SR)
        if r0 < n_out:
            rl = n_out - r0
            env[r0:] = np.exp(-np.linspace(0, 6, rl))
        if self.attack:
            na = min(n_out, int(self.attack * SR))
            env[:na] *= np.linspace(0, 1, na) ** 1.5
        return out * env * (vel / 127) ** 1.6


_INST = {}


def inst(name):
    if name not in _INST:
        spec = {
            "piano": ("audio-samples-piano-mp3-velocity*", dict(release=0.45)),
            "cello": ("tonejs-instrument-cello-mp3*", dict(release=0.5, attack=0.18)),
            "violin": ("tonejs-instrument-violin-mp3*", dict(release=0.6, attack=0.25)),
            "harp": ("tonejs-instrument-harp-mp3*", dict(release=1.2)),
            "nylon": ("tonejs-instrument-guitar-nylon-mp3*", dict(release=0.6)),
            "guitar": ("tonejs-instrument-guitar-acoustic-mp3*", dict(release=0.6)),
            "flute": ("tonejs-instrument-flute-mp3*", dict(release=0.25, attack=0.06)),
            "bass": ("tonejs-instrument-contrabass-mp3*", dict(release=0.3, attack=0.03)),
        }[name]
        _INST[name] = Instrument(spec[0], **spec[1])
    return _INST[name]


# --------------------------------------------------------------------------- harmony
MAJ = [0, 2, 4, 5, 7, 9, 11]
CH = {  # chord name -> (scale degree of root, intervals)
    "I": (0, [0, 4, 7]), "Imaj7": (0, [0, 4, 7, 11]), "Iadd9": (0, [0, 4, 7, 14]),
    "ii": (1, [0, 3, 7]), "ii7": (1, [0, 3, 7, 10]), "iii": (2, [0, 3, 7]), "iii7": (2, [0, 3, 7, 10]),
    "IV": (3, [0, 4, 7]), "IVmaj7": (3, [0, 4, 7, 11]), "IVmaj9": (3, [0, 4, 7, 11, 14]),
    "V": (4, [0, 4, 7]), "V7": (4, [0, 4, 7, 10]), "Vsus": (4, [0, 5, 7]),
    "vi": (5, [0, 3, 7]), "vi7": (5, [0, 3, 7, 10]), "vi9": (5, [0, 3, 7, 10, 14]),
}


def deg(d, tonic):
    """Scale degree (0 = tonic, 7 = octave, negatives below) -> midi."""
    o, r = divmod(d, 7)
    return tonic + 12 * o + MAJ[r]


def chord(name, tonic, base=48):
    r, iv = CH[name]
    root = tonic + MAJ[r]
    while root < base:
        root += 12
    while root >= base + 12:
        root -= 12
    return root, [root + i for i in iv]


def voice_lead(prev, notes, lo=55, hi=72):
    """Choose an inversion of `notes` (pitch classes) close to the previous voicing."""
    pcs = sorted(set(n % 12 for n in notes))
    best, bestc = None, 1e9
    for inv in range(len(pcs)):
        for octv in (48, 60):
            v = []
            for i in range(len(pcs)):
                n = octv + pcs[(i + inv) % len(pcs)]
                while v and n <= v[-1]:
                    n += 12
                v.append(n)
            if v[0] < lo or v[-1] > hi + 7:
                continue
            c = sum(abs(a - b) for a, b in zip(sorted(v), sorted(prev))) if prev else abs(sum(v) / len(v) - 62)
            if c < bestc:
                best, bestc = v, c
    return best or [60 + p for p in pcs]


# --------------------------------------------------------------------------- songs
# Progression = 4 slots + final ringing chord. Melodies: per slot list of (scale degree, beats), 2 beats per slot,
# plus the final note. Strong beats sit on chord tones; phrase = question (slots 1-2) and answer (3-4).
SONGS = {
    "tender_piano": dict(bpm=(60, 84), prog=["Iadd9", "V", "vi", "IV", "I"], mel=[
        [[(2, .5), (4, .5), (7, 1)], [(6, 1), (4, 1)], [(5, .5), (4, .5), (2, 1)], [(3, 1), (1, .5), (2, .5)], [(0, 2)]],
        [[(4, 1.5), (5, .5)], [(4, 1), (1, 1)], [(2, 1.5), (4, .5)], [(5, 1), (3, 1)], [(2, 2)]],
        [[(7, 1), (6, .5), (7, .5)], [(8, 1), (6, 1)], [(7, .5), (6, .5), (4, 1)], [(5, .5), (3, .5), (5, 1)], [(4, 2)]]]),
    "heartbreak": dict(bpm=(56, 78), prog=["vi", "IV", "I", "V", "vi"], mel=[
        [[(7, 1), (6, .5), (5, .5)], [(5, 1), (3, 1)], [(4, 1.5), (2, .5)], [(1, .5), (2, .5), (4, 1)], [(5, 2)]],
        [[(2, 1), (4, .5), (2, .5)], [(3, 1.5), (2, .5)], [(0, 1), (2, 1)], [(1, 1), (-1, 1)], [(-2, 2)]],
        [[(5, 1.5), (7, .5)], [(7, 1), (5, 1)], [(4, 1.5), (2, .5)], [(4, .5), (6, .5), (8, 1)], [(7, 2)]]]),
    "hopeful_guitar": dict(bpm=(70, 96), prog=["I", "IV", "vi", "V", "I"], mel=[
        [[(4, .5), (4, .5), (2, .5), (4, .5)], [(5, 1), (3, .5), (5, .5)], [(2, 1), (0, 1)], [(1, .5), (2, .5), (1, 1)], [(0, 2)]],
        [[(7, .5), (6, .5), (4, 1)], [(5, .5), (7, .5), (5, 1)], [(4, .5), (2, .5), (4, 1)], [(1, 1.5), (2, .5)], [(2, 2)]]]),
    "music_box": dict(bpm=(66, 90), prog=["I", "iii", "IV", "V", "I"], mel=[
        [[(7, .5), (4, .5), (2, .5), (4, .5)], [(6, .5), (4, .5), (2, 1)], [(5, .5), (3, .5), (7, 1)], [(6, .5), (8, .5), (4, 1)], [(7, 2)]],
        [[(9, 1), (7, 1)], [(6, .5), (4, .5), (6, 1)], [(5, 1), (7, 1)], [(8, .5), (6, .5), (4, 1)], [(7, 2)]]]),
    "lofi": dict(bpm=(68, 88), prog=["ii7", "V7", "Imaj7", "vi7", "Imaj7"], mel=[
        [[(5, .75), (3, .25), (1, 1)], [(3, .5), (1, .5), (-1, 1)], [(2, 1.5), (6, .5)], [(4, 1), (2, 1)], [(6, 2)]],
        [[(7, .5), (5, .5), (3, 1)], [(3, .75), (4, .25), (6, 1)], [(4, 1), (2, 1)], [(4, .5), (5, .5), (2, 1)], [(2, 2)]]]),
    "cinematic": dict(bpm=(56, 76), prog=["vi", "IV", "I", "V", "vi"], mel=[
        [[(2, 2)], [(3, 1), (5, 1)], [(4, 2)], [(6, 1), (8, 1)], [(7, 2)]],
        [[(5, 1.5), (4, .5)], [(5, 2)], [(7, 1.5), (6, .5)], [(6, 1), (4, 1)], [(5, 2)]]]),
    "playful": dict(bpm=(84, 112), prog=["I", "IV", "V", "I", "I"], mel=[
        [[(0, .5), (2, .5), (4, .5), (7, .5)], [(5, .5), (3, .5), (5, .5), (3, .5)], [(4, .5), (6, .5), (8, .5), (6, .5)], [(7, .5), (4, .5), (7, 1)], [(7, 1)]],
        [[(4, .5), (2, .5), (4, .5), (7, .5)], [(5, .75), (5, .25), (3, 1)], [(1, .5), (4, .5), (6, .5), (4, .5)], [(2, .5), (1, .5), (0, 1)], [(0, 1)]]]),
    "ostinato": dict(bpm=(64, 86), prog=["vi", "IV", "I", "V", "vi"], mel=[
        [[(2, 2)], [(3, 1), (5, 1)], [(4, 1.5), (2, .5)], [(1, 2)], [(0, 2)]],
        [[(7, 1.5), (6, .5)], [(5, 2)], [(4, 1), (7, 1)], [(6, 2)], [(5, 2)]]]),
    "film_score": dict(bpm=(60, 80), prog=["vi", "IV", "I", "V", "I"], mel=[
        [[(2, 1.5), (4, .5)], [(5, 2)], [(4, 1), (7, 1)], [(6, 1), (8, 1)], [(7, 2)]],
        [[(5, 2)], [(5, 1), (7, 1)], [(7, 1.5), (9, .5)], [(8, 2)], [(7, 2)]]]),
    "acoustic_pop": dict(bpm=(88, 120), prog=["I", "V", "vi", "IV", "I"], mel=[
        [[(4, .5), (4, .5), (5, .5), (4, .5)], [(4, .5), (6, .5), (4, 1)], [(2, .5), (2, .5), (4, .5), (2, .5)], [(3, .5), (5, .5), (3, .5), (1, .5)], [(2, 2)]],
        [[(7, .5), (7, .5), (6, .5), (4, .5)], [(6, 1), (4, 1)], [(5, .5), (4, .5), (2, 1)], [(3, .5), (2, .5), (0, 1)], [(0, 2)]]]),
    "rnb_soul": dict(bpm=(64, 82), prog=["IVmaj7", "iii7", "vi9", "ii7", "Imaj7"], mel=[
        [[(5, 1), (4, .5), (2, .5)], [(4, 1.5), (6, .5)], [(4, .5), (2, .5), (0, 1)], [(1, .5), (3, .5), (5, 1)], [(4, 2)]],
        [[(7, .75), (5, .25), (4, 1)], [(6, .5), (4, .5), (2, 1)], [(2, 1), (4, 1)], [(3, .75), (1, .25), (0, 1)], [(2, 2)]]]),
    "night_rain": dict(bpm=(54, 70), prog=["vi9", "IVmaj9", "Iadd9", "Vsus", "vi"], mel=[
        [[(9, 1.5), (7, .5)], [(5, 2)], [(4, 1), (2, 1)], [(1, 2)], [(2, 2)]],
        [[(4, 1), (2, 1)], [(3, 1.5), (5, .5)], [(4, 2)], [(4, .5), (3, .5), (1, 1)], [(0, 2)]]]),
}


def reverb_ir(secs, damp, seed):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    irs = []
    for ch in range(2):
        x = rng.standard_normal(n) * np.exp(-t * 6.5 / secs)
        x = sosfilt(butter(1, damp, "low", fs=SR, output="sos"), x)
        x[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
        irs.append(x / np.sqrt(np.sum(x ** 2)))
    return irs


class Mix:
    def __init__(self, seconds):
        self.n = int((seconds + 4) * SR)
        self.bus = {}

    def add(self, busname, audio, t, pan=0.0, gain=1.0):
        b = self.bus.setdefault(busname, np.zeros((2, self.n), np.float32))
        i = int(t * SR)
        if i >= self.n or i < 0:
            return
        j = min(self.n, i + len(audio))
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        b[0, i:j] += audio[:j - i] * gain * l * 1.41
        b[1, i:j] += audio[:j - i] * gain * r * 1.41


def fluid_stem(notes, programs, seconds, bpm):
    """Render notes [(ch, midi, start_s, dur_s, vel)] with FluidR3; returns stereo array."""
    import mido
    mf = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack(); mf.tracks.append(tr)
    tempo = mido.bpm2tempo(120)
    tr.append(mido.MetaMessage("set_tempo", tempo=tempo))
    ev = []
    for ch, prog in programs.items():
        if ch != 9:
            ev.append((0, mido.Message("program_change", channel=ch, program=prog)))
        ev.append((0, mido.Message("control_change", channel=ch, control=91, value=30)))
    tick = lambda s: int(s * 960)
    for ch, m, st, du, v in notes:
        ev.append((tick(st), mido.Message("note_on", channel=ch, note=int(m), velocity=int(max(1, min(127, v))))))
        ev.append((tick(st + du), mido.Message("note_off", channel=ch, note=int(m), velocity=0)))
    ev.sort(key=lambda e: (e[0], e[1].type == "note_on"))
    last = 0
    for t, msg in ev:
        tr.append(msg.copy(time=t - last)); last = t
    wk = tempfile.mkdtemp()
    mid, wav = os.path.join(wk, "f.mid"), os.path.join(wk, "f.wav")
    mf.save(mid)
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.6", "-r", str(SR), "-F", wav, SF2, mid], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()


def render(out_wav, seconds, style, key=0, seed=1):
    S = SONGS[style]
    rng = random.Random(seed)
    nprg = np.random.default_rng(seed)
    tonic = 60 + key  # C4 + key
    ring = 1.6
    lo, hi = S["bpm"]
    bpm = 120 * 4 / max(1.0, seconds - ring)  # 4 slots x 2 beats fill the Reel, last chord rings
    slots = 4
    while bpm < lo and slots < 8:  # long Reel: repeat the middle of the phrase
        slots += 2
        bpm = 120 * slots / max(1.0, seconds - ring)
    bpm = max(lo, min(hi + 10, bpm))
    beat = 60 / bpm
    prog = S["prog"][:4]
    if slots > 4:
        prog = prog[:2] + prog[2:4] * ((slots - 2) // 2)
    prog = prog + [S["prog"][4]]
    mel = rng.choice(S["mel"])
    mel = mel[:2] + mel[2:4] * ((slots - 2) // 2) + [mel[4]]
    mx = Mix(seconds)
    fl_notes, fl_prog = [], {}
    H = lambda: rng.uniform(-0.012, 0.012)  # humanise timing
    V = lambda v: max(10, min(127, v + rng.randint(-6, 6)))
    prev = None
    nsl = len(prog)
    for si, cname in enumerate(prog):
        t0 = si * 2 * beat + (0.12 * beat if si == len(prog) - 1 else 0)  # small ritardando into the last chord
        last = si == nsl - 1
        slot_len = (2 * beat) if not last else ring + 0.6
        root, notes = chord(cname, tonic - 12, base=36)
        vo = voice_lead(prev, notes); prev = vo
        dyn = [0.97, 0.94, 1.0, 0.95, 0.9, 1.0, 0.95, 0.9][min(si, 7)] if not last else 0.85
        # ---------------- accompaniment
        if style in ("tender_piano", "heartbreak", "night_rain"):
            P = inst("piano")
            mx.add("piano", P.render(root, slot_len + 0.2, V(int(62 * dyn))), t0 + H(), -0.15)
            mx.add("piano", P.render(root + 12 if style != "night_rain" else root + 7, slot_len, V(int(50 * dyn))), t0 + H(), -0.1)
            if style == "tender_piano":
                pat = [vo[0], vo[1], vo[-1], vo[1]] if not last else [vo[0], vo[1], vo[-1]]
                for k, n in enumerate(pat):
                    mx.add("piano", P.render(n, slot_len - k * beat * .5, V(int(48 * dyn))), t0 + k * beat * .5 + H(), 0.15)
            elif style == "heartbreak":
                for k, n in enumerate([vo[0], vo[-1]] if not last else [vo[0]]):
                    mx.add("piano", P.render(n, slot_len - k * beat, V(int(46 * dyn))), t0 + k * beat + H(), 0.15)
                for k, n in enumerate(vo[1:3]):
                    mx.add("piano", P.render(n, slot_len - k * beat, V(int(40 * dyn))), t0 + (k + .5) * beat + H(), 0.2)
            else:
                for k, n in enumerate(vo[:3]):
                    mx.add("piano", P.render(n, slot_len, V(int(34 * dyn))), t0 + k * 0.06 + H(), 0.1)
            if style == "tender_piano":
                mx.add("strings", inst("cello").render(root - 12 + 12, slot_len, V(70)), t0, -0.35, 0.55)
            if style == "heartbreak":
                mx.add("strings", inst("cello").render(root, slot_len, V(78)), t0, -0.4, 0.6)
                if si >= 2:
                    mx.add("strings", inst("violin").render(vo[-1] + 12, slot_len, V(64 + 8 * si)), t0, 0.4, 0.4)
            if style == "night_rain" and si % 2 == 0:
                mx.add("strings", inst("cello").render(root, slot_len * 2, V(62)), t0, -0.3, 0.5)
        elif style == "hopeful_guitar":
            G = inst("nylon")
            pick = [root, vo[1], vo[-1], vo[1], root + 7, vo[1], vo[-1], vo[0]] if not last else [root, vo[1], vo[-1], vo[0] + 12]
            for k, n in enumerate(pick):
                mx.add("gtr", G.render(n, 1.2 if not last else ring, V(int((66 if k % 4 == 0 else 52) * dyn))), t0 + k * beat / 4 + H() * .5, 0.25 if k % 2 else -0.25)
            mx.add("bass", inst("bass").render(root - 12, slot_len * .9, V(70)), t0, 0, 0.6)
            for k in range(4 if not last else 0):
                fl_notes.append((9, 70, t0 + k * beat / 2, 0.05, 30 + 12 * (k % 2 == 0)))
            fl_prog[9] = 0
        elif style == "music_box":
            Hp = inst("harp")
            for k, n in enumerate([root, vo[0], vo[1], vo[-1]] if not last else [root, vo[0], vo[1], vo[-1], vo[0] + 12]):
                mx.add("harp", Hp.render(n, slot_len, V(60)), t0 + k * beat * (0.5 if not last else 0.12) + H(), -0.2 + 0.1 * k)
        elif style == "lofi":
            for n in vo:
                fl_notes.append((0, n, t0 + 0.01 * (n % 3), (1.6 if not last else ring) * beat, V(52)))
                if not last:
                    fl_notes.append((0, n, t0 + 1.5 * beat, 0.4 * beat, V(38)))
            fl_notes.append((1, root - 12, t0, 1.2 * beat, V(84)))
            if not last:
                fl_notes.append((1, root - 12 + 7, t0 + 1.5 * beat, 0.4 * beat, V(70)))
                fl_notes.append((9, 36, t0, .1, V(84))); fl_notes.append((9, 37, t0 + beat, .1, V(66)))
                for k in range(4):
                    fl_notes.append((9, 42, t0 + k * beat / 2 + (0.06 * beat if k % 2 else 0), .05, V(42 if k % 2 else 52)))
            fl_prog.update({0: 4, 1: 33, 9: 0})
        elif style == "cinematic":
            for k, n in enumerate(vo):
                mx.add("strings", inst("violin" if n >= 60 else "cello").render(n + (12 if n < 60 else 0), slot_len, V(int(70 * dyn + 6 * si))), t0 + 0.02 * k, -0.4 + 0.3 * k, 0.45)
            mx.add("strings", inst("cello").render(root, slot_len, V(84)), t0, -0.3, 0.7)
            mx.add("piano", inst("piano").render(root - 12, slot_len, V(90)), t0, 0, 0.8)
            mx.add("piano", inst("piano").render(root, slot_len, V(70)), t0, 0, 0.6)
            if si % 2 == 0 or last:
                fl_notes.append((9, 41, t0, .5, V(80 if not last else 96))); fl_prog[9] = 0
        elif style in ("ostinato", "film_score"):
            P = inst("piano")
            mx.add("piano", P.render(root, slot_len + 0.3, V(int(64 * dyn))), t0 + H(), -0.2)
            mx.add("piano", P.render(root + 12, slot_len + 0.3, V(int(48 * dyn))), t0 + H(), -0.15)
            fig = [root + 12, vo[1], vo[-1], vo[1], vo[0] + 12, vo[1], vo[-1], vo[1]] if not last else [root + 12, vo[1], vo[-1], vo[0] + 12]
            step = beat / 4 if style == "ostinato" else beat / 2
            fig = fig if style == "ostinato" else fig[:4]
            for k, n in enumerate(fig):
                acc_ = 1.15 if k % 4 == 0 else 1.0
                mx.add("piano", P.render(n, step * 1.6 if not last else slot_len, V(int(44 * dyn * acc_))), t0 + k * step + H() * .5, 0.2)
            if True:
                mx.add("strings", inst("cello").render(root, slot_len, V(int(70 + 4 * si))), t0, -0.35, 0.6)
            if si >= 2 or last:
                mx.add("strings", inst("violin").render(vo[-1] + 12, slot_len, V(int(58 + 7 * si))), t0, 0.4, 0.45)
            if style == "film_score":
                for n in vo[:3]:
                    mx.add("strings", inst("violin" if n >= 55 else "cello").render(n + 12, slot_len, V(int(52 + 8 * si))), t0 + 0.03, 0.1, 0.3)
                if si % 2 == 0 or last:
                    fl_notes.append((9, 41, t0, .5, V(70 if not last else 100)))
                    if last:
                        fl_notes.append((9, 49, t0, 2.0, V(55)))
                fl_prog[9] = 0
        elif style == "acoustic_pop":
            G = inst("guitar")
            strum = [(0, 1, 78), (.5, -1, 50), (1, 1, 70), (1.5, -1, 56)] if not last else [(0, 1, 82)]
            shape = [root] + vo
            for bt_, dirn, vv in strum:
                notes_ = shape if dirn > 0 else shape[::-1][:3]
                for i, n in enumerate(notes_):
                    mx.add("gtr", G.render(n, (beat * .55) if not last else ring, V(int(vv * dyn))), t0 + bt_ * beat + i * 0.014 + H() * .3, -0.3 + 0.12 * i, 0.8)
            mx.add("bass", inst("bass").render(root - 12, beat * .9 if not last else ring, V(78)), t0, 0, 0.7)
            if not last:
                mx.add("bass", inst("bass").render(root - 12 + 7, beat * .8, V(70)), t0 + beat, 0, 0.6)
                fl_notes += [(9, 39, t0 + beat, .05, V(64)), (9, 36, t0, .1, V(70)), (9, 42, t0 + .5 * beat, .05, V(40)), (9, 42, t0 + 1.5 * beat, .05, V(40))]
            fl_prog[9] = 0
        elif style == "rnb_soul":
            for k, (st_, du_, vv) in enumerate([(0, 1.4, 54), (1.5, .4, 46)] if not last else [(0, 3, 54)]):
                for i, n in enumerate(vo):
                    fl_notes.append((0, n, t0 + st_ * beat + 0.012 * i, du_ * beat if not last else ring, V(vv)))
            fl_notes.append((1, root - 12, t0, 0.9 * beat, V(86)))
            if not last:
                fl_notes += [(1, root - 12 + 12, t0 + 1.25 * beat, .2 * beat, V(70)), (1, root - 12 + 10, t0 + 1.5 * beat, .4 * beat, V(72)),
                             (9, 36, t0, .1, V(80)), (9, 36, t0 + 1.25 * beat, .1, V(60)), (9, 37, t0 + beat, .1, V(72))]
                for k in range(8):
                    fl_notes.append((9, 42, t0 + k * beat / 4 + (0.03 if k % 2 else 0), .04, V(30 if k % 2 else 44)))
            fl_prog.update({0: 4, 1: 33, 9: 0})
        elif style == "playful":
            for k, n in enumerate([root, vo[-1], vo[0], vo[-1]] if not last else [root, vo[0], vo[-1]]):
                fl_notes.append((0, n if k else n - 12, t0 + k * beat / 2, 0.2, V(78)))
            if not last:
                fl_notes += [(9, 39, t0 + beat, .05, V(70)), (9, 42, t0 + beat / 2, .05, V(40)), (9, 42, t0 + 1.5 * beat, .05, V(40))]
            fl_prog.update({0: 45, 9: 0})
        # ---------------- melody
        bt = 0.0
        for d, b in mel[si]:
            m = deg(d, tonic + (12 if style in ("music_box",) else 0))
            st = t0 + bt * beat + H()
            du = b * beat * (0.92 if not last else 1) + (ring if last else 0)
            vm = V(int((80 if bt == 0 else 70) * dyn))
            if style in ("tender_piano", "heartbreak", "night_rain"):
                mx.add("lead", inst("piano").render(m + (12 if style == "night_rain" else 0), du + 0.3, vm), st, 0.05)
            elif style == "hopeful_guitar":
                mx.add("lead", inst("flute").render(m + 12, du, V(int(66 * dyn))), st, 0.1, 0.5)
            elif style == "music_box":
                fl_notes.append((2, m, st, du, vm)); fl_prog[2] = 10
            elif style == "lofi":
                mx.add("lead", inst("piano").render(m + 12, du + 0.3, V(int(58 * dyn))), st, 0.1)
            elif style == "cinematic":
                mx.add("lead", inst("violin").render(m + 12, du, V(int(86 * dyn))), st, 0.15, 0.8)
            elif style in ("ostinato", "film_score"):
                inst_m = "piano" if style == "ostinato" else "violin"
                mx.add("lead", inst(inst_m).render(m + 12, du + (0.3 if inst_m == "piano" else 0), V(int((72 if inst_m == "piano" else 84) * dyn))), st, 0.05, 1.0 if inst_m == "piano" else 0.75)
            elif style == "acoustic_pop":
                mx.add("lead", inst("flute").render(m + 12, du, V(int(70 * dyn))), st, 0.15, 0.55)
            elif style == "rnb_soul":
                mx.add("lead", inst("piano").render(m + 12, du + 0.3, V(int(62 * dyn))), st, 0.1)
            elif style == "playful":
                fl_notes.append((2, m + 12, st, min(du, 0.25), vm)); fl_prog[2] = 12
            bt += b
    # --------------------------------------------------------------------- mixing
    total = mx.n
    out = np.zeros((2, total), np.float32)
    rev = {"piano": .32, "lead": .38, "strings": .45, "gtr": .25, "bass": .1, "harp": .4, "fluid": .2}
    irs = reverb_ir(2.6 if style in ("heartbreak", "night_rain", "cinematic", "music_box", "ostinato", "film_score") else 1.8, 5000, seed)
    wet = np.zeros_like(out)
    for name, b in mx.bus.items():
        out += b
        wet += b * rev.get(name, .25)
    if fl_notes:
        fs = fluid_stem(fl_notes, fl_prog, seconds, bpm)
        fs = fs[:, :total] if fs.shape[1] >= total else np.pad(fs, ((0, 0), (0, total - fs.shape[1])))
        g = 1.3
        out += fs * g
        wet += fs * g * rev["fluid"]
    for c in range(2):
        out[c] += fftconvolve(wet[c], irs[c])[:total].astype(np.float32) * 1.4
    out = sosfilt(butter(2, 45, "high", fs=SR, output="sos"), out, axis=1)
    if style == "lofi":
        out = sosfilt(butter(2, 4800, "low", fs=SR, output="sos"), out, axis=1)
    if style in ("lofi", "night_rain"):
        rr = np.random.default_rng(seed)
        noise = rr.standard_normal((2, total)).astype(np.float32)
        if style == "night_rain":
            noise = sosfilt(butter(2, [800, 6000], "band", fs=SR, output="sos"), noise, axis=1) * 0.02
        else:
            crack = np.zeros((2, total), np.float32)
            idx = rr.integers(0, total, int(seconds * 25))
            crack[:, idx] = rr.standard_normal(len(idx)) * 0.15
            noise = sosfilt(butter(2, 3000, "high", fs=SR, output="sos"), crack, axis=1)
        out = out + noise
    # gentle bus compression (RMS, slow)
    rms = np.sqrt(sosfilt(butter(1, 4, "low", fs=SR, output="sos"), (out ** 2).mean(0)) + 1e-9)
    thr = np.percentile(rms, 70)
    gain = np.where(rms > thr, (thr / rms) ** 0.35, 1.0)
    out = out * gain
    n = int(seconds * SR)
    out = out[:, :n]
    fade = int(0.9 * SR)
    out[:, -fade:] *= np.linspace(1, 0, fade) ** 1.5
    out[:, :200] *= np.linspace(0, 1, 200)
    out /= max(1e-6, np.abs(out).max())
    wk = tempfile.mkdtemp()
    tmp = os.path.join(wk, "pre.wav")
    import wave
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out.T * 0.9 * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", str(SR), out_wav],
                   check=True)
    return out_wav


if __name__ == "__main__":
    out, secs, style = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    key = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    render(out, secs, style, key, seed)
    print("ok", out)
