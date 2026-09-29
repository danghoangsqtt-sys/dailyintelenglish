# Task 19.8 — Gate B-12: media gate + owner visual sign-off on Remotion output

- **Status:** ready (PM protocol doc, PM-executed — no Coder pickup this task)
- **Owner:** PM (execution) + owner (visual sign-off, final PASS/FAIL decision)
- **Priority:** P0 (gate decides whether 19.9 close-out flips `DIE_VIDEO_RENDERER` default
  from `ffmpeg` to `remotion`)
- **Dependency:** Task 19.7 accepted (`cca36f8`) — Remotion path callable via `renderer=
  remotion` request field, env kill switch, `check_dependencies` reports status
- **Controlling detail:** `docs/implementation/phase-19-remotion.md` §3 "19.8"; Phase 19
  invariants I36-I40; existing media gate framework (Phase 14/15, `analyze_media_pipeline`
  in `scripts/run_ai_operational_trial.py`)

## Goal

Prove on real evidence that the Remotion path is production-ready before Task 19.9 flips
the `DIE_VIDEO_RENDERER` default. This is a **gate**, not a task-level acceptance — decision
authority is owner's, same shape as D31 (Gate B-11 PASS) and D33 (Task 19.1 spike PASS).

Gate B-12 has three PASS conditions, all must hold:

1. **Media gate PASS on ≥3 real episodes** — duration ±0.5s, A/V drift ≤1.0s, codec check
   (h264/aac), 1280×720 exact.
2. **Owner visual sign-off** — owner watches ≥1 full episode rendered via Remotion path,
   judges the karaoke + speaker chip + vocab card + intro/outro + chapter bar all read as
   "shippable YouTube content, not prototype."
3. **Fallback invariant I36 verified** — one deliberate-failure scenario (Node missing,
   Chrome download blocked, etc.) proves the app degrades to ffmpeg without user-visible
   failure.

## Allowed files (PM-only, no Coder pickup)

- **New** `docs/operations/phase19-gate-b12.md` — the gate report. This is the deliverable.
- **Modify** `.viepilot/phases/19-remotion/PHASE-STATE.md` — evidence log entry, flip 19.8
  status.
- **Modify** `.viepilot/TRACKER.md` — Decision Log entry once owner signs off (D-number to
  be assigned).
- **Modify** `.viepilot/HANDOFF.json` — key_decisions append after owner sign-off.
- **Modify** `CHANGELOG.md` — one `[Unreleased]` bullet once gate closes.
- **Modify** `.viepilot/requests/*` if any real deferred bug or enhancement surfaces
  during the gate that's out of Phase 19 scope.

**Not allowed:** any file under `app/`, `frontend/`, `tests/`, `video-renderer/`,
`scripts/` (this is a measurement task, not a code change). `data/app.db` is `mode=ro` for
gate reads; any real project data mutation (e.g. deleting a test project) requires owner
OK + backup per standing rule.

## Gate protocol (PM steps)

### Step 1 — Pick 3 real B1 episodes

- Prefer 3 different topics/genres so the gate isn't a single-content sample.
- The demo runner has been pinning `b330d37f...` (2:56); use it as episode 1 for
  baseline continuity.
- Episodes 2 and 3: pick from real DB via `mode=ro` query for `audio_jobs.status = 'complete'`.
  If only 1-2 exist (which was the case at Phase 19 start), PM generates additional real
  episodes via the running app on port 8000 (dashboard → Step 1-4). This IS a real DB
  write, but it's PM territory (per standing brief: "data/app.db thật chỉ PM ghi, sau khi
  backup và có OK của owner") — get owner OK + backup before generating.
- Document project ids in the gate report §1.

### Step 2 — Render each episode twice: once ffmpeg, once Remotion

- Via the actual `POST /api/projects/{id}/video?renderer=<mode>` route on the dev server
  (port 8000, still running per earlier rounds). Not the spike script — the real API path
  Task 19.7 wired.
- Record wall time + output filesize + ffprobe metadata (duration / streams / codec / dims)
  for each render.
- If Remotion path fails on any episode: capture the exact error, fallback path taken,
  final output. That's data for the gate decision, not a hard fail.

### Step 3 — Media gate check per episode

For each Remotion output:

