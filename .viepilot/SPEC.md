# SPEC — Giọng nói riêng và Solo Explainer

- Ngày: 2026-10-16 · Mode: Add Feature · Độ lớn: XL.
- Trạng thái: **Phase48 implemented_verified; Phase49 executing49.3**. Owner listening examples accepted, real47-choice UI/audio/video/export and final full1704 pass. Solo demo:Hoang — Why do we build habits?; front21 visual gate remains later.
- Nguồn yêu cầu: [brainstorm 2026-10-16](../docs/brainstorm/session-2026-10-16.md).
- Kế hoạch thực thi: [PLAN](PLAN.md); [Phase 48](phases/48-character-voices/SPEC.md); [Phase 49](phases/49-solo-explainer/SPEC.md).
- Bản đang phát hành: **1.4.0-rc.1**, stable gần nhất 1.3.0. Mục tiêu tính năng **1.5.0**; 1.5.0-rc.1 chỉ được tạo sau kiểm thử và quyết định phát hành.
- Phase 47 đã có source fix, chờ owner xem phụ đề; B-25/B-26/B-27/B-28 vẫn pending. Kế hoạch này không đóng các gate đó.

## 1. Mục tiêu và phạm vi

Thêm khả năng chọn giọng thật riêng cho mỗi nhân vật, dùng được cho video hiện tại và video mới. Thêm dạng **Solo Explainer**: một người giải thích đời sống/kiến thức bằng tiếng Anh, nhìn chính diện người xem, luôn hiện cùng minh họa ảnh/sơ đồ/thẻ chữ. Hệ thống đề xuất bố cục theo nội dung; owner xem, sửa và duyệt trước khi render.

Đây là phần mở rộng quy trình 7 bước hiện có, dùng lại profile nhân vật, CEFR, thời lượng, audio/word timings, nhạc, phụ đề Phase 47, brand, xuất YouTube 16:9, 9:16 và Shorts. Không cần chuyển toàn bộ frontend sang SPA.

### Ma trận yêu cầu đã xác nhận

| ID | Yêu cầu của owner | Task chính | Nghiệm thu |
|---|---|---|---|
| R01 | Một người giải thích đời sống/kiến thức bằng tiếng Anh | 49.1, 49.4 | Why/How/List, đúng một speaker, đúng CEFR |
| R02 | Nhân vật dùng profile hiện có, nhìn chính diện người xem | 49.2, 49.3, 49.8 | Giữ nhận diện/trang phục, không giả bằng lật ảnh nghiêng |
| R03 | Người dẫn luôn hiện, nhỏ, trái/phải/giữa | 49.6, 49.7, 49.8 | Có presenter ở mọi frame phần trình bày |
| R04 | Minh họa phía sau, không bị che nội dung quan trọng | 49.5–49.8 | Kiểm tra cả hình, chữ và tay nhân vật |
| R05 | Kích thước presenter thay đổi linh hoạt | 49.6–49.8 | Scale theo ý nói, chuyển động có easing |
| R06 | Tự đề xuất vị trí/size, owner duyệt và chỉnh | 49.5–49.8 | Preview, chỉnh, tải lại, render đúng bản duyệt |
| R07 | Kết hợp ảnh, sơ đồ và thẻ chữ | 49.5, 49.7, 49.8 | Một tập mẫu thể hiện đủ ba loại |
| R08 | App tạo prompt, owner tạo ảnh AI bên ngoài rồi import | 49.2, 49.3 | Prompt/reference → import → review → usable |
| R09 | 10 tư thế × hai miệng + một blink = 21 ảnh/profile | 49.2, 49.3 | 21 slot duy nhất, đúng version, đã duyệt |
| R10 | Chọn giọng nói riêng cho nhân vật | 48.1–48.5 | Hai profile cùng giới tính/locale dùng hai voice ID |
| R11 | Dùng được cho video YouTube và video dọc | 49.6–49.10 | Hai bố cục riêng, safe area và caption rõ |
| R12 | Tận dụng assets và pipeline hiện có | 48.2, 49.1–49.10 | Project classic/native cũ vẫn chạy |
| R13 | Đã chọn giọng thì audio phải dùng đúng giọng | 48.2–48.5 | Cache, word timings và freshness nhất quán |
| R14 | Giọng khác biệt rõ hơn và tự nhiên, có ngữ điệu hơn (feedback2026-10-16) | 48.1, 48.4, 48.5 | So sánh thêm giọng thật/cùng đoạn; owner nghe, khác ID chưa đủ |
| R15 | Khoảng20 giọng để lựa chọn cho nhiều nhân vật | 48.1, 48.4, 48.5 | Hiện catalog English thật, hiện47; tìm/lọc/nghe/lưu toàn bộ, không chỉ bốn mẫu |

