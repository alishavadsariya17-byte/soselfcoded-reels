# soselfcoded-reels

Daily Reel pipeline for Instagram **@so.self.coded_** (SO.SELF.CODED).

- `pipeline/make_day.py` builds a finished 9:16 Reel (cover, text animation, soft voiceover, original music) from a spec.
- `specs/` one JSON per day · `reels/` published videos · `lessons.json` upcoming lessons · `state.json` posting log.
- `CLAUDE.md` is the step-by-step runbook the daily scheduled run follows.

Fonts: Cormorant Garamond, Playfair Display, Poppins (SIL Open Font License). Voice: Kokoro (Apache-2.0).

## Music credits
Background music is composed by `pipeline/songs.py` and played with these sample libraries (fetched at setup, not
stored in the repo): Salamander Grand Piano V3 by Alexander Holm (via the MIT `@audio-samples/piano-mp3-*` packages),
tonejs-instruments by Nicholaus Brosowsky (cello, violin, harp, guitars, flute, contrabass; via MIT npm packages), and
FluidR3 GM by Frank Wen (MIT) for electric piano, music box, pizzicato, marimba and percussion.
