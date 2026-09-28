# T6 report — live-demo dry-run checklist

**Rehearsal:** T5 evening (2026-10-01) recommended. **Report:** Friday 2026-10-02.
**Duration budget:** 15-20 min presentation + demo + ~5 min Q&A.

_Goal: catch every failure mode before it happens in front of the judging panel._

---

## 24 hours before (T5 evening)

### Machine + network

- [ ] Restart machine once (clears stale state, memory pressure, orphan processes)
- [ ] Confirm reliable network — run `curl https://generativelanguage.googleapis.com/` and
  `curl https://openrouter.ai/api/v1/models` (should return valid JSON, not timeout)
- [ ] Confirm Ollama service running: `ollama ps` shows `qwen3.5:9b` loaded
  (or auto-loads on first request within 5s)
- [ ] Confirm ffmpeg on PATH: `ffmpeg -version` returns a version
- [ ] Confirm `.env` has non-empty `DIE_GEMINI_API_KEY` + `DIE_OPENAI_COMPAT_API_KEY`
- [ ] Free disk: `>=5 GB` on `%LOCALAPPDATA%` (for a fresh `.exe` install's data dir if
  demo uses the packaged app instead of dev mode)

### App state

- [ ] Dev server on port 8000 running: `curl http://127.0.0.1:8000/health` → `200`
- [ ] Real DB has at least 1 pre-generated project ready to show existing content
  (Dashboard should not be empty on stage)
- [ ] Sample `.zip` (`docs/report/samples-A1-B1-C1.zip`) already shared with panel via
  email/drive link — confirmed panel received it
- [ ] Chart PNG (`docs/report/benchmark-chart.png`) inserted into slide 5, renders
  crisp at projection resolution

### Backup artifacts

- [ ] Slide deck exported to PDF as offline fallback (in case Google Slides / PowerPoint
  live rendering fails)
- [ ] Pre-recorded backup video ready (optional but recommended — see "Backup video"
  section below)
- [ ] Screenshot of Report-UX-1 banner (`Generating learning pack — queued (0%) · 0:14
  · ~28s left [Cancel]`) saved locally as a fallback still image for slide 6 in case
  the live demo can't reach that state

---

## Demo dry-run script (rehearse twice)

Do the full run twice on T5 evening. Time each attempt. Target: **7-8 minutes** for
the demo portion (steps 1-8 below), leaving room for narration in between.

