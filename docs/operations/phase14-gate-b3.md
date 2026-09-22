# Phase 14 Gate B-3 — Local-Only Operational Trial (after 14.7 + 14.8)

- **Task:** 14.9 (PM/Tester execution). Protocol: plan §12 Task 14.9 = Phase 13 §8 Task
  13.9 verbatim (same thresholds, no changes) + one real thumbnail and one real YouTube
  package on the winning project.
- **Run date:** 2026-09-22 (00:00–00:33Z UTC, local matrix; probes right after)
- **Code HEAD:** `4542b58` (14.8-b); state HEAD `71e1464`. Runner unchanged since `dec4913`.
- **Evidence (gitignored):** `data/quality_reviews/phase14/gate-b3/` — see §6. The runner
  still writes to its fixed `gate-b2/` paths (trial DB and raw evidence); the PM copied
  the evidence file into `gate-b3/` under a `gate-b3-` name. Same trial DB as Gate B-2;
  every run creates its own project, so earlier rows do not interfere.

## 1. Preflight

| Check | Result |
|---|---|
| Git | `71e1464`, worktree clean, upstream `origin/main`; Coder confirmed idle (stand-still since 14.8-b) |
| Full suite at this HEAD | **884 passed**, 0 failed, 6m32s; `ruff` clean |
| Ollama | `qwen3.5:9b` digest `6488c96fa5fa` (matches Gate A); GPU 1,108 / 12,288 MiB before the run |
| Health at trial start | `mode: local`, `ollama_reachable: true`, `model_present: true`, **`cloud_enabled: false`** (14.7 payload) |
| Cloud | none — no Gemini call is possible in this configuration |

## 2. Primary set — five B1 eight-minute jobs (`AI_MODE=local`)

| Run | Status | Seconds | Total words | All content checks | Repairs (semantic + length-only + final) | Router calls |
|---|---|---:|---:|---|---|---|
| 1 | **complete** | 168.7 | **733** | ✔ all 7 | 5 | 11 / 11 attempts |
| 2 | **complete** | 147.7 | **744** | ✔ all 7 | 4 (incl. 1 length-only: 217 → 80) | 10 / 10 |
| 3 | **complete** | 159.7 | **792** | ✔ all 7 | 6 (incl. 1 length-only: 291 → 161) | 12 / 12 |
| 4 | **complete** | 165.8 | **782** | ✔ all 7 | 4 | 10 / 10 |
| 5 | **complete** | 165.8 | **800** | ✔ all 7 | 4 (incl. 1 length-only: 411 → 151) | 10 / 10 |

Content checks per run: words in 720–880, speaker share 35–65% (observed 45/55, 45/55,
49/51, 47/53, 53/47), no duplicate line, repeated 8-gram < 1%, intro present, outro
present, no unknown speaker id. First durable progress 0.01–0.03 s; longest stage gap
42–69 s (< 5 min); longest job 169 s (< 20 min). **Infra failures 0, `handler_exception`
0, max attempts on any call 1** — no backoff was needed at all.

**Script gate: 5/5 complete, 5/5 pass — PASS by the unchanged Phase 13 rule.** This is
the first time the script gate has passed (Phase 13: 1/5; Gate B-2: 3/5).

### 2.1 Per-section behaviour (25 sections, from checkpoint `metrics_json`)

| Run | Section words | Effective targets | Length-only repair |
|---|---|---|---|
| 1 | 183, 173, 86, 141, 147 | 160, 137, 104, 119, 217 | — |
| 2 | 143, 106, 204, 209, 80 | 160, 177, 216, 230, 138 | s5: 217 → 80 |
| 3 | 180, 167, 99, 161, 184 | 160, 140, 113, 127, 193 | s4: 291 → 161 |
| 4 | 188, 126, 140, 124, 201 | 160, 132, 138, 136, 222 | — |
| 5 | 173, 118, 151, 214, 139 | 160, 147, 181, 216, 144 | s3: 411 → 151 |

Aggregates: within ±15% of nominal **52%** (13/25; Gate B-2: 34.8%); mean deviation vs
nominal −4.7%; **σ 22.9%** (Gate B-2: 55.7%); repair success 45% (9/20; Gate B-2 44%);
total repairs 23; totals in 720–880 **5/5**. The 14.8 length-only repair fired three times
in the primary set and cut every over-length section it targeted (217→80, 291→161,
411→151); the running budget then absorbed the resulting under-shoots. The "2–3× section"
killer from Gate B-2 did not kill a single primary run.

## 3. Samples, learning, media, and the local-mode probes

### 3.1 Samples (informational)

| Run | Status | Words / target | Notes |
|---|---|---|---|
| B1 5-min | complete, 90.4 s | 478 / 500 | all checks pass |
| B1 10-min | error `section_validation_failed`, 81.4 s | — | "more than 5 consecutive lines from speaker … (lines 2–7)" — the 14.8 repair prompt now names the run, the model still did not fix it |
| A2 8-min | complete, 150.7 s | 744 / 720 | all checks pass; 2 length-only repairs (379 → 200, 151 → 80) |
| C1 8-min | error `global_validation_failed`, 126.6 s | — | repeated 8-gram ratio 1.05% ≥ 1% — the global repetition gate, not word count |

### 3.2 Learning — **4/5** (gate requires 5/5 → FAIL)

