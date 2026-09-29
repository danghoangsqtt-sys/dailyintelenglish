# Phase 19 Gate B-12 — Remotion media gate + owner visual sign-off

- **Gate:** B-12 (Remotion path acceptance gate for Phase 19)
- **Executed:** 2026-09-29 by PM against an isolated instance of the app on ephemeral
  port + copy of `data/app.db` (respecting standing rules: dev server on :8000 never
  restarted, real DB `mode=ro` from write POV — the isolated instance's own writes go
  to the temp-dir copy).
- **Decision:** **PARTIAL** — media gate 6/6 PASS + fallback invariant PASS +
  Remotion visual PASS by owner, but Edge TTS voice quality flagged as blocker for
  shipping the `DIE_VIDEO_RENDERER=remotion` default. Task 19.9 close-out **held**
  until Phase 21 (better TTS engine) ships. Combined `v1.2.0-beta` release will then
  flip both.

## 1. Episodes

3 real B1/A2 episodes with completed audio, chosen for content diversity:

| # | Project id | Name | CEFR | Genre | Duration |
|---|---|---|---|---|---|
| 1 | `b330d37f-a212-4cf7-a779-7a109098bd6c` | Demo Episode | B1 | small_talk | 2:56 (176.02s) — baseline (all prior Phase 19 tasks measured against this) |
| 2 | `c08ce057-792a-44db-be5d-2585e6600f4b` | Demo Episode | B1 | small_talk | 5:00 (300.06s) — mid |
| 3 | `22484f26-f944-40db-8064-44088ccdb507` | Good Morning | A2 | small_talk | 9:26 (566.38s) — longest, different CEFR |

## 2. Renders — real, per-API, isolated instance

Each episode rendered TWICE via real `POST /api/projects/{id}/video/generate` route:
once with `{"renderer": "ffmpeg"}` (baseline) and once with `{"renderer": "remotion"}`.
The isolated server started with `DIE_VIDEO_RENDERER=remotion` env so the request-level
`renderer` field could actually resolve to `"remotion"` (per Task 19.7 D19.7-b kill
switch).

Raw evidence: `docs/operations/gate-b12-evidence/gate-b12-runs.json`.

| Episode | Renderer | Wall time | Output size | Duration | Video stream | Audio stream | A/V drift |
|---|---|---|---|---|---|---|---|
| B1 2:56 | ffmpeg | 7.3 s | 2.51 MB | 176.04 s | 176.04 s | 176.02 s | 0.02 s |
| B1 2:56 | **remotion** | **62.7 s** | 9.22 MB | 183.57 s | 183.53 s | 183.57 s | 0.04 s |
| B1 5:00 | ffmpeg | 21.2 s | 5.30 MB | 300.08 s | 300.08 s | 300.06 s | 0.02 s |
| B1 5:00 | **remotion** | **112.2 s** | 18.54 MB | 307.63 s | 307.57 s | 307.63 s | 0.06 s |
| A2 9:26 | ffmpeg | 41.5 s | 9.45 MB | 566.40 s | 566.40 s | 566.38 s | 0.02 s |
| A2 9:26 | **remotion** | **224.2 s** | 31.30 MB | 573.93 s | 573.90 s | 573.93 s | 0.03 s |

All 6 renders **1280×720 h264/aac**, exact.

## 3. Media gate check — 6/6 PASS

Media gate thresholds (unchanged from Phase 14/15/17, I40 invariant):
- **Duration ±0.5 s** of expected. For Remotion, expected = audio + intro (2.5 s) +
  outro (5.0 s) = audio + 7.5 s (per Task 19.6 composition design).
- **A/V drift ≤ 1.0 s**
- **Codec** h264 (video) + aac (audio)
- **Resolution** 1280×720 exact

| Episode | Renderer | Duration Δ vs expected | A/V drift | Codec | Dims | Verdict |
|---|---|---|---|---|---|---|
| B1 2:56 | ffmpeg | +0.02 s (audio 176.02, video 176.04) | 0.02 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |
| B1 2:56 | remotion | +0.05 s (audio+7.5=183.52, video 183.57) | 0.04 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |
| B1 5:00 | ffmpeg | +0.02 s | 0.02 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |
| B1 5:00 | remotion | +0.06 s (audio+7.5=307.56, video 307.63) | 0.06 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |
| A2 9:26 | ffmpeg | +0.02 s | 0.02 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |
| A2 9:26 | remotion | +0.05 s (audio+7.5=573.88, video 573.93) | 0.03 s | h264/aac ✅ | 1280×720 ✅ | **PASS** |

