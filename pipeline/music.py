"""Usage: python3 music.py out.wav [key_offset_semitones -3..3] [seed]
Warm, dreamy, hopeful instrumental (no drums) in the style trending under calm voiceover Reels.
Soft felt piano chords + high glassy melody + airy pad, 70 BPM, C major-ish: Cmaj9 - G/B - Am7 - Fmaj7.
Arranged to the pre-cover timeline: gentle 0-15.7 | thins out 15.7-17.4 (the pause) | pad opens + melody lifts at 17.5."""
import numpy as np, wave, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
KEY = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 33
from scipy.signal import butter, sosfilt, fftconvolve
SR = 44100; D = 28.0
rng = np.random.default_rng(SEED)
hz = lambda m: 440 * 2 ** ((m + KEY - 69) / 12)

def piano(f, dur, v):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * k * 1.0006 ** k * t) * np.exp(-t * (0.9 + 0.8 * k)) for k, a in enumerate([1, .35, .15, .06], 1))
    x *= 1 - np.exp(-t * 220)
    return sosfilt(butter(2, 1800, 'low', fs=SR, output='sos'), x) * v

def glass(f, dur, v):  # soft bell-like top melody
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 3)) * np.exp(-t * 1.2)
    return x * (1 - np.exp(-t * 80)) * v

def pad(fs, dur, v, bright):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f in fs:
        for d in (-0.003, 0.003):
            x += sum(np.sin(2 * np.pi * f * (1 + d) * k * t + rng.random() * 6) / k ** 1.4 for k in range(1, 6))
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.0).clip(0)
    return sosfilt(butter(2, bright, 'low', fs=SR, output='sos'), x) * env * v / len(fs)

def place(b, s, st):
    i = int(st * SR); j = min(len(b), i + len(s))
    if 0 <= i < len(b): b[i:j] += s[:j - i]

def verb(x, secs, mix):
    n = int(secs * SR); ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 5.5, n))
    ir = sosfilt(butter(1, 2600, 'low', fs=SR, output='sos'), ir); ir /= np.abs(ir).sum() ** .5 * 5
    return x * (1 - mix) + fftconvolve(x, ir)[:len(x)] * mix * 3

beat = 60 / 70; bar = 4 * beat; t0 = 0.05
CH = [[48, 55, 62, 64, 71], [47, 55, 59, 62, 67], [45, 52, 55, 60, 64], [41, 48, 55, 57, 64]]  # Cmaj9 G/B Am7 Fmaj7
MEL = [[76, 74], [74, 71], [72, 76], [72, 69]]
MEL2 = [[79, 76, 74], [74, 79, 71], [76, 72, 76], [77, 76, 72]]
_r = np.random.default_rng(SEED)
MEL = [list(_r.permutation(m)) for m in MEL]
MEL2 = [list(_r.permutation(m)) for m in MEL2]
L = int((D + 4) * SR); P = np.zeros(L); G = np.zeros(L); A = np.zeros(L)
for b in range(int(D / bar) + 1):
    s = t0 + b * bar; c = CH[b % 4]; pause = 15.4 <= s < 17.4
    place(P, piano(hz(c[0]), 4.5, 0.30), s)
    for k, m in enumerate(c[1:4]):
        place(P, piano(hz(m), 4.0, 0.16 if pause else 0.20), s + 0.03 * k + (beat * 2 if k == 2 else 0))
    if not pause:
        lift = s >= 17.3
        mel = MEL2[b % 4] if lift else MEL[b % 4]
        for k, m in enumerate(mel):
            place(G, glass(hz(m), 3.0, 0.11 if lift else 0.08), s + beat * (1 + k * (1.2 if lift else 1.6)))
    place(A, pad([hz(m) for m in c[1:4]], bar + 1.2, 0.5, 900 if s < 17.3 else 2200), s - 0.4)
tt = np.arange(L) / SR
A *= 0.45 + 0.55 * np.clip((tt - 16.8) / 1.5, 0, 1)  # pad opens at the turn
mix = verb(P, 3.2, 0.42) + verb(G, 4.0, 0.55) * 1.2 + verb(A, 2.5, 0.4) * 0.7
mix += sosfilt(butter(1, 2000, 'high', fs=SR, output='sos'), rng.standard_normal(L)) * 0.0012  # faint tape air
mix = mix[:int(D * SR)]
f = np.ones(len(mix)); f[:int(.4 * SR)] = np.linspace(0, 1, int(.4 * SR)); f[-int(2.2 * SR):] = np.linspace(1, 0, int(2.2 * SR))
mix *= f
st = np.stack([mix, np.roll(mix, 220)], 1); st = st / np.abs(st).max() * 0.89
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok')