**V48 listening update:** owner xác nhận cả bốn Brian/Christopher/Roger/Ryan tốt, muốn khoảng20 lựa chọn. Phần nghe mẫu được chấp nhận; phase còn chờ persistence/cache/UI/E2E. Catalog hiện trả47 giọng, không đặt trần20 hay bịa giọng nếu provider thay đổi.

## 2. Hiện trạng đã đối chiếu code

- Edge TTS là engine duy nhất. `EDGE_TTS_VOICE_MAP` gán một giọng mặc định theo accent + gender; các profile cùng cặp đó thường trùng giọng. Không kết luận mọi accent có chung một giọng nam/nữ.
- Profile đã có `default_voice_id`; `apply_character_voice` có thể chép vào speaker. UI chưa có catalog/nghe thử; `SpeakerConfig`, `SpeakerUpdate` và `_replace_speakers` chưa round-trip voice ID đầy đủ.
- TTS cache dùng project/line, có `.words.json`, chưa có fingerprint giọng. Endpoint preview script hiện tại viết cache của line thật, không phù hợp làm nút nghe thử catalog.
- Bộ native hiện có 29 slot, prompt hướng nghiêng và nhìn bạn nói; registry/readiness/path nhiều chỗ mặc định `facing='native'`. DB asset đã có facing + identity_version; không cần tạo lại bảng nhân vật.
- Script có hỗ trợ một người nói; storyboard hiện tại thiên về scene/insert hội thoại. Solo cần contract nội dung và bố cục riêng.
- Remotion `Episode.tsx` đang dùng vị trí/hướng nhân vật hội thoại. Front presenter cần nhánh scene riêng, tái sử dụng caption/audio/brand.
- Migration mới nhất lúc lập kế hoạch là 026. Chưa chạy migration mới trên dữ liệu thật.

## 3. Quyết định thiết kế dùng cho kế hoạch

Các mặc định dưới đây là lựa chọn kỹ thuật/UX để triển khai, không ghi thành câu trả lời owner đã xác nhận riêng:

| Quyết định | Mặc định thực hiện |
|---|---|
| Phân biệt dạng video | `presentation_mode`: `classic` / `solo_explainer`; project cũ luôn classic, kể cả một speaker |
| Dạng giải thích | `explainer_structure`: `why` / `how` / `list`; giữ CEFR/thời lượng/accent có sẵn |
| Đổi giọng profile | Mặc định cho lần cast tiếp theo; project đã cast giữ giọng đang lưu |
| Áp dụng vào project hiện tại | Thao tác rõ ràng “Áp dụng giọng hồ sơ” hoặc chọn giọng project |
| Speed/pitch/volume | Giữ giá trị project khi áp giọng profile để không phá tốc độ theo CEFR |
| Duyệt bố cục | Có thể duyệt cả bản kế hoạch sau khi mọi đoạn hợp lệ; không bắt click duyệt từng đoạn |
| Chỉnh thủ công | Khóa trường/đoạn đã chỉnh; regenerate chỉ phần chưa khóa |
| Minh họa | Ảnh upload/thư viện hoặc prompt AI ngoài; sơ đồ/thẻ chữ do renderer dựng từ schema |
| Bộ front | Duyệt neutral gốc trước; phái sinh ảnh cử chỉ/miệng từ ảnh gốc tương ứng |
| Demo đầu tiên | Owner chọn chủ đề và profile lúc nghiệm thu; chưa cần quyết định để bắt đầu xây chức năng |

Không thêm engine trả phí, clone giọng, LivePortrait/rig 3D, tự tạo ảnh presenter bằng local Qwen, hoặc hệ thống tự kiểm chứng toàn bộ kiến thức. Cử chỉ vẫn là sprite ảnh với chuyển tiếp và chuyển động thân nhẹ; không hứa animation xương hay lipsync theo phoneme.

