# Task 48.3 — Fingerprint TTS, invalidation và bảo vệ media tốt cũ

- **Status:** implemented_verified · 2026-10-16; owner phase gate remains separate.
- **Dependencies:** 48.2
- **Requirements:** R12, R13.
- **Contract:** [SPEC tổng](../../../SPEC.md), [PLAN tổng](../../../PLAN.md), [phase SPEC](../SPEC.md), [phase PLAN](../PLAN.md).
- **Scope:** cache/freshness implemented and technically verified, including stale aspect regeneration.

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
- backend/schemas/tts.py
- backend/api/projects.py
- tests/test_phase40_character_names.py
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
- `schemas/tts.py` adds an explicit reuse_cached option for Generate All; a single-line preview still regenerates by default. `api/projects.py` passes the affected speaker ID into invalidation. Text replacement during speaker rename clears affected cache references so the new reuse path cannot speak an old name.
- Update the source-introspection assertion in `test_phase40_character_names.py` to test concrete voice selection behavior after centralizing the resolver. Isolate the raw-DB TTS test module's DATA_DIR before adding fingerprint sidecars; adapt old fixed-path assertions to the actual published versioned cache path.
- Shorts cover rendering also uses the attempt folder; snapshot composition inputs under a short read lock and draw outside it. Check clip range/hook/status/revision alongside voice/audio before publishing, preserving old cover/clip files on conflict. Keep audio/generate's existing requirement that uncached lines must first be generated; only nonempty invalid cache entries are repaired by the mix route.
- Review after the initial1693-pass full run found a remaining stale-aspect publication case: a fresh horizontal render carried forward an old vertical path even when the previous job was marked stale by a voice change. On successful horizontal replacement, preserve the vertical reference only from a previously complete job; otherwise require a new vertical render. Keep the old file intact on disk. Add a regenerate-after-voice-change regression and rerun the full gate before checkpoint.

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

- Implemented voice/text/parameter fingerprint sidecars, targeted line-cache invalidation and immutable attempt output paths, with source checks under publication transactions for TTS/mix/horizontal/vertical/Shorts. Previous files and published paths are retained on stale work/provider failure. Soundtrack follows the selected job's voice stem; public render audio is staged per attempt.
- Isolated candidate verification:99 focused TTS/cache/audio/video/name tests and73 additional project/music/Shorts/render/cast regressions passed. An initial new test accidentally used its own fake synthesizer; restored the real function in that invalid-ID check and reran successfully. Candidate files were then applied verbatim under the bounded contract. Ruff/diff clean. Initial workspace full suite1693 passed; review then caught stale vertical reference promotion after horizontal regeneration. Corrected it and added a real mix→render regression:34 focused tests passed, final full **1694 passed** in **920.34s**, one existing Starlette warning. Renderer104/14files and TypeScript pass; Ruff/diff clean. Evidence: `data/tmp/evolve-20261016/task48.3-pytest-r2.log`. Old files remain on disk; successful replacement stops advertising an old stale vertical as current. No real DB/EXE/release changes.
