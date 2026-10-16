# Task 48.4 — Voice picker trong hồ sơ nhân vật và Audio Studio

- **Status:** implemented_verified · 2026-10-16; source UI complete, final phase QA/documentation separate.
- **Dependencies:** 48.1, 48.2, 48.3
- **Requirements:** R10, R13, R14, R15.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** shared picker implemented and technically verified in profile/Audio Studio.

## Objective

Voice picker trong hồ sơ nhân vật và Audio Studio. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- frontend/pages/characters.html
- frontend/pages/step4_tts.html
- frontend/static/js/character_profiles.js
- frontend/static/js/character_selector.js
- frontend/static/js/step4_tts.js
- frontend/static/js/api.js
- frontend/static/css/style.css
- frontend/static/css/voice_picker.css
- tests/test_character_profiles_browser.py
- tests/test_tts_audio_browser.py
- frontend/static/js/voice_picker.js
- tests/test_voice_picker_browser.py
- frontend/static/js/step5_video.js
- tests/test_video_studio_browser.py
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.4.md

## File-Level Plan / allowed_files

Owner feedback2026-10-16: all four Brian/Christopher/Roger/Ryan comparisons are good; owner wants about20 voices for more characters. Show the complete actual English catalog (currently47), not just these four; searchable locale/gender filters and same-text auditions must work beyond the initial voices. Do not fabricate entries if provider availability changes.

1. Picker component vanilla dùng chung: search, locale/gender filters, tên+ID, stale indicator, nghe câu mẫu/câu nhập và save.
2. Profile hiển thị default; Step 4 hiển thị actual project voice và nút áp dụng default profile. Character selector cho biết voice snapshot khi cast.
3. Cảnh báo trùng ID giữa speaker nhưng không cấm. Thông báo rõ đổi giọng sẽ cần tạo lại audio/video phụ thuộc.
4. Disable/double-submit lock khi save/preview, bỏ response cũ bằng request token, stop playback cũ, serialize/trailing save và dirty navigation guards.
5. Xử lý offline/voice unavailable/409 bằng thông báo cụ thể và thao tác retry/reload; không hiển thị saved khi request chưa thành công.

**File mới dự kiến:** `frontend/static/js/voice_picker.js`, `tests/test_voice_picker_browser.py`.

### Execution refinement (before shipping code)

- Shared `voice_picker.js` owns catalog filtering/count, same-text auditions, draft/save/reload status and cancellation tokens. Dedicated `voice_picker.css` is linked only on Characters/Step4, avoiding changes to global layout rules.
- Profile picker lives outside the introduction autosave form. Capture profile IDs in async callbacks, guard late profile loads and preserve voice drafts across asset refreshes. Switching profiles with unsaved voice edits uses the existing ConfirmDialog; serialize optional detail saves before switching so a late save cannot write another profile.
- Step4 keeps its existing numeric sliders. Serialize their autosaves, update voice revision after each save, disable voice selection while parameter saves are pending, and disable generation while any voice edit is unsaved. Explicit profile apply preserves project numeric settings. Duplicate-voice notice is dismissible.
- Generate All requests reuse_cached for unchanged lines; single-line preview still forces generation. Clear affected UI playback and mixed-result readiness after a persisted voice/parameter change. Show the actual project voice above the picker, independent from profile defaults.
- Browser verification covers at least20 selectable entries, locale/gender/search, same-text preview with late responses, save/reload, error409 draft preservation, profile/project isolation and explicit profile apply. Use actual provider metadata for the real smoke; synthetic UI catalogs are labeled fixtures in tests.
- Full gate stopped at1553 pass on a second Step5 startup-readiness race: workspace is shown before async visuals/scenes finish and renderer status/Generate locks are applied. Extend bounded scope to move only workspace/loading visibility to the end of init in `step5_video.js`. Add a deterministic delayed-visuals browser regression proving workspace remains loading until controls are ready. This addresses the actual premature-ready UI state underlying the earlier isolated assertion race; do not change rendering behavior. Run both Video browser modules and voice/browser regressions, JS syntax and full suite again before checkpoint.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Giao diện summary có thể hiển thị default trong khi project dùng override; luôn label rõ hai cấp và dùng resolved project data.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Browser chọn hai giọng, nghe thử, save/reload profile/project; tên/ID displayed khớp response.
2. Race preview A chậm/B nhanh không phát A, save lỗi/409 không mất edit; keyboard/focus/loading hợp lý.
3. Sửa profile không tự đổi Step 4 project; apply profile có tác dụng và cho thấy stale; duplicate warning dismiss được.
4. Node JS syntax cho file sửa và regression browser characters/Audio Studio.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- Combined final browser verification: **45 passed** across Video Studio, visual modes, picker, profiles, Audio Studio and TTS shell; includes the delayed-init regression. Full suite finished **1704 passed in916.89s**; Ruff, all six JS syntax checks and diff check clean.
- Shared picker and profile/Step4 integration implemented: complete catalog/count/search/filters, same-text audition, draft/reload/save/error states, request tokens and playback cancellation; pinned profile/project display, explicit profile apply and dismissible duplicate notice. Generate All uses validated cache reuse and clears affected UI playback after changes. Existing numeric saves are serialized with voice saves; optional profile details save to captured profile IDs.
- Isolated browser verification **30 passed**: nine new voice flows plus existing character, Audio Studio and TTS shell regressions. Includes20-entry fixture (explicitly synthetic UI metadata, not a provider availability claim), filter/search/save/reload, late preview/profile responses,409/offline refresh, profile/project isolation, explicit apply, numeric-save race and dirty/pending-save navigation guards. Screenshots reviewed in both pages; refined control sizing/gaps. Candidate applied verbatim after task48.3 durable checkpoint. Ruff, all five changed/new JS syntax checks and diff checks clean. Full workspace **1704 passed** in **916.89s**, one existing Starlette warning. Initial gate1553 pass/1 failure exposed Step5's premature-ready state; a delayed-visuals test failed deterministically on the old source, then passed after moving workspace visibility after init controls. Full final evidence: `data/tmp/evolve-20261016/task48.4-pytest-r2.log`. All six JS syntax checks clean. Live unmocked sandbox UI also showed47 actual choices, saved/reloaded Christopher and preserved project Brian/Roger plus complete media, with zero JS errors. Real media exploratory run:11.54s speech,28.778667s outputs,1280×720 and1080×1920, full decode successful; embedded-speech correlations0.985/0.996. Actual screenshots and reports under `data/tmp/evolve-20261016/voice-media-dbc2312672/`. No real owner data or EXE/release changed; final phase QA/docs remains task48.5.
