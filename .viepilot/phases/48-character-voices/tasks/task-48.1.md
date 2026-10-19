# Task 48.1 — Catalog giọng Edge TTS và nghe thử độc lập

- **Status:** implemented_verified · 2026-10-16; phase listening acceptance pending.
- **Dependencies:** Không có task mới; đọc SPEC/PLAN và trạng thái hiện tại trước.
- **Requirements:** R10, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Catalog giọng Edge TTS và nghe thử độc lập. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/ai/tts/tts_service.py
- backend/api/tts.py
- backend/schemas/tts.py
- backend/core/constants.py
- backend/core/paths.py
- tests/test_tts_api.py
- tests/test_tts_service.py
- backend/ai/tts/voice_catalog_service.py
- backend/ai/tts/voice_preview_service.py
- tests/test_voice_catalog.py
- tests/test_voice_preview.py
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/SPEC.md
- .viepilot/PLAN.md
- .viepilot/phases/48-character-voices/PLAN.md
- .viepilot/phases/48-character-voices/tasks/task-48.1.md

## File-Level Plan / allowed_files

1. Thêm catalog service lấy metadata bằng API edge_tts đang cài, normalize locale/name/ShortName/gender; chỉ English; filter/search không hứa số lượng cố định.
2. Cache 24h và timeout 15s bằng constants, giữ last-good với stale flag nếu refresh lỗi; không gọi provider trong DB transaction.
3. Thêm GET voices, POST audition và GET opaque preview media theo SPEC, kiểm tra route order để không bị dynamic route cũ nuốt.
4. Preview text tối đa 500 ký tự, tham số dùng validator TTS hiện có; cache riêng data/tts_preview theo fingerprint, TTL24h và cap dung lượng cấu hình. Không dùng endpoint preview script đang ghi line thật.
5. Audit installed edge_tts version và payload thật trước chốt schema. Resolve URL/path chỉ trong preview root; service async hoặc offload tác vụ blocking.

**File mới dự kiến:** `backend/ai/tts/voice_catalog_service.py`, `backend/ai/tts/voice_preview_service.py`, `tests/test_voice_catalog.py`, `tests/test_voice_preview.py`.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Provider metadata/API có thể khác phiên bản mới nhất; dùng nguồn hiện tại và schema tolerant với metadata optional. Không nghe thử sai giọng khi explicit voice không có.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Focused pytest cho catalog success/stale/empty cache/timeout/provider error/filter; metadata không có trường optional vẫn hợp lệ.
2. Preview cùng input reuse riêng, khác voice/text/tham số không reuse; invalid ID/text/path traversal bị từ chối; TTL/cap cleanup không xóa cache sản xuất.
3. Snapshot DB, production TTS cache và mixed files trước/sau audition: không đổi. Một provider smoke có timeout khi mạng sẵn, ghi ID thực tế; không biến network smoke thành unit test bắt buộc.
4. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- Final full pytest: **1,668 passed**, one existing warning,1,171.01s; focused **39 passed**, Ruff/diff clean. Evidence: `data/tmp/evolve-20261016/task48.1-pytest.log`. Commit/push checkpoint follows; no phase PASS claimed.
- Owner feedback: Guy/Andrew differ, but both clearer differences and more natural intonation are required. Four further real auditions (Brian/Christopher/Roger/Ryan) prepared with the same question/example passage at1x speed/pitch0. Gate V48 stays pending. No provider/engine change or unsupported emotion claim.

- Implemented English catalog, last-good disk cache, bounded network timeout, typed audition API and separate TTL/quota preview storage. Targeted tests **39 passed** (including legacy TTS routes); Ruff and diff check clean. One fixture setup issue (pre-created tts_cache directory) corrected; no product failure hidden.
- Live service smoke:47 English voices, Guy/Andrew en-US male auditions generated, each14 word boundaries; both MP3s fully decoded (6.864s/5.256s). Isolated DATA_DIR did not create app.db. Evidence `data/tmp/evolve-20261016/voice-smoke/report.json`. Owner listening question sent asynchronously; this is not phase acceptance.
- Full post-implementation pytest running before task persistence checkpoint. No frontend, project voice semantics or production audio changes in this task.

- Execution preflight: Codex adapter executes inline; no sub-agents. Read AI-GUIDE, SYSTEM-RULES, STACKS and pytest/SQLite/browser summaries. Installed edge_tts is 7.3.1; existing TTSError/ValidationError handlers reused.
- Per-file contract: voice_catalog_service.py owns metadata validation, disk cache and timeout; voice_preview_service.py owns separate bounded audition files and opaque URLs; schemas/tts.py owns typed catalog/preview payloads; api/tts.py delegates new routes; constants.py owns TTL/deadlines/cap. paths.py changes only if a path helper is needed. Tests use fake provider/synth and isolated DATA_DIR; one bounded real-provider smoke is separate.
- Planned verification: `.venv/Scripts/python.exe -m pytest tests/test_voice_catalog.py tests/test_voice_preview.py tests/test_tts_api.py -q`, Ruff, then full pytest before checkpoint commit. Baseline full suite starts before shipping edits; network/provider tests remain isolated.

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
- Baseline before source edits: full pytest **1,636 passed**, one existing Starlette warning, 1,026.86s. Ruff clean. Evidence: `data/tmp/evolve-20261016/baseline-pytest.log`. Real Edge7.3.1 catalog smoke:47 English voices observed,9 en-US male IDs; provider results saved separately, no project writes. CLI adapter detection defaults to Claude on this installation; actual runtime is Codex, so the documented non-Claude inline workflow is used.
