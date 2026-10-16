# Task 48.5 — Gate V48: giọng thật, hồi quy và hướng dẫn

- **Status:** implemented_verified · 2026-10-16; V48 technical evidence complete and owner listening response recorded.
- **Dependencies:** 48.4
- **Requirements:** R10, R12, R13, R14, R15.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** source voice feature verified and documented; release/installed EXE unchanged.

## Objective

Gate V48: giọng thật, hồi quy và hướng dẫn. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- README.md
- docs/user/windows-installation.md
- scripts/generate_api_docs.py
- docs/api.md
- tests/test_tts_service.py
- tests/test_character_profiles_browser.py
- docs/user/character-voices.md
- docs/operations/phase48-character-voices.md
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.5.md
- .viepilot/phases/48-character-voices/SUMMARY.md
- .viepilot/phases/48-character-voices/SPEC.md
- .viepilot/phases/48-character-voices/PLAN.md
- .viepilot/SPEC.md
- .viepilot/PLAN.md
- .viepilot/phases/49-solo-explainer/PHASE-STATE.md
- .viepilot/phases/49-solo-explainer/PLAN.md
- .viepilot/phases/49-solo-explainer/SPEC.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.1.md
- .viepilot/phases/49-solo-explainer/tasks/task-49.2.md

## File-Level Plan / allowed_files

1. Tạo hai profile thử nghiệm cùng gender/locale nhưng hai voice ID khả dụng khác nhau; dùng project/DB sandbox, không sửa audio dự án thật.
2. Chạy luồng audition → lưu profile → cast → mix → render ngắn; lưu actual resolved voice IDs, timing hashes và ảnh UI.
3. Cập nhật user guide và API docs từ OpenAPI thật, ghi rõ mạng cần cho Edge TTS, profile default vs project override và invalidation.
4. Ghi technical verification và owner listening acceptance riêng. Phase 48 chỉ complete sau owner/PM acceptance, không coi synthesized success là nghe tự nhiên.
5. Không tự publish1.5; Phase 49.1 phụ thuộc V48 theo PLAN.

**File mới dự kiến:** `docs/user/character-voices.md`, `docs/operations/phase48-character-voices.md`.

### Execution refinement before documentation edits

- Reuse the completed real-provider sandbox evidence recorded under task48.4:47 catalog voices, two male/en-US concrete voices, isolated auditions, persistence, cached word timings,11.54s speech, both production aspect renders and complete decode. Owner already accepted Brian/Christopher/Roger/Ryan; retain that response as listening acceptance without reopening the same question.
- Copy reviewed guide/report drafts, distinguish new source features from published EXE1.4.0-rc.1 in README/install guide, and regenerate API reference from the actual app without starting the owner instance. Add a phase SUMMARY and update only the listed planning/state artifacts after final gates pass.
- Run full pytest again after documentation changes, Ruff/diff, and verify documentation links/API output. Renderer104/TypeScript and real media evidence remain applicable because no renderer/media implementation changes in this task. Review three CEFR script samples and exercise the sandbox YouTube package/export handoff required by phase rules; record exact limits rather than claiming fresh AI generation.
- Once V48 evidence is complete and persisted, open49.1's existing bounded plan/state. No Solo shipping implementation or owner DB migration until that checkpoint.
- Owner's new demo choice, **Hoang — Why do we build habits?**, is recorded in Phase49 state and front-task planning. Its isolated front candidate preparation remains separate from shipping source while Phase48 regression runs.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Không thể dùng checksum khác nhau để kết luận chất giọng đạt yêu cầu; owner nghe quyết định. Không overwrite source audio thật để dựng evidence.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Full pytest/Ruff theo gate dự án; renderer regression/typecheck nếu bridge/freshness sửa liên quan. Không claim pass trước khi có log.
2. Nghe thử hai actual voices để owner nhận ra khác biệt và duyệt; code chỉ xác minh IDs, audio decode/timings.
3. Provider error/stale catalog/no silent fallback demo, save/reload/copy và unchanged classic defaults.
4. Evidence có commands/results/limits; các gate cũ và release1.4.0-rc.1 giữ nguyên.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- Final full pytest **1704 passed in901.80s** (one existing Starlette warning), Ruff/diff clean. API reference regenerated from actual OpenAPI:172 routes. Guides and newly added local links verified. Task48.4's45 final browser regressions, real47-entry UI and104 renderer/TypeScript checks remain applicable; no implementation changed in this documentation task.
- Real Edge Brian/Roger auditions, cast/persist/cache/words,11.54s mix and28.778667s both-aspect H264/AAC outputs fully decoded; speech matches source above0.98. Follow-on production thumbnail/favorite/YouTube ZIP API verified CRC and real video byte identity (3,559,565bytes); metadata/suggestions explicitly editorial fixtures, no fresh AI or publish.
- Read/reviewed archived A1/B1/C1 scripts; vocabulary/naturalness and an over-absolute health claim recorded as limits, not a CEFR or owner quality certification. Existing script/full-package regression remains covered by the full suite.
- Owner accepted Brian/Christopher/Roger/Ryan and requested about20 choices; actual catalog47 meets the requested choice count with auditions. Source features documented separately from published EXE. V48 evidence: docs/operations/phase48-character-voices.md; no new release or owner DB write.
- Next authorized task49.1; isolated70-test Solo candidate and read-only online-backup migration exploration available, not yet shipping. Owner demo: Hoang — Why do we build habits?; real front21 still required before V49.
