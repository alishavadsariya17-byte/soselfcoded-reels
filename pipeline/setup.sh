#!/usr/bin/env bash
# Per-session setup for the Reel pipeline (quote-page Reels + song-style music). Safe to re-run. ~1 min.
set -e
cd "$(dirname "$0")/.."
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
if ! which fluidsynth >/dev/null || [ ! -s /usr/share/sounds/sf2/FluidR3_GM.sf2 ]; then
  (apt-get install -y --no-install-recommends fluidsynth fluid-soundfont-gm >/dev/null 2>&1) || \
  (apt-get update >/dev/null 2>&1 && apt-get install -y --no-install-recommends fluidsynth fluid-soundfont-gm >/dev/null 2>&1)
fi
python3 -c "import mido, scipy, PIL, numpy" 2>/dev/null || \
  pip install --break-system-packages -q mido scipy pillow numpy
# real instrument samples (Salamander Grand Piano + tonejs-instruments), MIT-licensed npm packages, ~30 MB
mkdir -p .samples/dl
if [ ! -f .samples/dl/.done ]; then
  ( cd .samples/dl && npm pack -q @audio-samples/piano-mp3-velocity6 @audio-samples/piano-mp3-velocity10 \
      @audio-samples/piano-mp3-velocity14 tonejs-instrument-cello-mp3 tonejs-instrument-violin-mp3 \
      tonejs-instrument-harp-mp3 tonejs-instrument-guitar-acoustic-mp3 tonejs-instrument-guitar-nylon-mp3 \
      tonejs-instrument-flute-mp3 tonejs-instrument-contrabass-mp3 >/dev/null 2>&1 && \
    for f in *.tgz; do mkdir -p "${f%.tgz}" && tar xzf "$f" -C "${f%.tgz}" --strip-components=1 && rm "$f"; done && touch .done )
fi
python3 pipeline/songs.py /tmp/_songtest.wav 4 tender_piano >/dev/null && echo "music ok"
echo "setup ok"
