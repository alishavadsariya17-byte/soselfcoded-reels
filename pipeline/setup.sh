#!/usr/bin/env bash
# One-time (per session) setup for the daily Reel pipeline. Safe to re-run.
set -e
cd "$(dirname "$0")/.."
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
python3 -c "import kokoro_onnx, soundfile, scipy, PIL, numpy" 2>/dev/null || \
  pip install --break-system-packages -q kokoro-onnx soundfile scipy pillow numpy
mkdir -p .models
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s ".models/$f" ] || curl -sSL -o ".models/$f" \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
ls -la .models
echo "setup ok"