- **Duration ±0.5s** of audio duration (I40 invariant, existing media gate threshold)
- **A/V drift ≤1.0s** (existing threshold)
- **Codec** h264 (video) + aac (audio) — matches ffmpeg output
- **Resolution** 1280×720 exact
- **File exists + non-empty** (>1 MB for a ~3-min episode)

Use `ffprobe` directly (`ffprobe -v error -show_entries stream -show_entries format
-of json <file>`), same as Phase 14/15 gates.

Record PASS/FAIL per episode per criterion in a table.

### Step 4 — Fallback invariant I36 verification

Deliberate-failure scenarios, pick one:
- **Rename `video-renderer/node_modules/.remotion/` away** (removes Chrome Headless
  Shell), immediately trigger a Remotion render, confirm:
  - Either: Remotion re-downloads Chrome successfully (D19.7-h Option 2 working as
    designed), first-render slow but produces valid output. **This is not a fallback
    scenario — it's the download-on-first-use path.**
  - Or: some real failure surfaces (network blocked, Chrome download errors), confirm
    `fallback_used: true` in `POST /video` response body, real ffmpeg output produced.
- Alternative: **block Node.js by renaming its exe temporarily** (harder to reverse safely
  on Windows), or **set an invalid `DIE_VIDEO_RENDERER` value**, or **kill the running
  Node subprocess** mid-render.
- Pick whichever is easiest to reverse cleanly. Document the exact scenario + observed
  behaviour + confirmation that a normal ffmpeg render still works after the test.

### Step 5 — Owner visual sign-off

- PM sends owner the Remotion MP4 output from step 2 (attach or link to
  `data/video/<project_id>/video.mp4`).
- Owner watches ≥1 full episode end-to-end.
- Owner answers: does the composition look production-ready for a real YouTube upload?
  Any specific visual bugs (karaoke sync, chip legibility, vocab card timing, chapter bar,
  intro/outro polish)?
- Owner sign-off is required for gate PASS. A "yes but with these fixes" answer means
  gate is CONDITIONAL — either fix in a small follow-up before 19.9, or accept-with-known-
  limitations and log the fixes as follow-up items.

### Step 6 — Gate decision

**PASS conditions (all three):**
- ≥3/3 episodes pass media gate
- Owner visual sign-off = YES (or CONDITIONAL with fixes deferred)
- Fallback invariant I36 verified

**FAIL conditions (any one):**
- Any episode fails media gate on any hard threshold (duration/A-V/codec/dims)
- Owner sign-off = NO
- Fallback path broken (Remotion failure → app error to user, not degradation)

**PARTIAL:**
- Gate passes but with known caveats. 19.9 close-out proceeds anyway if owner accepts
  the caveats; alternative is to open small follow-up tasks before 19.9.

Record owner's decision in this doc + TRACKER Decision Log (D-number TBD).

## Evidence (gate report structure)

The `docs/operations/phase19-gate-b12.md` deliverable must include:

1. **Environment** (OS, Node/npm, Remotion version, ffmpeg, machine specs)
2. **Episodes chosen** (project ids, topics, durations, source)
3. **Renders per episode** (ffmpeg + Remotion, wall time, filesize, ffprobe raw output)
4. **Media gate table** (rows = episodes, cols = criteria, cells = PASS/FAIL with actual
   numbers)
5. **Fallback invariant I36 test** (scenario, observed, PASS/FAIL)
6. **Owner visual sign-off** (owner's exact answer + any conditions)
7. **Gate decision** (PASS / PARTIAL / FAIL + rationale)
8. **Recommendations** for 19.9 close-out (flip default? version bump number? tag?)

## Definition of done

- Gate report on disk at `docs/operations/phase19-gate-b12.md`
- All 3 PASS conditions evaluated with real evidence (or FAIL documented)
- Owner sign-off recorded (with exact quote of owner's decision)
- TRACKER Decision Log D-number assigned
- PHASE-STATE + HANDOFF + CHANGELOG updated
- Ready to hand off to Coder for 19.9 close-out (if PASS)

## PM note

This gate is smaller than Gate B-11 (which measured across 11 real jobs). Gate B-12 is
about **visual production quality** more than performance — owner's own eyes are the
primary judgment, not just PM's ffprobe. Don't skip the owner-visual step; a media-gate
PASS with a visually-broken karaoke would still be a bad ship.

Expected 1 day PM time + 30-60 min owner time.
