# Aether: Night Shift

Animated thriller Shorts for the Aether YouTube channel, generated entirely with code.

- `episodes/<ep>/`: each episode's script, final video and thumbnail
- `pipeline/audio.py`: offline TTS voices (Kokoro) plus sound design, which writes `mix.wav` and `timing.json`
- `pipeline/render.py`: pycairo animation rendered to MP4 with ffmpeg

Usage: `python3 pipeline/audio.py episodes/epXX && python3 pipeline/render.py episodes/epXX`
