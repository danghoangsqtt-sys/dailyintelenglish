# PHASE-STATE — Phase 38: Project layout restructure (D115)

- **Status:** ✅ complete 2026-10-13 (38.1–38.5). Opened 2026-10-13 (owner request: "các mô hình AI tập trung hết trên thư mục backend… bố cục lại thư mục và
  cấu trúc dự án"; layout chosen by the owner). Plan: `docs/structure/RESTRUCTURE-PLAN.md` (made with the new `vp-struct` skill).

| Task | Description | Status |
|---|---|---|
| 38.1 | `app/` → `backend/` with domain packages (`ai/{llm,image,tts,prompts}`, `content`, `media`, `library`, `channel`, `schemas`); image worker out of `scripts/`; codemod imports; path constants; entry points | done |
| 38.2 | `video-renderer/` → `renderer/` | done |
| 38.3 | `.venv`, `.venv-image` recreated from freeze; launch/build scripts | done |
| 38.4 | `models/` → `backend/ai/models/` (after the Phase 39 downloads) | done |
| 38.5 | Docs (README, ARCHITECTURE, AI-GUIDE, `docs/structure/STRUCTURE.md`, CHANGELOG); restart the real app (owner OK) | done |

## Implementation notes (before coding)

- Mapping and codemod: scratchpad `restructure_map.py` (module → module, file names kept) applied by an AST-located rewrite
  of `from … import …` / `import …` statements and a dotted-string rewrite for monkeypatch targets; statements that import
  modules now in different packages are split. Verify with compileall, Ruff, the full suite (baseline 1,686) and Vitest (70).
- Heavy folders are renamed on the same drive only when nothing uses them; venvs are recreated, never moved.

## As built (2026-10-13)

- Worked in a git worktree (`phase38-restructure`, 9 commits), full suite there 1,678 passed; merged by fast-forward after
  the owner's OK; the real app restarted as `uvicorn backend.main:app` on `.venv` (health, image worker, renderer green).
- Recreating the venv from `requirements.txt` exposed three undeclared runtime dependencies that only worked because the old
  venv had them: **librosa** (music pace/mood analysis silently returned nothing), **tzdata** (Gemini quota reset time zone on
  Windows) and **numpy**; plus `transformers`/`huggingface_hub` for the CLIP-budget tests. All declared and pinned.
- The renderer install check compared `package-lock.json` with the `node_modules` folder time; a lockfile-only change (the
  package rename) disabled Generate. It now reads npm's own `node_modules/.package-lock.json`.
- Removed with the owner's OK: `venv/` (5.5 GB), the old `Daily_Intel_English_phase33_auto` worktree (branch kept),
  `.agents/`, `.cache/`. Still to remove: `venv-image/` (used by the running download) and `models/` → `backend/ai/models/`.
- Full suite on the new layout and `.venv`: 1,675 passed + the 10 dependency failures fixed (91/91 on rerun).
- 38.4 done after the Phase 39 downloads: the 95 GB `models/image` folder renamed to `backend/ai/models/image` (same drive);
  `venv-image/` (4.6 GB) removed. Repository root now: backend, frontend, renderer, scripts, tests, docs, data + config files.