**Media gate: 6/6 PASS.** Every render inside every threshold.

## 4. Fallback invariant I36 verification

`/api/video/health` after 3 remotion renders:
```json
{"remotion_configured": true, "remotion_total_calls": 3, "remotion_fallback_count": 0,
 "fallback_rate": 0.0, "last_fallback_reason": null}
```

Zero fallbacks across 3 real renders. Kill switch check (Task 19.7 own e2e verification,
cited): the same runner without `DIE_VIDEO_RENDERER=remotion` env produced `remotion_
total_calls: 0` at the end — Remotion was never even attempted, request routed to
ffmpeg per I36's safety direction. **I36 verified from BOTH directions**: the "happy
path" (Remotion actually runs) and the "kill switch" (Remotion silently skipped).

## 5. Real disclosure — first-run finding (transparent for the record)

Gate run 1 was executed without `DIE_VIDEO_RENDERER=remotion` env, and all 3 Remotion
requests silently resolved to ffmpeg (per Task 19.7 D19.7-b spec — kill switch
enforcement, working as designed). PM's own script omitted the env. Not a defect,
disclosed here so a future reader knows what "run 2" fixed. This same behavior IS what
Task 19.7 shipped intentionally: without the deployment opt-in, Remotion cannot even
be attempted.

## 6. Owner visual sign-off

- 3 Remotion MP4 files delivered to owner 2026-09-29 for review.
- Owner played back and provided real feedback (verbatim, 2026-09-29):
  > *"Video tạo ra chất lượng rất tốt nhưng giọng nghe không tự nhiên, thiếu cảm xúc."*
  > (Video output quality is very good, but the voice sounds unnatural, lacking
  > emotion.)

**Owner visual (Remotion composition): PASS.** Karaoke word-highlight, speaker chip,
vocab card, intro/outro, chapter bar — all "chất lượng rất tốt" (very good quality)
per owner's own words.

**Owner audio (voice quality): FAIL — specifically NOT a Remotion issue.** Same Edge TTS
voice runs in both ffmpeg and Remotion paths. The complaint is about the TTS engine, not
the video composition. Ships in EVERY future video regardless of renderer choice unless
addressed.

## 7. Additional owner feedback (unrelated but real, recorded 2026-09-29)

- **UI issue**: "Enhanced (Remotion, opt-in)" toggle in Step 5 has an unclear label —
  doesn't tell the user what features they get. Owner didn't know if it turns karaoke
  script on/off. Logged as `task-19.7.n1` (nit fix, ~30-60 min copy fix).
- **New feature request**: AI music generation from text description (copyright-free).
  Owner cited https://github.com/ace-step/ACE-Step-1.5. Logged as future Phase 22
  (post-Phase 21).

## 8. Decision (owner + PM, 2026-09-29)

**Gate B-12: PARTIAL.**
- ✅ Media gate 6/6 PASS
- ✅ Fallback invariant I36 verified (both directions)
- ✅ Owner visual sign-off on Remotion composition
- ❌ Owner audio sign-off on Edge TTS voice — blocker for shipping `remotion` default

**Consequences:**
- Task 19.9 close-out (flip `DIE_VIDEO_RENDERER=remotion` default + version bump)
  **held** until Phase 21 (Kokoro TTS) ships.
- Combined `v1.2.0-beta` release will ship BOTH improvements at once. Version bump
  meaningful.
- Task 19.7.n1 tooltip fix opened as nit (~30-60 min, does not block anything).
- Phase 21 scaffolded and Task 21.1 spike doc-first card ready for Coder pickup.

**Next work order (Coder):**
1. **Task 19.7.n1** — tooltip clarity fix (~30-60 min, unblocks nothing but pleases
   owner immediately).
2. **Task 21.1** — Kokoro TTS spike (~1-2 days, spike-first per Phase 19 precedent).

**No PM/owner action required between 19.7.n1 and 21.1**; Coder can pick up 21.1
straight after 19.7.n1 handover.
