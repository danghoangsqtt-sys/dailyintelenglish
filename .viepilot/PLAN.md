# PLAN — Phase 48/49, mục tiêu 1.5.0

- Ngày lập: 2026-10-16 · Trạng thái: **Phase48 implemented_verified; Phase49 executing49.3**.
- Phạm vi: Add Feature từ [SPEC](SPEC.md) và [brainstorm](../docs/brainstorm/session-2026-10-16.md).
- 15 task: **5 task Phase48 +10 task Phase49**;48.1–48.5 and49.1–49.2 implemented_verified,49.3 in_progress,7 planned. V48 technical verified + owner listening accepted;47 actual voice choices observed. Demo Hoang — Why do we build habits?; V49 still pending.
- Bản đang phát hành giữ **1.4.0-rc.1**; target 1.5.0. Không sửa version runtime, tạo EXE hay release trong phiên lập kế hoạch.
- Phase 47 chờ owner visual review; B-25/B-26/B-27/B-28 vẫn pending, không dùng planning mới để tự đóng gate.

## 1. Trình tự thực hiện

| Chặng | Task | Kết quả cần thấy | Điều kiện qua |
|---|---|---|---|
| Catalog / audition | 48.1 | Tìm, nghe nhiều giọng tiếng Anh | API/provider/cache riêng được kiểm tra |
| Voice persistence | 48.2 | Profile và project giữ voice ID đúng | Round-trip, pinned defaults, conflict guard |
| Cache/freshness | 48.3 | Đổi giọng không phát lại audio cũ | Fingerprint và invalidation đúng phạm vi |
| Voice UI | 48.4 | Chọn/nghe/lưu ở profile và Step 4 | Browser save/reload + race/error flows |
| Gate V48 | 48.5 | Hai người cùng giới tính dùng hai giọng thật | Technical evidence + owner nghe |
| Mode/data | 49.1 | Classic/Solo riêng và migration an toàn | Legacy defaults, rollback trên DB bản sao |
| Front assets | 49.2 → 49.3 | Prompt/import/review đủ 21 ảnh | Native 29 không ảnh hưởng |
| Script | 49.4 | Why/How/List tiếng Anh một người | CEFR/budget và classic regression |
| Plan + layout | 49.5 → 49.6 | Đoạn có timing, hình, bố cục hợp lệ | Lock/revision, collision, stale |
| Preview editor | 49.7 | Duyệt/chỉnh nhìn được cả hai aspect | Player dùng cùng scene như render |
| Production render | 49.8 | Cử chỉ/motion và media đúng approved plan | Determinism, asset pin, atomic publish |
| Integrations | 49.9 | Thumbnail/Shorts/export/series/copy | Mode/voices/front pack không rơi mất |
| Gate V49 | 49.10 | Demo thật + EXE candidate | Full regression, owner duyệt, release riêng |

Liên kết task và phạm vi file nằm trong [Phase 48 PLAN](phases/48-character-voices/PLAN.md) và [Phase 49 PLAN](phases/49-solo-explainer/PLAN.md). Làm tuần tự mặc định, không tự giao sub-agent.

## 2. Dependency graph

~~~mermaid
flowchart TD
  V1["48.1 Catalog + audition"] --> V2["48.2 Persistence"]
  V2 --> V3["48.3 Cache + freshness"]
  V1 --> V4["48.4 Picker UI"]
  V3 --> V4
  V4 --> V5["48.5 Gate V48"]
  V5 --> S1["49.1 Mode + schema"]
  S1 --> S2["49.2 Front registry + prompts"]
  S2 --> S3["49.3 Import + review UI"]
  S1 --> S4["49.4 Solo script"]
  S4 --> S5["49.5 Explainer plan"]
  S2 --> S5
  S5 --> S6["49.6 Layout solver"]
  S3 --> S7["49.7 Player editor"]
  S6 --> S7
  S7 --> S8["49.8 Production render"]
  S8 --> S9["49.9 Integrations"]
  S9 --> S10["49.10 Gate V49"]
~~~

Owner nghe V48 trước khi chốt phase; nếu chưa có phản hồi, có thể chuẩn bị draft tài liệu/fixture Phase 49, không tự ghi V48 pass. Một front pack thật cần sẵn trước demo V49; các task schema/layout có thể kiểm tra bằng fixture.

## 3. Kiến trúc thực hiện

### 3.1 Backend

