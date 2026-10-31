# SO.SELF.CODED — daily Reel runbook

Owner: Alisha (Instagram **@so.self.coded_**, vidIQ platformAccountId `29410977918494469`).
Brand: self-empowerment and resilience; each Reel is one lesson from a well-known self-help book,
rewritten in our own words. Signed **SO.SELF.CODED**. Approved look: light cream background,
espresso serif-italic text, terracotta accent, soft female voiceover, soft dreamy piano kept low.

The owner approved **fully automatic daily posting** (one Reel per day, ~7:30 pm Toronto) on 2026-10-30.
She is not watching the run: make sensible calls, never stop to ask, and message her the result at the end.

## Daily procedure

0. **One post per day.** If `state.json.posted` already has an entry dated today (Toronto date) — posted or
   scheduled — do nothing except a one-line note to the owner, and stop.

1. `git pull` in this repo, then `bash pipeline/setup.sh` (installs deps + voice model; ~1 min).
2. Read `state.json` → `next_day`. If `specs/dayNN.json` already exists for that day, use it (skip step 3). Take that day's entry from `lessons.json` (book, author, idea, hook_idea).
   If lessons run out, pick a new well-known self-help book not used in `state.json.posted`.
3. Write `specs/dayNN.json` (copy the shape of `specs/day01.json` exactly). Rules:
   - **Own words only.** Never quote a book verbatim beyond a 2–4 word phrase (titles/catchphrases are fine).
   - `hook` (≤ 9 words): scroll-stopper using a proven pattern — "Someone asked me…", "I saw a line that…",
     a permission line ("You don't have to…"), or a relatable pain ("Tired of…?").
   - `pair`: two short serif lines (≤ 26 chars each) that set up the problem.
   - `beats`: exactly 3 × [setup ≤ 30 chars ending with a comma, punch ≤ 14 chars]. Repetition = rhythm.
   - `turn` (≤ 34 chars): the emotional pivot. `heading` (≤ 9 chars, e.g. "Let me.", "Begin."),
     `lines`: 3 short lowercase lines (≤ 20 chars). `closer` (≤ 40 chars): the save/send line.
   - `cover`: label "A lesson from <Book>", `line1`/`line2` ≤ 10 chars each, `small` ≤ 6 chars, `sub` ≤ 36 chars.
   - `caption`: hook sentence + 🖤, a comment question, a save/send CTA, blank line, 6–8 hashtags ending with
     `#soselfcoded`.
   - `music_key`: integer −3..3 (vary day to day), `music_seed`: any int (use the day number × 7).
4. Build: `python3 pipeline/make_day.py specs/dayNN.json reels/<YYYY-MM-DD>_<slug>.mp4` (~3 min).
   Check the printed `vo` lines: every segment must end before its limit, ideally at speed ≤ 1.0
   (above that she sounds rushed). If a segment needed > 1.0, shorten that text in the spec and rebuild.
5. Verify before posting: `ffprobe` shows 1080x1920 and ~28.5 s; extract frames at 0.2, 4, 8, 22, 27.5 s and
   look at them (text readable, nothing cut off, nothing overlapping). Fix and rebuild if anything is wrong.
6. Publish the file:
   - `git add reels/... specs/... && git commit && git push` (end commit messages with the session's
     attribution lines).
   - Public URL: `https://raw.githubusercontent.com/alishavadsariya17-byte/soselfcoded-reels/main/<path>`.
   - `vidiq_video_upload` with that `url` (free) → `videoUrl`.
   - `vidiq_instagram_publish_reel` with `platformAccountId` `29410977918494469`, that `videoUrl`, the spec's
     `caption`; no trial params; do not set `isAiGenerated` unless the owner asks. Continue with the returned
     `containerId`/`mcpJobId` until `PUBLISHED`. Never retry a failed publish automatically.
7. Update `state.json` (append to `posted` with day, date, file, permalink or error; bump `next_day`), commit, push.
8. Message the owner (SendUserMessage + push notification if available): what posted, the permalink,
   the hook line. If anything failed, say exactly what and attach the mp4 so she can post it by hand.

## Weekly (Sundays)
Use `vidiq_instagram_owner_insights` for the last 7 days: which hooks/books got the most reach, saves and
shares. Re-order the next 7 entries in `lessons.json` toward what worked, note findings in `insights.md`.

## Repo size
Each Reel is ~20 MB. When `du -sh .git` passes ~800 MB, tell the owner and propose cleaning old videos;
do not rewrite history without her OK.
