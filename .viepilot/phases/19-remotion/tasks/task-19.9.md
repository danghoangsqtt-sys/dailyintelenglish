# Task 19.9 — Close-out: Remotion becomes the default renderer; 1.2.0-beta (doc-first card)

## Authority

Plan `docs/implementation/phase-19-remotion.md` §19.9. Gate B-12 ended PARTIAL: media 6/6 PASS
and owner visual PASS, but audio FAIL because of the Edge TTS voice, which is not a renderer
issue. Owner D38 (2026-09-30) then stopped Phase 21 and kept Edge TTS, and recorded: "Per
Amendment A, Phase 19.9 flips the Remotion default on its own." Run via `/vp-auto` (owner:
"tiếp tục tự động không cần hỏi thêm").

## Paths

- `app/core/config.py` (`VIDEO_RENDERER` default)
- `frontend/static/js/step5_video.js` (stored-renderer default)
- `tests/` (tests that relied on the old default)
- `CHANGELOG.md` (`[Unreleased]` → `[1.2.0-beta]`), `README.md` (current version)
- `.viepilot/` state files (Phase 19 closed, tag `die-vp-p19-complete`)

## File-Level Plan

- **config:** `VIDEO_RENDERER` default `"ffmpeg"` → `"remotion"`, with the comment updated.
  The kill switch semantics are unchanged: `DIE_VIDEO_RENDERER=ffmpeg` still forces ffmpeg
  regardless of the request (I36). Same pattern as Task 18.11.
- **step5_video.js:** `readStoredRenderer()` defaults to `"remotion"` when nothing is stored.
  It is still only used when `remotionConfigured`; otherwise the toggle stays Standard. A choice
  the owner already stored is kept.
- **tests:** update only the assertions that relied on the old default implicitly. Tests that set
  `VIDEO_RENDERER` explicitly keep proving both directions of I36.
- **CHANGELOG:** `[Unreleased]` becomes `## [1.2.0-beta] - 2026-10-05`, with a short headline (Remotion
  by default; AI visuals, scene library, storyboard behind their own owner gates). **README:**
  current version 1.2.0-beta.
- **State:** Phase 19 PHASE-STATE/ROADMAP/TRACKER/HANDOFF marked closed; tag
  `die-vp-p19-complete`. No `v1.2.0-beta` release tag: release tagging stays an owner action.

## Verification

Full suite green; vitest/tsc unaffected; `GET /api/video/health` unchanged. A fresh Step 5 with
Remotion installed and nothing stored shows Enhanced selected.