- `voice_catalog_service.py`: provider metadata, filters/cache/timeout; không giữ DB lock khi gọi mạng.
- `voice_preview_service.py`: preview cache riêng, media URL an toàn, TTL/size cleanup.
- Các service profile/project/TTS/audio hiện có: round-trip voice ID, computed voice revision, fingerprint cache và stale propagation; không replace speaker IDs trong project đã có script.
- `character_asset_service.py`, `sprite_service.py`, `sprite_upload.py`: registry theo view, front21/native29 độc lập, version manifest, front alignment và review.
- `explainer_service.py`: validation/propose/revision/locks/approval, derive timing từ token anchors.
- `explainer_layout_service.py`: thuật toán bố cục thuần dữ liệu, safe-zone/alpha bounds/important rectangles.
- `explainer.py` schema/API riêng; durable AI operation đăng ký vào worker hiện có; không giữ transaction khi gọi LLM.
- Video bridge chỉ stage tài nguyên và truyền approved snapshot; fingerprint check trước công bố output.

### 3.2 Frontend và Remotion

- Giữ vanilla UI hiện có: Step 1 content type, characters front/voice, Step 4 voice picker, Step 5 explainer plan editor.
- Thêm widget React biệt lập qua `@remotion/player`; pin cùng bản Remotion thực tế của lockfile, đồng bộ họ package khi cần. Không đổi frontend thành SPA.
- Build `renderer/preview/` bằng script bundler rõ ràng vào `frontend/static/solo-preview/`. Khai báo direct bundler dependency nếu dùng esbuild, không dựa vào transitive dependency. Không commit node_modules hoặc media.
- Shared `SoloScene.tsx`, `Presenter.tsx`, `ExplainerVisual.tsx` và caption band cho preview/render; pure frame/geometry helpers có unit tests.
- Preview dùng API asset URLs; render dùng staged URLs. Component nhận resolved media URLs thay vì gọi `staticFile` cho mọi ngữ cảnh.
- Trích CaptionBand từ Episode chỉ khi cần dùng chung, giữ props/default classic và kiểm tra caption Phase 47.
- Player bundle được build trước chạy source mới và trước PyInstaller; EXE phân phối không cần một Vite/dev server.

## 4. Migration, compatibility và rollback

1. Task 49.1 kiểm tra migration runner hiện tại với lỗi giữa file; không cho runner đánh dấu một file đã xong khi chỉ một ALTER thành công.
2. Lập migration kế tiếp sau 026, đề xuất 027. Nếu cần tách ALTER, dùng các số tiếp theo và cập nhật tài liệu/task ngay trước code.
3. Thử trên DB mới và bản sao DB hiện tại: schema + FK + row counts + mở lại app hai lần; kiểm tra fault injection rollback/resume.
4. Project cũ default classic; không tự biến tất cả project một speaker thành Solo. Không đụng native pack/readiness.
5. DB backup trước áp dụng thật, không chạy migration trên app đang có job. Không đổi dữ liệu dự án/ảnh/video đã xuất trong task nghiên cứu.
6. Rollback binary/source chỉ dùng với schema backward-compatible đã kiểm chứng; nếu không, phục hồi DB backup **cùng** phiên bản source và media phù hợp. Không down-migrate phá dữ liệu mới.
7. Mỗi render dùng revision/snapshot độc lập. Fail/stale giữ file tốt cũ; không ghi đè MP4/SRT/thumb khi chưa kiểm tra.
8. Snapshot cast/front asset revisions phải còn resolve được khi owner import phiên bản ảnh mới.

## 5. Rủi ro và cách giải quyết cụ thể

| Rủi ro | Cách xử lý trong task | Không coi là pass khi |
|---|---|---|
| Voice catalog đổi/Edge lỗi | stale cache + retry + visible failure, 48.1/48.3 | âm thanh giọng khác được fallback lặng |
| Cache chỉ theo line | thêm fingerprint + targeted stale, 48.3 | word sidecar tồn tại nhưng giọng cũ |
| Lưu nhiều request chồng nhau | expected revision + serialized/trailing saves, 48.2/48.4/49.5/49.7 | request cũ ghi đè sửa mới |
| Front ảnh không đồng nhất | base-first, review21, alignment front, 49.2/49.3 | fixture bị coi là ảnh thật đạt chất lượng |
| Hình bị presenter che | important rectangles + contain/reflow + path check, 49.6 | chỉ xét vị trí tâm hoặc frame đầu |
| Preview khác render | component/timing origin/media resolver dùng chung, 49.7/49.8 | chỉ screenshot một editor mock |
| Hình/diagram quá dài | limits + wrap/overflow check + owner edit, 49.5–49.7 | ép chữ nhỏ để che lỗi |
| Render chậm hơn | pure precompute/memo + baseline cùng máy, 49.8/49.10 | ghi phần trăm cải thiện chưa đo |
| EXE thiếu preview/dependency | build step + frozen smoke trên thư mục trial, 49.10 | chạy được chỉ nhờ dev server |
| Facts không chính xác | ghi chú nguồn khi có, owner review, 49.4/49.5 | bịa URL hoặc tuyên bố fact-check tự động |