## 4. Chọn giọng riêng — contract Phase 48

### 4.1 Catalog và nghe thử

- Lấy danh sách từ Edge TTS bằng API của phiên bản đang cài; chỉ hiện giọng tiếng Anh có metadata thật. Lọc locale/accent/gender, tìm tên/ID. Không hardcode số lượng hoặc gán nhãn cảm xúc không được provider hỗ trợ.
- Cache catalog 24 giờ, timeout mạng 15 giây bằng constants cấu hình; refresh lỗi giữ bản gần nhất kèm trạng thái stale. Chưa từng tải được thì hiện lỗi/retry, không giả danh sách khả dụng.
- Cùng câu mẫu tiếng Anh để so sánh; cho nhập trích đoạn tối đa 500 ký tự với speed/pitch/volume hiện tại.
- Preview lưu vùng riêng `data/tts_preview/`, khóa theo engine/voice/text hash/tham số; trả URL qua opaque ID, TTL mặc định 24 giờ và dung lượng tối đa mặc định 256MiB bằng constants cấu hình. Cleanup loại file hết hạn/cũ nhất, không xóa file đang phục vụ. Không ghi script line, audio_job, mixed track hoặc cache sản xuất.
- Nút nghe thử có loading, cancel/replace playback cũ, chống double-submit. Nếu request cũ trả sau lựa chọn mới, không phát hoặc hiển thị nhầm giọng.

### 4.2 Lưu, áp dụng và tính nhất quán

- Profile lưu concrete `default_voice_id`. Speaker project lưu concrete `voice_id`; create/get/update/copy đều round-trip.
- Thứ tự resolve: explicit speaker voice → profile voice lúc cast → accent/gender default khi chưa chọn. Sau cast, không tự đọc lại profile mỗi lần render.
- Không tự đổi explicit voice khi đổi accent/gender; UI mời chọn lại hoặc chủ động dùng mặc định. Legacy chưa có ID tiếp tục fallback như trước.
- Voice cụ thể lỗi/không khả dụng: báo rõ và cho chọn lại, không synth bằng giọng khác trong im lặng.
- Hiện tên + ID giọng thực tế trong profile, selector nhân vật và Step 4. Trùng giọng trong cùng video là cảnh báo có thể bỏ qua.
- Trước lưu xác minh ID/engine và payload; thao tác mạng ngoài write lock. Dùng computed `voice_revision` từ cấu hình hiện tại để phát hiện request cũ và trả 409 thay vì ghi đè.
- Cập nhật speaker tại chỗ theo ID; không gọi replace toàn bộ speaker khi script đã tồn tại.

### 4.3 Cache và thay giọng

Fingerprint sidecar `.tts.json`: schema_version, engine, resolved_voice_id, locale, effective speed/pitch/volume và hash text. Chỉ cache có fingerprint phù hợp mới được xem là phù hợp với một thay đổi giọng mới.

Khi owner đổi giọng project: chỉ line thuộc speaker đó cần synth lại; mixed audio, timings tổng, video và Shorts liên quan phải stale. Giữ file tốt gần nhất cho tới khi bản thay thế được kiểm tra và publish nguyên tử. Không xóa hàng loạt cache khi chỉ mở app/nâng cấp; cache legacy thiếu fingerprint được kiểm tra/nâng cấp lười tại lần tạo lại chủ động. Giữ `.words.json` và luồng karaoke, nhạc, export. Render đang chạy phải kiểm tra fingerprint đầu vào trước khi công bố kết quả.

## 5. Bộ presenter chính diện — contract Phase 49

### 5.1 Manifest 21 ảnh

Mỗi key dưới đây duy nhất trong `(character, identity_version, facing=front, slot)`.

| Tư thế | Miệng đóng | Miệng mở |
|---|---|---|
| Nghỉ, nhìn người xem | calm__closed | calm__open |
| Giải thích, mở bàn tay | gesture-talk | gesture-talk__open |
| Chỉ bên trái màn hình | gesture-point-left | gesture-point-left__open |
| Chỉ bên phải màn hình | gesture-point-right | gesture-point-right__open |
| Nhấn mạnh | gesture-emphasize | gesture-emphasize__open |
| Đếm 1 | gesture-count-1 | gesture-count-1__open |
| Đếm 2 | gesture-count-2 | gesture-count-2__open |
| Đếm 3 | gesture-count-3 | gesture-count-3__open |
| Suy nghĩ | gesture-think | gesture-think__open |
| Chào | gesture-wave | gesture-wave__open |

