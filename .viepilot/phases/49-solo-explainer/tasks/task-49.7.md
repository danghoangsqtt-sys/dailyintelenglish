# Task 49.7 — Player preview và editor duyệt bố cục trong Step 5

- **Status:** implemented_verified · 2026-10-16; owner acceptance remains separate.
- **Dependencies:** 49.3, 49.6
- **Requirements:** R03, R04, R05, R06, R07, R11.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** implemented within the authorized plan; technical verification below does not imply owner acceptance.

## Objective

Player preview và editor duyệt bố cục trong Step 5. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- frontend/static/js/storyboard.js
- tests/test_explainer_editor_browser.py
- frontend/pages/step5_video.html
- frontend/static/js/step5_video.js
- frontend/static/js/api.js
- frontend/static/css/style.css
- renderer/package.json
- renderer/package-lock.json
- renderer/tsconfig.json
- .gitignore
- frontend/static/solo-preview/player.js
- frontend/static/solo-preview/player.css
- renderer/src/Episode.tsx
- renderer/src/types.ts
- frontend/static/js/explainer_editor.js
- renderer/scripts/build-preview.mjs
- renderer/preview/entry.tsx
- renderer/preview/PreviewEditor.tsx
- renderer/src/SoloScene.tsx
- renderer/src/Presenter.tsx
- renderer/src/ExplainerVisual.tsx
- renderer/src/CaptionBand.tsx
- tests/test_explainer_editor_browser.py
- backend/api/explainer.py
- backend/library/explainer_service.py
- backend/library/explainer_media.py
- renderer/src/soloTypes.ts
- backend/library/presenter_asset_plan.py
- frontend/static/js/character_profiles.js
- frontend/pages/characters.html
- tests/test_presenter_asset_plan.py
- tests/test_presenter_assets_browser.py
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.7.md

## File-Level Plan / allowed_files

1. Thêm @remotion/player đúng bản Remotion lockfile, khai báo direct bundler dependency khi cần, build vào frontend/static/solo-preview; include preview TS trong typecheck.
2. Shared SoloScene/Presenter/ExplainerVisual/CaptionBand cho Player và render. Trích caption band có giới hạn, giữ classic props/defaults và paging Phase 47.
3. Editor timeline/audio seek, chọn aspect, vị trí/size/gesture, loại minh họa/asset và vùng quan trọng; hiển thị issues.
4. Media resolver dùng API URL cho preview và staged URL cho render; frame origin, font, safe area dùng chung. Không cần dev server.
5. Serialize/trailing saves, UI xử lý409, locks/unlock/regenerate only unlocked; duyệt toàn plan sau validation.
6. Giữ Step 5 classic; mount/unmount widget dọn playback/listeners/object URLs, bỏ response cũ.

**File mới dự kiến:** `frontend/static/js/explainer_editor.js`, `renderer/scripts/build-preview.mjs`, `renderer/preview/entry.tsx`, `renderer/preview/PreviewEditor.tsx`, `renderer/src/SoloScene.tsx`, `renderer/src/Presenter.tsx`, `renderer/src/ExplainerVisual.tsx`, `renderer/src/CaptionBand.tsx`, `tests/test_explainer_editor_browser.py`.

**Build outputs dự kiến:** `frontend/static/solo-preview/player.js` và `player.css` (CSS nếu cần). Build từ source bằng script; ignore output tái tạo được trong git, đóng gói từ bước build rõ ràng. Không commit node_modules hoặc dựa vào bundle tồn tại sẵn.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

### Owner refinement2026-10-16

Owner confirms no real front21 art exists and asks21 clearly labeled upload slots with strict detailed per-action outside-AI prompts. Enhance existing front cards (do not duplicate profiles/native packs): names/instructions per closed/open/blink, approved parent input, full-body camera/identity/clothes/scale invariants, exact finger counts/viewer directions, negative constraints and per-slot checklist. Preserve upload/review race guards. Add a read-only draft preview props endpoint with verified front/images/audio and geometry outside DB lock; it does not approve content. Media helper resolves preview URLs vs production staging; share schema/components and frame origin. Pin player exactly to installed Remotion4.0.529, direct esbuild0.28.1, build static IIFE for vanilla mount/unmount. No dev server or runtime Node dependency for Player playback.

staticFile URL và frame origin có thể khác giữa Player/render; truyền resolved media refs và frame offset rõ ràng.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Install lock/typecheck/Vitest/build preview; Player mở fixture không có dev server.
2. Browser edit → save → reload → regenerate giữ locks; layout hai aspect riêng; dirty navigation/409/error không mất sửa.
3. Preview có sprite/ảnh/sơ đồ/thẻ chữ, highlight caption và audio thật; seek cùng frame cho cùng hình.
4. Caption suite104 hiện tại và Step 5 classic browser regression còn pass; so Player/final frames ở49.8.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [x] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [x] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [x] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: initial plan recorded before implementation; final evidence below.

## Final technical verification —2026-10-16

Strict per-action21 upload/prompt cards and static shared Player editor, serialized/trailing autosave, dirty/conflict guards and operation locks. Actual source/frozen UI,3 browser race cases, native/front regression and no-audio editor/reload checked.

Feature full pytest 1867 passed in779.20s. Post-Windows-UTF8 full run:1862 passed,5 legacy subprocess mock-signature failures; all40 video/bridge checks passed in7.95s after updating those5 mocks, with no further application-code change.124 renderer tests, TypeScript/Ruff/JS/diff clean. Actual Player/StillFrame6 comparisons, four decoded fixture MP4s, two frozen restarts and production landscape/portrait/SRT verified. Real owner art/V49 acceptance pending.

[Evidence report](../../../../docs/operations/phase49-solo-explainer.md). Git persistence is recorded after the implementation checkpoint; no owner acceptance or release tag implied.