## 6. Validation theo tầng

- Trong từng task: focused pytest hoặc Vitest/TypeScript thực sự kiểm tra contract, một số regression fail trên hành vi cũ khi phù hợp; không test chỉ mirror implementation.
- Phase 48: catalog/provider failure fixtures, isolated preview, profile/project/cast/copy, chỉ speaker liên quan stale, true audio + word timings. Owner nghe hai voice khác ID.
- Phase 49: migration old/new/failure,21slot/native29, schema/anchors/revision/locks, geometry & whole transition path, deterministic seek, safe-area both aspects, Player/final component parity.
- Browser: chọn giọng, upload/review pack, tạo Solo, đổi shape minh họa, kéo/chỉnh vùng bảo vệ, save/reload, request race, stale approval và dirty navigation.
- Integration: một episode và Short, thumbnail một người, series/Episode folders, titles, export copy; classic fixture không đổi behavior.
- Gate cuối: full pytest, Ruff, renderer Vitest + `npm.cmd run typecheck`, JS syntax, browser suite; chạy theo quy tắc dự án trước commit/release. Phân biệt flake hạ tầng với lỗi thật, không bỏ qua test fail chưa giải thích.
- Render/probe: đoạn khó trước, sau đó demo thật 16:9/9:16 và Short. Decode đầy đủ, xem frames/chuyển động, drift/duration theo SPEC, audio IDs/timings; artifact/log/hashes lưu vùng evidence.
- Packaging: source install build preview + EXE trial, mở từ icon logo, player/media không lỗi, voice cần mạng báo đúng. Không ghi đè bản owner đang dùng nếu chưa có chỉ định triển khai.
- Evidence dự kiến `docs/operations/phase48-character-voices.md`, `docs/operations/phase49-solo-explainer.md`; media/log tạm dưới `data/tmp/phase48-voices/`, `data/tmp/phase49-solo/`. Các file evidence này chưa tồn tại và chưa có kết quả pass.

## 7. Quản trị thực thi và hoàn thành

- Task cards có Paths repo-relative, file-level plan, dependency, risks và verification. Chỉ code trong bounded scope đã nhận; phát hiện cần thêm file thì cập nhật card trước.
- Tuân thủ AR-06: plan → triển khai được giao → kiểm tra → PM/owner acceptance. Yêu cầu hiện tại chỉ lập kế hoạch; không phải lệnh chạy vp-auto.
- Không đổi status task/phase thành done chỉ vì có plan. Gate kỹ thuật và owner acceptance ghi riêng.
- Không commit/push/build/release trong phiên lập kế hoạch này. Khi thực hiện dùng explicit staging, checkpoint từng task theo workflow và authorization đang có.
- Ước lượng effort tương đối: Phase 48 L, Phase 49 XL; hiệu lực nghiệm thu phụ thuộc thời gian owner chuẩn bị ảnh/duyệt giọng. Không đặt deadline giả.
- Bước tiếp theo: `vp-auto --from 48`, đọc Task 48.1 và phase state trước code.

## 8. Kiểm tra bản kế hoạch

- Đủ 13 yêu cầu R01–R13, 15 task cards, các dependency tạo DAG không có vòng lặp.
- Mọi Paths trong card là repo-relative; file chưa có được ghi rõ là file mới hoặc output build. Đường dẫn code hiện có được đối chiếu inventory.
- Liên kết nội bộ của tài liệu mới, JSON handoff, số task và manifest 21 slot được kiểm tra tự động; diff không có lỗi whitespace.
- Evidence validation: `data/tmp/evolve-20261016/validation.json` (local, ignored). Đây là kiểm tra tài liệu, không phải kết quả tests của tính năng.
