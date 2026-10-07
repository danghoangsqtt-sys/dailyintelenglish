# Phase 27 Task 27.5: the Daily Beyond English video intro and outro (2026-10-07)

**Frames:** `docs/operations/phase27-brand-video-frames.png` (9 real frames from the Remotion composition: the intro
at 0.5 s, 1.9 s, 3 s, 5 s and 7 s, then the outro at 11 s, 12.7 s, 14.3 s and 16.7 s).

- The morph the owner approved in Phase 25 is unchanged. What changed: the mark is the owner's circular logo, the
  wordmark reads "Daily Beyond" over a yellow "ENGLISH", the background is deep green with green, lime and yellow
  blobs, the level pill is yellow, the speaker rings are yellow and lime, Subscribe stays red.
- **Voice:** Jenny's lines now say "Welcome to Daily Beyond English Channel!" and "Thanks for watching Daily Beyond
  English!"; the cache is keyed by text, so new audio was made once (6.2 s and 6.2 s with the wish and the farewell):
  intro slide 7.62 s, outro slide 8.54 s.
- **Real render check:** intro + a 3 s line + outro = 19.16 s expected; the rendered MP4 is 19.22 s (the encoder's
  audio padding), with a video and an audio stream, and both voice windows carry audio (peaks -4.6 and -5.9 dB).
- Tests: vitest 47 (palette has no violet or cyan; every text colour is AA on the deep green; the name and the logo
  path), `tsc` clean, Python: the new sentences, the logo asset and that git tracks it.
- Colour contrast: text on the background >= 7:1, muted text and the yellow >= 4.5:1, white on the Subscribe red 5.5:1.
