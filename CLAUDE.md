# SO.SELF.CODED — Reel runbook (quote-page style, 2 posts a day)

Owner: Alisha (Instagram **@so.self.coded_**, vidIQ platformAccountId `29410977918494469`).
Niche: self-worth, healing, letting go, boundaries, soft life, discipline, love and friendships, written for
young women. Format (owner's choice 2026-11-03): short (6–9 s) "quote page" Reels in the style of the big quote
accounts. Textured paper, small serif or handwritten text, lots of empty space, a song-like background track
that fits the words, and no voiceover. Her reference images are in `references/`. Look at the newest ones before
writing, because she adds more over time and they show where she wants the page to go.

**SONG-READY DRAFTS, TWICE A DAY (owner's choice 2026-11-03): a midday draft (~12:05 Toronto) and an evening
draft (~19:05 Toronto).** She wants real movie songs on her Reels. Copyrighted songs can't go inside the file
(Instagram mutes or removes them), so each run builds a **silent** video and sends it to her with the caption and
3 song picks from `songs.md`. She posts it from the Instagram app and adds the song there. **Do not publish
anything yourself** unless she switches back to auto-posting. She is not watching the runs: make sensible
calls and never stop to ask.

## Content rules (this is what makes or breaks reach)
- **Own words only.** Never copy another account's line or a book passage beyond 2–4 words. Book lessons are
  welcome (about 1 in 3 posts): write the idea in our own words, and only name the book in the caption
  ("a lesson from <Book>").
- Every post must be **instantly relatable and worth saving or sending**. Give one sharp truth that makes her
  audience think "this is me", in fewer than 30 words on screen. Use concrete, specific images ("replying in
  2 minutes to people who reply in 2 days") over vague ones ("be positive").
- Proven framings to rotate: "I read this at 2am and had to put the book down,", "Someone once said … and I felt
  that.", "read this before your day starts:", "Soft reminder", "To the strong friend:", "Lately", a quiet
  confession, a funny truth, or a permission line. **Never use the same framing in two posts in a row.**
- Mix moods across the week: comforting, empowering, a little sad, funny and relatable. Use evenings for
  heavier and 2am-feelings posts, and middays for lighter, morning, coffee, discipline and funny posts.
- Caption: one punchy line + 🖤, a comment question or tag prompt, a save/send line, a blank line, then 5–7
  hashtags ending with `#soselfcoded`.

## Visual rules
- Formats (`pipeline/paper.py`, see its docstring; copy the shape of any file in `queue/` or `specs/examples3/`):
  book-page highlight, coffee cup, minimal serif with *italic* words, red handwritten caps on speckled paper,
  paragraph with a closing ” mark, solid colour + handwritten caps, "Someone once said", torn note in blue pen,
  heading + line, handwriting on blush paper.
- **Change is good. Never post the same format twice in a row.** Vary the paper colour, highlight colour (yellow,
  pink, mint), fonts, alignment and text position from post to post. At least once a week, build a new layout
  inspired by the newest image in `references/`. Extend `paper.py` with a new `bg` or block style when needed
  and test it with a still preview before posting.
- **Thumbnails:** the first frame is the finished design, held for 0.7 s, so it becomes the cover and the
  profile grid stays beautiful. Keep all text inside the middle 3:4 area (y 240–1680) so the grid crop never
  cuts it. Check the `_grid.jpg` that each build writes. The profile should read as one calm aesthetic: soft
  neutrals with the occasional deep colour (maroon, coffee black).
- Audio: every spec has `"silent": true` (she adds a real song in the app). Keep a `"music": {"style": ...}`
  entry as the mood tag. `pipeline/songs.py` (our own composed music with real instruments) is only used if
  she switches back to auto-posting. Never put copyrighted songs in the file.
- Songs: choose 3 from `songs.md` that fit the words: a movie song, a score or instrumental, and a wildcard.
  Name the part to use (for example "start at the chorus") and don't repeat a song within a week.

## Each run (procedure)
0. Work out the slot from the Toronto time: **midday** (before 15:00) or **evening**. If `state.json.posted`
   already has an entry with today's Toronto date and the same `slot`, send her one line and stop.
1. `git pull`, then `bash pipeline/setup.sh`.
2. Spec: if `queue/` has files, take the lowest-numbered one whose format differs from the last post's
   `format` (in `state.json`) and `git mv` it to `specs/<YYYY-MM-DD>_<slot>.json`. Otherwise write a new spec
   following the rules above, never repeating a line from `state.json.posted`. Check every hook against the
   last ~20 posts.
3. Still preview: `python3 pipeline/paper.py specs/<file>.json /tmp/prev.png`, then look at it. Text must be
   readable, nothing cut off, and it must look like the references. Fix the spec if anything is off.
4. Build: `python3 pipeline/paper.py specs/<file>.json reels/<YYYY-MM-DD>_<slot>_<slug>.mp4` (~1 min).
   Verify with `ffprobe` (1080x1920, has audio, 6–10 s). Look at `_cover.jpg`, `_grid.jpg` and frames at 1.5 s
   and the last second.
5. Save: `git add` the reel, its `_cover.jpg`/`_grid.jpg` and the spec, then `git commit && git push`
   (end commit messages with the session's attribution lines).
6. Send the draft to her:
   - `SendUserFile` with the mp4 (status proactive).
   - `SendUserMessage` with: "Ready to post (midday|evening)"; the caption in a code block so she can copy it
     in one tap; 3 song picks (song – artist (film) + which part to use); and a one-line how-to: in the
     Instagram app, New Reel → pick the video → Add audio → search the song → set the clip → keep the first
     frame as the cover → paste the caption → Share.
   - Push notification: "Draft ready: <on-screen line> · song: <first pick>".
7. Append to `state.json.posted`: date, slot, format, mood, hook (first on-screen line), file, songs,
   status "draft sent". Then commit and push. (If she shares a permalink later, add it.)
8. If `queue/` has fewer than 4 specs left, write 4 more good ones into it (varied formats and moods) and push.

## Weekly (Sundays, evening run)
Run `vidiq_instagram_owner_insights`. Match her posted Reels to our drafts by caption. Note which formats,
framings and songs got the most reach,
watch %, saves and shares in `insights.md`, and lean the next week's queue toward what worked.

## Repo size
Each Reel is ~15–20 MB. When `du -sh .git` passes ~800 MB, tell the owner and propose cleaning old videos;
do not rewrite history without her OK.

## History
Days 1–4 (Oct 30–Nov 2) used the old book-lesson voiceover format (`pipeline/make_day.py`, `lessons.json`).
That format is retired. Keep its files for reference only.
