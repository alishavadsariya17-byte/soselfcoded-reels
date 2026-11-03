"""Background music for short silent-text Reels.
Usage: python3 lofi.py out.wav seconds mood key seed
mood: warm (lo-fi keys + soft beat + vinyl), dreamy (piano + pad, no drums), dark (minor piano + low pulse)
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

OUT = sys.argv[1]
D = float(sys.argv[2]) if len(sys.argv) > 2 else 12
MOOD = sys.argv[3] if len(sys.argv) > 3 else "warm"
KEY = int(sys.argv[4]) if len(sys.argv) > 4 else 0
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 7
SR = 44100
rng = np.random.default_rng(SEED)
hz = lambda m: 440 * 2 ** ((m + KEY - 69) / 12)
lp = lambda x, f: sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
hp = lambda x, f: sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)


def T(dur):
    return np.arange(int(dur * SR)) / SR


def keys(f, dur, v):  # rhodes-ish electric piano
    t = T(dur)
    x = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3))
    x += 0.2 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t * 4)
    x *= np.exp(-t * 1.1) * (1 - np.exp(-t * 300)) * (1 + 0.12 * np.sin(2 * np.pi * 4.5 * t))
    return x * v


def piano(f, dur, v):
    t = T(dur)
    x = sum(a * np.sin(2 * np.pi * f * k * 1.0006 ** k * t) * np.exp(-t * (0.8 + 0.8 * k)) for k, a in enumerate([1, .35, .15, .06], 1))
    return lp(x * (1 - np.exp(-t * 220)), 1900) * v


def pad(fs, dur, v, bright=1000):
    t = T(dur)
    x = sum(np.sin(2 * np.pi * f * (1 + d) * k * t + rng.random() * 6) / k ** 1.5
            for f in fs for d in (-.003, .003) for k in range(1, 5))
    env = np.minimum(1, t / 1.0) * np.clip((dur - t) / 1.0, 0, 1)
    return lp(x, bright) * env * v / len(fs)


def kick(v):
    t = T(0.45)
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * v


def snare(v):
    t = T(0.3)
    n = hp(lp(rng.standard_normal(len(t)), 5000), 900)
    return (n * 0.8 + 0.3 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 18) * v


def hat(v):
    t = T(0.08)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 60) * v


def place(b, s, st):
    i = int(st * SR)
    j = min(len(b), i + len(s))
    if 0 <= i < len(b):
        b[i:j] += s[:j - i]


def verb(x, secs, mix):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 5.5, n))
    ir = lp(ir, 2600)
    ir /= np.abs(ir).sum() ** .5 * 5
    return x * (1 - mix) + fftconvolve(x, ir)[:len(x)] * mix * 3


L = int((D + 3) * SR)
M = np.zeros(L); Dr = np.zeros(L); A = np.zeros(L)
if MOOD == "dark":
    bpm, CH = 66, [[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [43, 50, 55, 59, 62], [40, 47, 52, 55, 59]]  # Am F G Em
elif MOOD == "dreamy":
    bpm, CH = 70, [[48, 55, 62, 64, 71], [45, 52, 55, 60, 64], [41, 48, 55, 57, 64], [43, 50, 55, 59, 62]]  # Cmaj9 Am7 Fmaj7 G
else:
    bpm, CH = 78, [[50, 57, 60, 64, 65], [43, 55, 59, 62, 65], [48, 55, 59, 64, 67], [45, 55, 60, 64, 67]]  # Dm9 G13 Cmaj7 Am7
beat = 60 / bpm
bar = 4 * beat
for b in range(int(D / bar) + 2):
    s = 0.05 + b * bar
    c = CH[b % 4]
    if MOOD == "warm":
        place(M, keys(hz(c[0]), bar, 0.35), s)
        for k, m in enumerate(c[1:]):
            place(M, keys(hz(m), bar * 0.9, 0.13), s + 0.012 * k)
            place(M, keys(hz(m), bar * 0.5, 0.07), s + beat * 2.5 + 0.012 * k)
        if b >= 1 or True:
            sw = beat * 0.08
            for q in range(4):
                if q in (0,) or (q == 2 and b % 2):
                    place(Dr, kick(0.55), s + q * beat)
                if q in (1, 3):
                    place(Dr, snare(0.22), s + q * beat)
                for e in (0, 1):
                    place(Dr, hat(0.06 if e else 0.09), s + q * beat + e * (beat / 2 + sw))
        mel = rng.permutation(c[2:])[:2]
        for k, m in enumerate(mel):
            place(M, keys(hz(m + 12), 1.4, 0.06), s + beat * (1.5 + 1.5 * k))
    elif MOOD == "dreamy":
        place(M, piano(hz(c[0]), bar + .5, 0.32), s)
        for k, m in enumerate(c[1:4]):
            place(M, piano(hz(m), bar, 0.2), s + 0.03 * k + (beat * 2 if k == 2 else 0))
        for k, m in enumerate(rng.permutation(c[3:] + [c[2] + 12])[:2]):
            place(M, piano(hz(m + 12), 2.5, 0.09), s + beat * (1 + 1.6 * k))
        place(A, pad([hz(m) for m in c[1:4]], bar + 1, 0.5, 1100), s - 0.3)
    else:
        place(M, piano(hz(c[0] - 12), bar + 1, 0.30), s)
        place(M, piano(hz(c[0]), bar, 0.18), s)
        for k, m in enumerate(c[2:]):
            place(M, piano(hz(m), 1.8, 0.14), s + beat * (k + 1))
        place(A, pad([hz(m) for m in c[:3]], bar + 1, 0.6, 700), s - 0.3)
        for q in range(2):
            place(Dr, kick(0.45) * 0.8, s + q * beat * 2)

mix = verb(M, 2.6, 0.38) + verb(A, 2.5, 0.4) * 0.8 + lp(Dr, 6000) * (1.0 if MOOD == "warm" else 0.7)
if MOOD == "warm":
    mix = lp(mix, 5200)
    crackle = np.zeros(L)
    idx = rng.integers(0, L, int(D * 40))
    crackle[idx] = rng.standard_normal(len(idx)) * 0.25
    mix += hp(crackle, 2500) + lp(rng.standard_normal(L), 900) * 0.004
mix = mix[:int(D * SR)]
f = np.ones(len(mix))
f[:int(.3 * SR)] = np.linspace(0, 1, int(.3 * SR))
f[-int(1.2 * SR):] = np.linspace(1, 0, int(1.2 * SR))
mix *= f
st = np.stack([mix, np.roll(mix, 260)], 1)
st = st / np.abs(st).max() * 0.85
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok", OUT)