Four packs complete; one `pack_validation_failed`: `idiom 'go on': phrase not found in
transcript`. The grounding validator refused a pack whose idiom is not in the script —
correct behaviour, real defect in the model's output (Gate B-2: 2/3, same failure class).

### 3.3 Media pipeline (winning project = run 1, 733 words, 43 lines) — **FAIL as declared**

| Step | Result |
|---|---|
| Real Edge TTS per line | 43/43 |
| Mix | HTTP 200; **301.52 s**, −16.01 LUFS; MP3 6,032,204 bytes, `9ec1c22b…` |
| Render | HTTP 200; **304.00 s**; MP4 4,739,714 bytes, h264/aac, `15aa1b1c…` |
| Checks | codecs ✔; audio and video duration ∉ [432, 528] ✘; A/V diff **2.48 s** > 1.0 ✘ |

733 words → 301.5 s = **≈ 146 spoken wpm** (Gate B-2: ≈ 135). The planned pace is 100 wpm.
The owner has not yet decided the pace question (raise targets / slow TTS / longer
silences) or the A/V padding question, so the media gate is reported FAIL against the
declared thresholds, exactly as plan §12 says. Both failures are product decisions, not
pipeline defects; the pipeline itself again ran end to end with zero server errors.

### 3.4 Thumbnail and YouTube on Ollama (`AI_MODE=local`, real calls, no mocks)

Evidence `thumbnail-youtube-local-probe.json`, on the winning project's real script:

- **Thumbnail** (`generate_suggestions`, template `minimal_clean`, 3 variants): **OK in
  8.5 s**, schema-valid pack — e.g. headline "Small Habits, Big Health", supporting text
  "Consistency is Key", five topic keywords, full palette.
- **YouTube package** (`generate_package`): **OK in 7.3 s** — 3 titles (click-worthy /
  educational / SEO variants, all on-topic and B1-labelled), 666-char description, 13 tags,
  estimated chapters.

Both gateway consumers that Gemini used to serve work on the local model with structured
output on the first attempt.

## 4. Decision (Phase 13 Gate B rule, unchanged)

| Gate | Threshold | Result |
|---|---|---|
| Script: 5/5 complete, ≥ 4/5 pass | — | **PASS 5/5, 5/5** |
| Learning: 5/5 deterministic checks | — | **FAIL 4/5** |
| Media: 432–528 s, A/V ≤ 1.0 s, codecs | — | **FAIL** (301.5 s / 304.0 s, 2.48 s; codecs ✔) |
| Timing: first progress ≤ 90 s, section ≤ 5 min, job ≤ 20 min | — | PASS |
| Infra: no server ERROR/traceback | — | PASS (0 infra, 0 `handler_exception`) |

**Overall Gate B-3: FAIL** — on learning (4/5) and media (duration/A-V). The script gate,
which Phases 13 and 14 were built around, passes for the first time. Per plan §12 Task
14.9: D11 (local as primary) therefore **remains an owner override, recorded as such**,
not an evidence-backed promotion; 13.10 still resumes under D11. No threshold was
weakened.

## 5. What the evidence says next (PM recommendation)

1. **Pace (owner decision, blocks the media gate):** measured 135–146 wpm vs planned 100.
   Cheapest honest fix is to recalibrate `CEFR_WORDS_PER_MINUTE` from measured TTS pace
   (B1 ≈ 140) so "8 minutes" means 8 minutes — this raises the B1 8-min target to ≈ 1,120
   words (7 sections), which the pipeline handled at 10 minutes / 1,084 words in Gate B-2.
   Alternative: slow Edge TTS rate (−20%…−25%) keeps word targets. Either is a declared
   change with a re-run, never a threshold edit.
2. **A/V padding 2.5 s:** inspect the renderer's tail padding; if intentional (end card),
   re-declare the threshold with the reason; otherwise trim.
3. **Learning grounding:** 1/5 packs failed on one idiom not present in the transcript.
   Options: a targeted repair that drops/replaces the ungrounded item (the plan already
   allows one learning repair — check whether it fired and what it did), or accept 4/5 as
   the owner's bar. Needs telemetry review of the failed job's `metrics.calls[]`.
4. **Consecutive-lines rule:** the only structural killer left (B1 10-min sample). The
   repair prompt now names the offending lines; a deterministic post-fix (split the run
   by re-attributing every other line to the other speaker) would remove the failure
   class entirely without touching the constant — candidate task, not started.

## 6. Evidence

| File | SHA-256 |
|---|---|
| `data/quality_reviews/phase14/gate-b3/gate-b3-local-20260922T000040Z.json` (copy of the runner's `gate-b2/gate-b2-20260922T000040Z.json`) | `9d3fc92605fbc1d56123d92d82636c1cc31c760741747b5086bc2177298d5d16` |
| `data/quality_reviews/phase14/gate-b3/thumbnail-youtube-local-probe.json` | `0f2b8e9d74dcd21b3de3c227124b8ebb79fda6ca1aa96aabbfb10edc973eac99` |
| `data/quality_reviews/phase14/gate-b3/local-matrix-console.log` | server + runner console; no key, no prompt text |
| `data/quality_reviews/phase14/gate-b2/trial-data/app.db` | trial DB (shared with Gate B-2); winning project `7bc713ac-a4b9-4e4b-8d56-1081086f18b1` |
| MP3 / MP4 of the winning project | `9ec1c22b1a9b5fa3…` / `15aa1b1c8c129f71…` (full hashes in the evidence JSON) |
