# Task 48.3 — Fingerprint TTS, invalidation và bảo vệ media tốt cũ

- **Status:** planned · 2026-10-16.
- **Dependencies:** 48.2
- **Requirements:** R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** card này là kế hoạch, chưa có kết quả triển khai hay acceptance.

## Objective

Fingerprint TTS, invalidation và bảo vệ media tốt cũ. Hoàn thành contract tương ứng trong SPEC, giữ khả năng dùng project classic và dữ liệu đã xuất.

## Paths

- backend/ai/tts/tts_service.py
- backend/api/tts.py
- backend/api/audio.py
- backend/content/project_service.py
- backend/media/audio_service.py
- backend/media/video_service.py
- backend/content/shorts_service.py
- tests/test_tts_word_boundary.py
- tests/test_audio_api.py
- tests/test_audio_service.py
- tests/test_voice_cache_invalidation.py
- backend/core/voice.py
- backend/api/video.py
- backend/api/shorts.py
- backend/media/video_renderer_remotion.py
- backend/library/project_visuals_service.py
- tests/test_tts_service.py
- tests/test_video_api.py
- .viepilot/phases/48-character-voices/PHASE-STATE.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- .viepilot/phases/48-character-voices/tasks/task-48.3.md

## File-Level Plan / allowed_files

1. Thêm sidecar .tts.json theo SPEC, giữ .words.json; cache check so sánh engine/voice/text/effective params/schema. Centralize resolve voice cho preview/synth/cache.
2. Dùng mark_speaker_voice_changed và freshness primitives hiện có; audit cả cast/apply/profile-to-project paths để không bỏ sót invalidation.
3. Chỉ line của speaker đổi giọng cần synth lại; mixed audio/timings/video/Shorts dependent stale. Giữ last-good file/metadata đến khi replacement đã validate.
4. Legacy cache thiếu fingerprint không tự bị xóa lúc mở app. Lần chủ động tạo lại sau voice change không được coi word timings cũ là bằng chứng đúng giọng.
5. Explicit voice provider fail không fallback sang voice khác. Active audio/video jobs chụp source fingerprint và không publish stale output sau concurrent edit.
6. Nếu freshness hiện có chưa biểu diễn đủ state, ghi rõ contract bổ sung trong card trước code; không nới scope sang viết lại toàn bộ job system.

**File mới dự kiến:** `tests/test_voice_cache_invalidation.py`.

### Execution refinement (2026-10-16, before code)

- Existing mix/render functions publish fixed filenames before their routes save DB metadata. A fingerprint check after that alone cannot preserve the previous file. Production routes will supply an attempt token; TTS/audio/video/Shorts write into unique attempt paths and only current inputs can update the DB's published references. Legacy direct service callers retain their default path conventions where required for compatibility.
- Audio soundtrack lookup must resolve the voice stem beside the selected audio job's WAV, with the existing canonical stem as legacy fallback. Remotion public audio/soundtrack staging uses the attempt key so simultaneous renders cannot exchange voice files.
- `core/voice.py` owns pure input fingerprint; routes snapshot speaker/script/audio revision before network/mix/render and compare under the write lock before publication. No whole-job-system rewrite or new DB table.
- Actual voice changes clear cache references only for affected speakers, retain old files and mark mixed audio/video stale through existing error-status fields with an explicit regeneration message. Shorts return to proposed with old media retained for reference. New requests cannot render an old stale mix.
- `project_visuals_service.py` calls the same targeted invalidation after a changed cast voice; unchanged cast voices remain pinned. Updating a profile alone does not invalidate project media.
- Commands: targeted TTS/audio/video/Shorts and new voice invalidation regressions, including edit-during-work; full pytest/Ruff before checkpoint. Expected: old files survive both provider failure and stale completion, sidecars/timings match the newly published line.

Chỉ sửa các Paths trên và cập nhật tiến độ card/phase. Nếu phát hiện cần file khác, ghi lý do và mở rộng bounded scope trước code. Các file đã tạo bởi task trước trong Paths được tiếp tục sử dụng; không tự viết lại hệ thống lân cận.

## Risks / guardrails

Cache filename cũ ổn định nên chỉ đổi DB ID chưa đủ. Giữ atomic publish và stale check xuyên TTS → mix → video → Shorts.

Dùng constants/path helpers hiện có, service layer async, validation API + semantic. Không giữ shared DB lock trong network/render/copy nặng. Không sửa dữ liệu production khi có thể dùng sandbox. Không thay đổi gate cũ hoặc phát hành chỉ vì task kỹ thuật chạy qua.

## Verification / expected results

1. Đổi một speaker trong project hai người: đúng tập line stale; line người kia và file đã xuất giữ hash.
2. Regenerate tạo đúng voice ID, word timings đầy đủ; mixed timeline/karaoke/Shorts tính lại; không đọc audio cũ chỉ vì .words.json có sẵn.
3. Text/voice/speed/pitch/volume đổi đều làm cache miss; lỗi synth hoặc đổi giọng trong khi job chạy không ghi đè last-good.
4. Legacy cache + không chỉnh voice: load project không gây synth/DB/file writes ngoài luồng hiện có.
5. `git diff --check`; review diff đúng Paths. Chạy quality gates theo SYSTEM-RULES và PLAN trước commit; explicit staging, tuân thủ PM/owner authorization.

## Acceptance / handoff

- [ ] Các bước trên có evidence thực, test commands và kết quả ghi vào card.
- [ ] Error/race/compatibility cases liên quan được kiểm tra, không chỉ happy path.
- [ ] Không ghi “done/pass” cho test hoặc owner gate chưa chạy.
- [ ] PM/owner nhận kết quả theo AR-06; ghi technical verification và owner acceptance riêng.

## Progress

- 2026-10-16: planned; shipping code chưa sửa, tests triển khai chưa chạy.
