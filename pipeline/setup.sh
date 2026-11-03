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
python3 pipeline/songs.py /tmp/_songtest.wav 2 tender_piano >/dev/null && echo "music ok"
echo "setup ok"
