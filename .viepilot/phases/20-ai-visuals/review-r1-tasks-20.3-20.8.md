# Phase 20 — PM review r1 of Tasks 20.3–20.8 (implementer branch `feature/phase20-ai-visuals` @ `e79e770`)

- **Reviewer:** Claude Code session (PM), 2026-10-01. AR-06: the implementer does not self-approve.
- **Verdict:** **changes requested**. The fixes F1–F5 below were to go back to the implementer
  as one round.
- **Update (2026-10-01):** the owner moved implementation to Claude (*"tôi không tin tưởng gpt
  sol code dự án này nữa bạn hãy code và chỉnh sửa dự án này"*, "I no longer trust GPT to code
  this project; you code and fix it"). Claude merged `feature/phase20-ai-visuals` into
  `claude/admiring-knuth-r1d8vc` and fixed F1–F5 there.
  - **Verification:** independent. A Codex runbook runs on the owner's machine (tests, fake and
    real smoke), then the owner's Gate B-14 visual sign-off. It stands in for AR-06 review of
    Claude's own fixes.

## What was verified

- **Tests (cloud re-run on `e79e770`).** Full pytest: 1266 passed. The 2 failures are the known
  cloud-only environment failures (see task 20.2d), and both also fail on the base.
  - `test_tts_word_boundary` needs the network.
  - `test_learning_generate_defaults_inspector_to_first_active_item` is a browser flake.
  - `tsc --noEmit`: clean. `vitest`: 37/37.
- **Spec conformance.** Read in full: engine, worker change (Errata E1), recipes, geometry,
  jobs/runner, library, project visuals, API, models, Remotion props, `visuals.ts`, thumbnail,
  Step 5/6 and the `/characters` UI.
  - Prompt strings and §2.4 numbers match the spec.
  - The geometry is a faithful port of `spike_character_v6.py`.
  - The worker change is exactly E1.
  - Content endpoints are path-guarded.
  - No `innerHTML` with user data.
  - No new dependencies.

## Findings

### F1 (blocking): the AI background flashes to midnight between every caption line

`video-renderer/src/visuals.ts::visualBackgroundForFrame` looks up the line with
`startSec <= t < endSec`.
- The audio mix puts a 300 ms / 500 ms silence between lines (Task 1.6b), so for 9–15 frames
  after every line the function returns `current: null`. The full-bleed shot vanishes and the
  midnight background flashes in.
- The zoom also restarts at 1.00 on every line, so when two consecutive lines share a shot the
  picture jumps from 1.04 back to 1.00.

Probe on `e79e770`: lines `[0–2 s]`, `[2.5–4.5 s]`, both shot `one`.
- frame 68 (in the gap) → `current: null`;
- frame 59 → scale 1.039;
- frame 75 (same shot) → scale 1.0, no crossfade.

**Required behaviour:**
- **Hold through gaps.** The active line for the background is the **last line whose
  `startSec <= t`**: it holds through gaps and after the last line. Before the first line's
  `startSec` it is `null`.
- **Runs.** A *run* is a maximal sequence of consecutive lines with the same `lineShots` id;
  `null` is its own id.
  - `runStart` = the first line's `startSec`.
  - `runEnd` = the last line's `endSec`.
- **Crossfade only at a run start.** `previous` = the previous run's shot URL (or `null`);
  `opacity = min(1, (frame - round(runStart * fps)) / 10)`.
- **Zoom per run.** `scale = 1 + 0.04 * clamp((t - runStart) / max(1/fps, runEnd - runStart), 0, 1)`.
  It is continuous across lines of the same run and stays at 1.04 in a trailing gap.
- **vitest:**
  - a gap holds the shot (never `null`);
  - the same shot across two lines → no crossfade, and the scale is non-decreasing across the
    boundary;
  - a shot change → crossfade starting at the new run;
  - before the first line → `null`;
  - after the last line → the last shot is held.

### F2: shot rows stay `pending` forever after a cancel or an app restart

- **Cancel.** `project_shots` / `shot_regenerate` re-raise `JobCancelled` without touching the
  shot rows.
- **Restart.** `recover_running` marks the job `error` but not its rows.
- **Result:** cards with no image and no explanation, forever.

**Required:**
- **On `JobCancelled`:** set this job's still-`pending` rows to `status='error'`,
  `error='cancelled'` (completed rows stay `complete`, per §5.3), then re-raise.
- **On startup:** set every `project_shots` row with `status='pending'` to `error` /
  `'interrupted by app restart'`. Shot rows only become `pending` inside a running job, so any
  `pending` row at startup is stale. Register this next to the runner start in `lifespan`, or
  do it inside the visuals startup.
- **Tests:** both paths.

### F3: a hung worker can keep its GPU memory after the session ends

`_WorkerProcess.close()` calls `process.wait(timeout=120)`. On `TimeoutExpired` the process is
never killed: it keeps its VRAM while the lease is released.

**Required:**
- On `TimeoutExpired`: `process.kill()` and then `process.wait()`.
- Kill the process too when the handshake fails.
- **Unit test** with a stubbed `Popen`.

### F4: unlock is accepted from any status

`unlock_character` sets `status='sheet'` even for a `draft` or `candidates` character (no sheet
exists).

**Required:**
- 409 `"Character is not locked"` unless `status == 'locked'`.
- **API test.**

### F5: no way to cancel a running image job from the UI

- A real project shot set took 598 s in the implementer's smoke. The cancel API exists
  (`POST /api/visuals/jobs/{id}/cancel`, §5.3), but neither `/characters` nor the Step 5
  section exposes it.

**Required:**
- **The button.** A "Cancel" button next to the progress (Step 5 visuals section and
  `/characters`):
  - visible while the polled job is `pending`/`running`;
  - it calls a new `Api.cancelImageJob(id)`.
- **The result.** A job that ends `cancelled` shows a neutral status message, not an error.
- **Checks:** `node --check` on the touched JS. An API test asserting that cancel on a pending
  job returns `cancelled`, if one does not already exist.

## Open question from 20.8 (the third person in the real `duo_close`)

- **Answer: no recipe change in this round.** §2 stays frozen until Gate B-14 evidence exists.
- **At Gate B-14 the owner uses the Step 5 raw/final toggle on the duo shots:**
  - **Third person already in `raw`:** a base-recipe issue. The PM designs a gated prompt
    or negative tweak (spike first, then a spec erratum).
  - **Only in `final`:** the regional refine introduced it. Compare with
    `DIE_VISUALS_DUO_REFINE=false`; if refine-off is better, the PM flips the default
    (§2.7). Otherwise the PM tightens the refine mask.
- **Outfit-colour drift is judged the same way** (raw vs refined).

## Non-blocking notes (no action this round)

- **Stable URLs.** Scene preview URLs are stable per scene (no cache-buster after a re-preview).
  Shot URLs already carry `&seed=`.
- **Smoke artefacts.** The smoke keeps only the stills. Gate B-14 judges shots in the app,
  where raw and final are both kept.
