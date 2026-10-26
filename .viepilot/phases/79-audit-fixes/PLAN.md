# Phase 79 — Audit fixes (2026-10-26)

Owner request (`/vp-audit`): "xem dự án còn vị trí nào bất hợp lý và bug tiến hành phân tích và sửa lỗi" — find unreasonable spots and bugs, analyse and fix them. Doc-first: this plan is committed before code.

Evidence: the installed app's `data/logs/desktop.log`, the Office Startup data folder, a review of the security surface, Ruff bug rules (no real hits).

## Tasks

1. **79.1 BUG-053** image-worker failures → typed error with a plain message. Paths: `backend/ai/image/engine.py` (`ImageWorkerError`, `explain_worker_error`), `backend/api/thumbnail.py` (catch in topic picture + AI scenes), `frontend/static/js/i18n_vi.js`, `tests/test_thumbnail_worker_errors.py` (new).
2. **79.2 BUG-054** remove the previous attempt folder after a render is committed as current. Paths: `backend/media/video_service.py` (`remove_superseded_attempt(old_path, new_path, project_id)`), `backend/api/video.py` (episode + vertical), `backend/api/shorts.py` (clip), `tests/test_render_attempt_cleanup.py` (new). Only a folder whose name is a 32-hex attempt id, inside `data/video/<project>/` (or the clip folder), different from the new one; failures never delete.
3. **79.3 ENH-056 + BUG-055 + small UI fix**: CORS limited to the app's own origins, Host header limited to local names (DNS rebinding) unless the owner set a LAN host; filter the harmless proactor reset traceback; `dashboard_channel.js` `el()` sets `aria-*` as attributes. Paths: `backend/main.py`, `frontend/static/js/dashboard_channel.js`, `tests/test_local_api_exposure.py` (new).
4. **79.4 ENH-055 + records**: ROADMAP Phase 49 / 76 rows match TRACKER; audit report; full pytest; rebuild/install only if the owner asks.

## Risks

- TestClient uses host `testserver`; it stays allowed. A wildcard `APP_HOST` (0.0.0.0 / ::) means the owner chose LAN access: the Host check is then off.
- Deleting media: only the attempt folder the database pointed at before the new commit, never the folder the database points at now; existing orphans are listed, not deleted.