Ảnh thứ 21: `blink`, chính diện, miệng đóng, cùng neutral gốc. “Trái/phải” luôn theo màn hình người xem. Không lật ảnh theo giới tính để giả tư thế.

### 5.2 Vòng đời tài nguyên

1. Tab riêng “Đối thoại / Thuyết trình” trên hồ sơ; native 29 ảnh không đổi readiness.
2. App tạo prompt neutral front bằng nhận diện/trang phục hiện có. Reference download và chỉ dẫn đúng crop/toàn thân đứng/chân-tay không bị cắt, nền xanh key hoặc PNG trong suốt theo pipeline hiện tại.
3. Owner tạo ngoài, import và duyệt neutral. App dùng neutral front làm reference cho 9 tư thế đóng; từng ảnh đóng làm reference cho ảnh mở tương ứng; blink từ neutral.
4. Reuse kiểm tra MIME/kích thước/key nền/alignment/alpha hiện tại; so với front base, không so độ khớp pixel với ảnh nghiêng.
5. Đủ **21/21 ảnh hợp lệ, approved, cùng identity version** mới usable cho Solo. Không điền tư thế thiếu bằng native mà vẫn báo hoàn tất.
6. Thay neutral làm các ảnh front phụ thuộc cần review lại. Không ảnh hưởng bộ native hay tự đổi render cũ.
7. Manifest render pin asset IDs + identity_version + pack_revision; giữ version cần cho render/job đang chạy. Một profile có hai pack, không tạo nhân vật trùng.

## 6. Solo Explainer — kịch bản và kế hoạch hình

### 6.1 Cấu hình và nội dung

- Step 1 chọn dạng “Hội thoại/hiện tại” hoặc “Một người giải thích”. Solo buộc một speaker và một cast hợp lệ, front pack usable trước render; không bắt cần pack để viết kịch bản.
- Why: vấn đề → cơ chế/nguyên nhân → ví dụ → tóm tắt.
- How: mục tiêu → từng bước → ví dụ/cảnh báo theo nội dung → tóm tắt.
- List: mở chủ đề → các ý có thứ tự → kết luận.
- Lời nói tiếng Anh hướng người xem, không giả hai người trò chuyện. Dùng validator word budget/CEFR/repair hiện có với tiêu chí độc thoại; tránh làm sai các genre classic.
- Nội dung kiến thức do owner xem/duyệt. Schema có nguồn/ghi chú khi có, không bịa URL/trích dẫn. Dữ kiện chưa kiểm chứng được đánh dấu để duyệt.

### 6.2 Contract kế hoạch đoạn

Thêm `ExplainerPlan` riêng, không nới tùy tiện enum scene/insert của storyboard classic.

- `schema_version, project_id, revision, status(draft|approved|stale), source_fingerprint`.
- `presenter`: speaker/profile IDs, identity version, front pack revision.
- Mỗi segment: stable ID, intent, line IDs và token anchors, visual kind, content, asset ID/version, important rectangles, gesture cues, layouts theo aspect, locks.
- Anchor là `(line_id, token_index)` start inclusive/end exclusive; các đoạn liên tục bao phủ toàn bộ phần lời nói, không lặp hoặc mất từ. Timestamp suy ra từ audio/word timings thật, không dùng thời gian AI tự đoán.
- `photo`: image asset ref, contain/crop và vùng quan trọng. `diagram`: template steps/comparison/cause_effect với nodes/edges có giới hạn. `text_card`: tiêu đề và ý ngắn, độ dài/overflow kiểm tra trước duyệt.
- Text là plain text/schema; không nhận HTML, JS, SVG tùy ý từ AI.
- Source fingerprint gồm script, effective voice/audio/timings, cast/front pack, illustration versions, layout rules version.
- Thiếu audio vẫn đề xuất nội dung ở draft; chỉ approve/render khi đã resolve timing thật và asset/front pack đủ.

