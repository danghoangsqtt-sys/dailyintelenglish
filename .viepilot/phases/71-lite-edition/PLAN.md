# PLAN — Phase 71: Lite edition for low-end machines (ENH-053)

Status: execution_authorized 2026-10-22 — the owner chose auto-detection plus a Lite package, hiding only the four local AI picture features.

| Task | Scope |
|---|---|
| 71.1 | `backend/core/edition.py`: the edition (`build-info.json` `edition`, `DIE_EDITION` for source runs; default `full`), the setting `local_image_ai` = `auto` / `on` / `off` in `app_settings`, and the decision: `on` shows, `off` hides, `auto` hides on Lite and, on Full, hides when there is no NVIDIA GPU with ≥ 8 GB VRAM (the image lease's own threshold) or no `.venv-image`. API `GET/PUT /api/system/capabilities` with the reason |
| 71.2 | Frontend: `capabilities.js` sets `data-local-image-ai` on the page; the four features carry `needs-local-gpu` and are hidden by CSS when off (scene picture button in Character Library → Scenes, "Draw illustrations" in Step 5, the topic picture row and the AI scene panel in Step 6); the AI scene template leaves the Step 6 template list. Settings → General gets "AI pictures on this computer" (Auto / Show / Hide) with the edition and what was detected. EN + VI |
| 71.3 | Build: `build_exe.ps1 -Edition lite` writes `edition` into `build-info.json`; version 1.6.0; the Settings app version line shows the edition |
| 71.4 | Tests: the decision table (edition × setting × GPU), the API, a browser test (Lite hides the four features, the switch shows them again); full pytest + Vitest |
| 71.5 | Release 1.6.0: CHANGELOG, guide (Lite package for the laptop), build Full + Lite, verify, install Full here, hand-over folder with the Lite package, tag, push |
