# PHASE-STATE — Phase 38: Project layout restructure (D115)

- **Status:** in progress 2026-10-13 (owner request: "các mô hình AI tập trung hết trên thư mục backend… bố cục lại thư mục và
  cấu trúc dự án"; layout chosen by the owner). Plan: `docs/structure/RESTRUCTURE-PLAN.md` (made with the new `vp-struct` skill).

| Task | Description | Status |
|---|---|---|
| 38.1 | `app/` → `backend/` with domain packages (`ai/{llm,image,tts,prompts}`, `content`, `media`, `library`, `channel`, `schemas`); image worker out of `scripts/`; codemod imports; path constants; entry points | in_progress |
| 38.2 | `video-renderer/` → `renderer/` | planned |
| 38.3 | `.venv`, `.venv-image` recreated from freeze; launch/build scripts | planned |
| 38.4 | `models/` → `backend/ai/models/` (after the Phase 39 downloads) | planned |
| 38.5 | Docs (README, ARCHITECTURE, AI-GUIDE, `docs/structure/STRUCTURE.md`, CHANGELOG); restart the real app (owner OK) | planned |

## Implementation notes (before coding)

- Mapping and codemod: scratchpad `restructure_map.py` (module → module, file names kept) applied by an AST-located rewrite
  of `from … import …` / `import …` statements and a dotted-string rewrite for monkeypatch targets; statements that import
  modules now in different packages are split. Verify with compileall, Ruff, the full suite (baseline 1,686) and Vitest (70).
- Heavy folders are renamed on the same drive only when nothing uses them; venvs are recreated, never moved.