### 6.3 Bố cục, safe area và motion

- Layout riêng cho 16:9 và 9:16, tọa độ normalized, anchor left/right/center và scale đồng dạng. Dùng lại safe-zone policy từng aspect, không mặc định safe area = tâm hình học.
- Default chiều cao presenter 22% frame, khoảng điều chỉnh 12–38%, giới hạn thêm bởi chiều rộng, safe area và vùng minh họa. Đây là default cần hiệu chỉnh khi xem demo, không phải kích thước owner đã chốt.
- Dùng alpha bounds hợp nhất của mọi pose sử dụng, kể cả bàn tay; cộng breathing/motion margin, caption band, labels và brand. Quan trọng nhất là nội dung vẫn đọc được, không chỉ tâm nhân vật trong safe area.
- Sơ đồ/thẻ chữ biết trước content bounds. Ảnh có important rectangles owner sửa được. Khi ảnh chưa có annotation, contain ảnh vào panel nội dung riêng, presenter ở vùng riêng; không giả định AI biết góc trống.
- Không đủ chỗ: tự đề xuất reflow/contain/size khác; nếu vẫn xung đột thì báo đoạn lỗi, không approve/render. Owner có thể sửa nội dung, vùng bảo vệ hoặc bố cục và xem lại.
- Chuyển vị trí/size theo ý hoặc chuyển đoạn, giữ tối thiểu khoảng 2.5 giây khi phù hợp. Motion dựa frame và seed cố định; easing, idle/breathing nhẹ, blink và miệng theo audio.
- Gesture cue theo ý: giải thích/chỉ đúng bên/đếm/nhấn/suy nghĩ/chào; có neutral rests, tránh đổi ảnh mỗi từ.
- Kiểm tra cả đường chuyển động không quét qua vùng nội dung. Nếu không có đường an toàn, đổi bố cục bằng cut ở ranh giới đoạn, presenter vẫn hiện. Không fade presenter xuống opacity 0.
- Lời dẫn luôn có presenter; intro/outro thương hiệu dùng host hiện có, không tạo khoảng trống nhân vật do chuyển cảnh.

### 6.4 Review, preview và lưu sửa

Step 5 có timeline đoạn, ảnh/sơ đồ/thẻ chữ, preview có audio/phụ đề, chuyển aspect, chọn trái/phải/giữa, slider size, gesture, vùng quan trọng và thay illustration.

- Cùng component dựng scene/caption cho preview và render; Player chỉ là widget trong vanilla app.
- Lưu revision; request sửa/regenerate/approve mang expected_revision. Cũ trả 409 và cho reload/so sánh, không tự ghi đè.
- Owner chỉnh trường nào thì khóa trường đó mặc định; có thao tác mở khóa. Regenerate chỉ phần chưa khóa; thêm/xóa script làm đoạn khóa mất anchor phải cảnh báo để owner sửa, không âm thầm bỏ khóa.
- Duyệt cả plan sau validation hai aspect được chọn xuất; gắn approved revision. Thay script/voice/audio/pack/asset/layout liên quan làm approval stale.
- Render chụp approved revision + source fingerprint. Trong lúc render có sửa mới thì không publish kết quả cũ thành hiện hành; file tốt trước đó còn nguyên.

## 7. API, dữ liệu và tích hợp dự kiến

Tên endpoint dưới đây là contract mục tiêu; Task 48.1/49.1 kiểm tra xung đột OpenAPI trước khi code.

| Contract | Mục tiêu |
|---|---|
| GET /api/tts/voices | Catalog, filters, fetched_at, stale |
| POST /api/tts/voices/preview | Audition độc lập, metadata + URL |
| GET /api/tts/voices/preview/{id}.mp3 | Media preview có TTL/path containment |
| PATCH /api/visuals/profiles/{id} | Voice ID, expected_voice_revision |
| PATCH /api/projects/{id}/speakers/{sid} | Voice ID hoặc apply_profile_voice, expected_voice_revision |
| GET /api/visuals/profiles/{id}/slots?view=front | 21 slots, prompt/reference/readiness/version |
| Existing upload/review routes + view=front | Không trộn với native; mặc định native |
| GET /api/projects/{id}/explainer-plan | Plan/revision/status và issues |
| POST /api/projects/{id}/explainer-plan/propose | Durable AI job; chỉ ghi draft nếu source còn khớp |
| PATCH /api/projects/{id}/explainer-plan | Chỉnh/lock/asset/layout theo revision |
| POST /api/projects/{id}/explainer-plan/approve | Validation + approved snapshot |