### 0 — Preamble (before opening the app)
- [ ] Screen recording software started (OBS / built-in), audio muted
- [ ] Timer widget visible on screen (upper-right corner recommended)
- [ ] Browser at 1280×720+ zoom level 100% (matches app UI's native design)
- [ ] Close every other tab and dock item to reduce visual noise

### 1 — Dashboard
- [ ] Navigate to `http://localhost:8000` (or the packaged `.exe`'s URL)
- [ ] Verify: Dashboard loads under 1s, existing projects visible with real status badges
- [ ] Narration cue: "This is where every episode starts. I have some existing projects
  from prior sessions here."

### 2 — Create new project (Step 1 Config)
- [ ] Click `+ New Project`
- [ ] Fill: topic = **"Morning coffee routine"** (short + memorable + finishes fast)
- [ ] CEFR = **B1** (matches Gate B-11 baseline — audience's ETA expectation is 45s)
- [ ] Duration = **3 minutes** (short so we don't exceed talk time)
- [ ] Genre = **small_talk** (fast, natural output)
- [ ] Speakers = **2** (Alex male + Maya female, both American)
- [ ] Click `Save & Continue` → navigates to Step 2
- [ ] Narration cue: "Everything from here is AI-generated in real time."

### 3 — Step 2 Generate Script (⭐ the money shot)
- [ ] Click `Generate Script`
- [ ] **Watch the banner** — call it out for the audience:
  `Generating script — outline (5%) · 0:03 · ~42s left [Cancel]`
- [ ] Elapsed counter ticks every second, stage advances (`outline` → `section_1` → …
  → `section_5`)
- [ ] Expected wall time: **~30-50 seconds** (Gate B-11 median 45s)
- [ ] When script appears, scroll through it briefly, point out a natural line
- [ ] Narration cue: "This is 8-minute podcast dialogue in ~45 seconds. Backend is
  cloud-first — Gemini 3.1 Flash-Lite handles it; if that failed, the app slid to
  OpenRouter, then to local qwen. Users never see failure."

### 4 — Step 3 Generate Learning Pack
- [ ] Click `Generate Learning Content`
- [ ] Same banner pattern: `Generating learning pack — queued (0%) · 0:02 · ~28s left [Cancel]`
- [ ] Expected: **~20-40 seconds**
- [ ] When done, click through **Vocabulary** tab: point at a vocab card (IPA, PoS,
  EN/VI definition, example)
- [ ] Click **Idioms** tab, brief pause
- [ ] Narration cue: "Educational content auto-generated at the same CEFR level. This is
  what makes it a learning podcast, not just a podcast."

### 5 — Step 4 TTS + Audio Mix
- [ ] Navigate to Step 4 (via workflow sidebar)
- [ ] Skip voice assignment (default is fine); optionally show the accent chip briefly
- [ ] Click `Generate All`
- [ ] Watch progress: `Synthesizing line 1/12 · 0:03 · ~35s left [Cancel]`
- [ ] Expected: **~60-90 seconds** for 3-min episode (5s/line × 12 lines + 15s mix)
- [ ] When done, click Play on the audio player, let 5-10 seconds of real audio play
- [ ] Narration cue: "That is real Edge TTS voice, real ffmpeg mix, normalized to
  broadcast loudness."

### 6 — Step 5 Video (optional, only if time)
- [ ] Navigate to Step 5
- [ ] Pick a background template (any)
- [ ] Click `Generate`
- [ ] Expected: **<5 seconds** (ffmpeg render is fast, subtitle burn-in)
- [ ] Play the video briefly — subtitles should be perfectly synced
- [ ] Narration cue: "Auto-subtitled video, ready for YouTube."

### 7 — Step 7 YouTube Package
- [ ] Navigate to Step 7 (skip Step 6 Thumbnail for time)
- [ ] Show the titles / description / chapters that were generated
- [ ] Click `Download full package (.zip)` — save to Desktop, briefly show the zip
  contents
- [ ] Narration cue: "One click: everything a creator needs to upload to YouTube."

### 8 — Wrap
- [ ] Return to Dashboard, show the new project card is now `complete`
- [ ] Narration cue: "One click, ~3 minutes end-to-end. Any level, any topic."

---

## If something goes wrong

| Failure | Response |
|---|---|
| Gemini returns 429/quota exhaustion | Stay calm — say "cloud is rate-limited, the app is now falling back to local qwen" (this IS the story). Local generation will take longer (~2 min) but still works. Fill talk time with the architecture slide. |
| Network completely down | Kill switch: `DIE_AI_ALLOW_CLOUD=false` env; restart the app; runs pure local. Say "here's what full offline looks like." |
| Ollama not responding | If dev server started with Ollama down, script gen will fail. Retry via UI's `Retry` button. Worst case switch to the pre-recorded backup video. |
| Dev server crashes | Cut to the backup video. Say "the demo footage shows the same flow." |
| Report-UX-1 counter doesn't show | Least likely (test suite covers this). Continue demo without pointing to elapsed; make the story about total wall time instead. |
| Sample .zip attached but panel didn't download | Have a spare zip on USB or open the folder locally. |
| Q&A goes deep on technical detail | Have `docs/operations/phase18-gate-b11.md` open in another tab — it's the primary evidence source. |

---

## Backup video — ✅ recorded

**File:** `docs/report/backup-demo-walkthrough.webm` (3:20, 10.6 MB, real full-pipeline
recording via `scripts/record_demo_video.py`)

**Contents:** Steps 1-5 end-to-end (Config → Script → Learning → Audio → Video) with real
Gemini + real Edge TTS + real ffmpeg. Report-UX-1 counter visible for the first time in a
recorded demo.

**Real disclosure (do not hide this if asked during Q&A):** during the recording,
`gemini-3.1-flash-lite` returned `ProviderUnavailableError` on the first call and the chain
fell back to `gemini-flash-lite-latest`. This is exactly the resilience story slide 4
describes — the app recovered without user visible failure. Not a defect. If a judge asks
"why did that take slightly longer than 45s?", the honest answer is "cloud transient
failure, chain fallback worked as designed" — which is stronger than "clean run" for a
technical audience.

**Steps 6-7 (Thumbnail + YouTube Package) not in backup video** — Gemini transient outage
persisted through step 6 and timed out. Not shipped. For live demo T6, if this happens:
skip step 6/7 verbally ("thumbnail + YouTube package would be next; those are Gemini text
calls with similar timing to script/learning").

**Also included:** `docs/report/backup-demo-step2-frame.png` — single frame extract at
t=8s showing the Step 2 banner with real counter. Use as slide 6's static fallback image
if the full video can't be embedded (large webm may not play cleanly in some slide apps).

**Playback recommendations:**
- Full video for slide 7 main content if live demo fails
- Or 5-10s clip of Step 2 (t=0:03 to t=0:12) showing counter counting down + banner text
  changing stage — highest single-visual impact
- Or the still frame `.png` as a slide 6 visual proof if no video option works

---

## Post-report cleanup (not for T6, for the day after)

- [ ] Unpark Phase 19: 19.5 vocab, 19.6 intro-outro, 19.7 full packaging, 19.8 Gate B-12,
  19.9 close-out
- [ ] Resolve ENH-014 outro heuristic (task card ready if not done pre-report)
- [ ] Resolve ENH-015 Gemini first-pass length (needs real cloud runs; owner budget)
- [ ] Consider whether to also open Phase 20 (AI thumbnails) based on report feedback
