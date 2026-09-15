# Task 3.1: Documentation

## Meta
- **ID**: 3.1
- **Phase**: 3
- **Status**: done (2026-09-15)
- **Priority**: high (first Phase 3 task, opens the phase)
- **Assignee**: PM (Claude Code)

## Doc-First Gate

User approved closing Phase 2 and moving to Phase 3 at a `/vp-auto` control point
(2026-09-15). ROADMAP.md's "3.1 Documentation" bullet has 4 items, all currently unchecked:
`README.md`, `docs/prompt-guide.md`, `docs/tts-setup.md`, `docs/api.md`. This task covers
all 4 as one doc-first slice since they're independent, additive doc files with no shared
code risk (same class of decision as Task 2.3's original multi-item ROADMAP bullet, but
these don't need the same sub-task split since none require app code changes).

## Objective

1. **README.md** — bring current: reflect Phase 1 + Phase 2 completion (currently only
   lists Phase 1 shipped features), correct test count, add Phase 2 highlights (UI
   redesign, quality-testing findings fixed), keep the existing bilingual (VI feature
   descriptions + EN structure) style and existing badges/sections.
2. **`docs/prompt-guide.md`** (new) — how to customize the Gemini prompt templates:
   `prompts/script/` (base + 10 genre blocks + 6 CEFR blocks, Jinja2 variables available),
   `prompts/learning/learning_pack.txt`. Document the CEFR-ceiling-vs-language-toggle
   precedence rule and solo-speaker override (real behavior in `script_service.py` /
   `prompt_loader.py`, not invented).
3. **`docs/tts-setup.md`** (new) — Edge TTS is the sole official engine (2026-09-13
   decision); document `EDGE_TTS_VOICE_MAP` (10 accents × 3 genders), the known
   Scottish/British voice-id duplication (upstream limitation, disclosed in Step 1 UI per
   Task 2.5c), and OmniVoice's status (downloaded/verified but permanently not integrated
   — real API is voice cloning, not text-described voice design; kept only as an honest
   tested fallback branch that always raises "model not loaded").
4. **`docs/api.md`** — auto-generated from the real FastAPI OpenAPI schema (ROADMAP's own
   wording), not hand-written prose that can drift. New `scripts/generate_api_docs.py`
   loads the app via `TestClient` (no live server needed), reads `app.openapi()`, and
   renders one Markdown section per route grouped by tag (method, path, summary,
   request/response models) to `docs/api.md`. Re-run this script instead of hand-editing
   `docs/api.md` whenever routes change — this is the actual meaning of "auto-generated,"
   verified against a real generated file, not an assumption.

## Allowed files
- `README.md`
- `docs/prompt-guide.md` (new)
- `docs/tts-setup.md` (new)
- `docs/api.md` (new, generated output — not hand-edited after generation)
- `scripts/generate_api_docs.py` (new)
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/phases/03-review-documentation/PHASE-STATE.md` (state tracking)

## Verification
- `venv\Scripts\python scripts\generate_api_docs.py` runs clean and produces a non-empty
  `docs/api.md` covering every mounted router (`projects`, `learning`, `tts` incl. preview,
  `audio`, `video` incl. templates, `music`, `thumbnail`, `youtube`).
- Manually spot-check `docs/prompt-guide.md` and `docs/tts-setup.md` against the real
  source files they describe (`prompt_loader.py`, `constants.py::EDGE_TTS_VOICE_MAP`) —
  no invented behavior.
- `README.md` test count matches the real `pytest tests/ -q` result from this session.
- No `app/`, `frontend/`, or `tests/` files touched — pure documentation task.

## Implementer Evidence (2026-09-15)

- `venv\Scripts\python scripts\generate_api_docs.py` → `Wrote D:\DataAdmin\Daily_Intel_English\docs\api.md (49 routes documented)`, real run, real output file (not hand-written).
- `ruff check scripts/generate_api_docs.py` → `All checks passed!`
- Full suite re-run (also serves as Phase 2's close-out gate, since no app code changed since the last commit): `venv\Scripts\python -m pytest tests/ -q` → `533 passed, 2 warnings in 431.53s` — the previously-tracked Gemini-retry timing flake did not recur.
- `docs/prompt-guide.md`'s CEFR-ceiling-vs-toggle and solo-speaker claims cross-checked
  directly against `prompts/script/script_base.txt`'s actual Jinja2 blocks (Precedence
  section, `{% if num_speakers == 1 %}` branches) — not invented.
- `docs/tts-setup.md`'s voice-map table cross-checked directly against
  `app/core/constants.py::EDGE_TTS_VOICE_MAP` (all 10 accents × 3 genders transcribed
  exactly) and `app/services/tts_service.py`'s real OmniVoice fallback code.
- Files touched: `README.md`, `docs/prompt-guide.md` (new), `docs/tts-setup.md` (new),
  `docs/api.md` (new, generated), `scripts/generate_api_docs.py` (new), plus
  `.viepilot/ROADMAP.md`/`TRACKER.md`/`HANDOFF.json`/phase-state files and
  `CHANGELOG.md` (state tracking + a retroactive Task 2.6 entry that was missing) — no
  `app/`, `frontend/`, or `tests/` production files touched, matching the Allowed files
  list above.

## PM Acceptance (2026-09-15)

Accepted — all 4 ROADMAP items delivered, every factual claim in the new docs
cross-checked against the real source files it describes rather than written from
memory, and the full test suite confirmed green (533/533) before closing. This also
closes Task 3.1 and satisfies the doc-first/git-persistence gates for Phase 2's
formal close-out (see TRACKER.md Decision Log, 2026-09-15).