- Phase 48 tận dụng cột voice đã có; computed revision, không cần migration chỉ để thêm picker.
- Phase 49 dự kiến migration **027_solo_explainer.sql**: projects.presentation_mode DEFAULT classic; projects.explainer_structure nullable; bảng project_explainer_plans cho current revision + version history/snapshot JSON, FK project, optimistic revision. Recheck số migration tại lúc thực hiện.
- Không trộn nhiều ALTER không idempotent trong một migration nếu runner chưa bảo đảm rollback toàn file. Task 49.1 phải kiểm tra và sửa **migration transaction tracking** trước, hoặc tách thành các migration kế tiếp; ưu tiên giữ nguyên DB nếu lỗi giữa chừng. Backup/restart thử trên bản sao trước dữ liệu thật.
- Dùng lại character_assets.facing/index hiện có, không sao chép ảnh thành character mới.
- Video props có presentationMode và approved explainer payload, native/classic defaults giữ nguyên. Media ID được resolve và stage bằng bridge hiện có; Player dùng URL local đã được cho phép, không nhận file path tùy ý.
- Step 6 thumbnail Solo lấy một front character + topic/illustration, không ép bố cục hai người. Shorts retime token anchors theo cửa sổ cắt, kiểm tra layout 9:16; không chép tọa độ 16:9.
- Copy project, channel episode creation, export package giữ mode, voice IDs và nội dung; project mới có approval draft và fingerprint riêng. Giữ quản lý series/Episode folder và title không tách “Ep. 2”.

## 8. Nghiệm thu và giới hạn

### Gate V48 — giọng riêng

- Hai nhân vật cùng gender/locale chọn voice khác nhau, audition và audio thật đúng IDs, save/reload/cast/copy không mất lựa chọn.
- Preview không thay project/cache sản xuất. Đổi profile không làm biến đổi project đã cast.
- Đổi voice một speaker chỉ làm line liên quan stale; audio tổng/video/Shorts stale; không dùng lại giọng cũ từ cache.
- Catalog lỗi/stale/voice mất/race đều xử lý rõ; giữ timings/karaoke/nhạc. Owner nghe và chấp nhận chất giọng, không coi số lượng voice là chất lượng biểu cảm.

### Gate V49 — video mẫu

- Một pack thật 21/21 do owner tạo và duyệt; fixture chỉ để kiểm thử, không thay nghiệm thu ảnh thật.
- Một tập kiến thức owner chọn, đủ ảnh + sơ đồ + thẻ chữ, presenter nhìn camera, gesture đa dạng phù hợp ý.
- Preview chỉnh/khóa/tải lại/regenerate và render đúng approved revision; đổi dữ liệu làm stale; xung đột revision không mất sửa.
- Xuất video đầy đủ cả 16:9 và 9:16, ít nhất một Short; phụ đề không vỡ cụm, không tràn, không che nội dung quan trọng ở đoạn đứng yên và chuyển động.
- Media decode đầy đủ, A/V drift tối đa 0.10 giây, duration sai lệch tối đa 0.10 giây so với timeline kỳ vọng (tính AAC padding khi probe container).
- Classic/native regression, package EXE mở từ icon logo, preview bundle đi kèm, không cần dev server.
- Benchmark cùng máy/cùng props baseline và mới; ghi thời gian thật, không cam kết tốc độ khi chưa đo.
- Owner quyết định visual/voice acceptance và phát hành. Các gate cũ vẫn được theo dõi riêng.

## 9. Tài liệu kỹ thuật tham chiếu

- [Edge TTS voice catalog source](https://github.com/rany2/edge-tts/blob/master/src/edge_tts/voices.py): metadata provider; kiểm tra phiên bản local lúc thực hiện.
- [Remotion Player](https://www.remotion.dev/docs/player): preview nhúng.
- [Remotion useCurrentFrame](https://www.remotion.dev/docs/use-current-frame): animation theo frame, seek có tính xác định.
