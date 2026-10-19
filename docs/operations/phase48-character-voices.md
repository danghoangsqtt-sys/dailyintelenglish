# Phase48 — Giọng riêng cho nhân vật

Ngày:16/10/2026 · Mã nguồn trên `owner-runs/20261001-r9` · Target1.5.0.

> Phase48 đã hoàn tất kiểm chứng kỹ thuật; owner đã chấp nhận bốn mẫu nghe Brian/Christopher/Roger/Ryan. Bản phát hành vẫn1.4.0-rc.1; EXE chưa được cập nhật. Không đóng các owner gates cũ.

## Yêu cầu và phản hồi chủ dự án

Chủ dự án muốn nhiều nhân vật cùng giới tính dùng các giọng khác nhau. Hai mẫu Guy/Andrew ban đầu chưa đáp ứng đủ sự khác biệt và tự nhiên. Chủ dự án sau đó chấp nhận cả bốn Brian, Christopher, Roger, Ryan và yêu cầu khoảng20 giọng để lựa chọn.

Catalog thật kiểm tra ngày16/10/2026 có **47 giọng tiếng Anh**. Bộ chọn hiển thị toàn bộ catalog, không khóa ở20 và không chỉ có bốn mẫu. Việc chấp nhận bốn mẫu nghe không được suy thành nhận xét chất lượng của mọi giọng trong catalog.

## Thay đổi chính

- Catalog có metadata provider thật, search/locale/gender,24h last-good cache và trạng thái stale. Timeout/failure có phản hồi rõ.
- Mẫu nghe thử tách khỏi project: engine/ID/text/tham số,500 ký tự tối đa,24h TTL,256MiB quota; audio được đọc trước khi trả nên không giữ file mở trong lúc cleanup.
- Giọng profile và project round-trip đầy đủ. Profile edit không tự sửa project đã cast; Apply profile voice là thao tác rõ ràng, giữ speed/pitch/volume của project. Revisions chống ghi đè lựa chọn cũ.
- `.tts.json` so sánh effective engine/voice/locale/text/speed/pitch/volume/schema; `.words.json` giữ karaoke. Legacy cache không tự bị xóa khi mở app; đổi giọng chỉ clear cache references của speaker liên quan.
- TTS/mix/video/Shorts ghi output theo attempt riêng và kiểm tra source trong transaction trước khi publish. Old files còn nguyên khi provider lỗi hoặc source thay đổi giữa chừng. Render staging audio/soundtrack cũng riêng theo attempt.
- Speaker rename clear cache của các câu thực sự đổi nội dung. Video ngang tạo lại không quảng bá bản dọc đã stale như output hiện hành; cần tạo bản dọc mới.
- Picker dùng chung trong Characters và Audio Studio: audition/save/reload/refresh, dirty guard, cancellation tokens, explicit apply và thông báo trùng voice có thể bỏ qua.

## Kiểm tra tự động

| Chặng | Evidence |
|---|---|
| Baseline | Full pytest1636 passed; Ruff sạch |
| 48.1 catalog/audition |39 focused; full1668 passed; provider English catalog47 |
| 48.2 persistence |45 focused gồm real Step1 browser; full1675 passed |
| 48.3 cache/freshness |99 +73 isolated regressions;34 focused sau review fix; final full1694 passed |
| Renderer |104 tests /14files và TypeScript pass |
| 48.4 picker |30 isolated voice/browser cases,45 combined final browser regressions; real47-entry UI smoke; full1704 passed in916.89s |
| 48.5 final QA/docs |Full1704 passed in901.80s;172-route OpenAPI docs; user/install guides and actual media/ZIP handoff verified |

Một full run của48.2 dừng vì test Step5 đọc `aria-pressed` trước khi async init hoàn tất; module chạy riêng5/5, thay bằng Playwright retrying expectation và full1675 pass. Không sửa hành vi Step5 vì lỗi test này.

Một full run đầu48.3 đạt1693; review tiếp phát hiện stale vertical path có thể được chuyển sang job ngang mới. Thêm regression mix→horizontal sau voice change, sửa và chạy lại full1694 pass. Không bỏ qua trường hợp này vì suite trước đã xanh.

Toàn bộ các full run ghi nhận một cảnh báo Starlette/httpx đã có từ trước. Các test catalog/network lỗi dùng fake provider rõ ràng; không dùng fake để xác nhận giọng thật khả dụng.

Full run đầu48.4 dừng tại1553 pass vì workspace Step5 hiện trước khi tải xong visual options và khóa theo renderer. Một bài kiểm tra cố ý trì hoãn tải đã tái hiện lỗi trên mã cũ; chuyển thời điểm hiện workspace đến cuối init,45 browser regressions và full1704 pass. Thay đổi không sửa quá trình render.

## Chạy media thật

Sandbox: `data/tmp/evolve-20261016/voice-media-dbc2312672/`.

1. API catalog thật trả47 giọng; audition Brian/Roger không tạo cache production hoặc project rows.
2. Hai profile thử cùng male/en-US lưu Brian/Roger, cast bằng API, project vẫn giữ đúng hai concrete IDs.
3. Hai câu tổng hợp thật có word boundaries và fingerprint sidecars; cache reuse trả kết quả trong3–4ms mà không gọi lại synth.
4. Mixed speech **11.54s**, cả hai câu có word timings; render production API tạo **28.778667s** gồm brand intro/outro.
5. Horizontal **1280×720**, vertical **1080×1920**, H.264/AAC; decode toàn bộ thành công. Thời gian render lần lượt21.85s và24.228s cho fixture ngắn này.
6. So sánh các cửa sổ lời nói trong output với WAV nguồn, cho phép lệch codec nhỏ: normalized correlation **0.9853** và **0.9959**, giống nhau ở hai aspect. Xác nhận đúng nguồn lời đã được đưa vào render, không thay cho đánh giá chất giọng của người nghe.
7. Kiểm tra frame có speaker label/karaoke ở cả hai aspect. Mốc intro lấy từ SRT là8.31s.

**Giới hạn fixture:** hai profile dùng trạng thái legacy-ready tổng hợp cho bài kiểm tra giọng; render ở `podcast_black`. Không dùng kết quả này để nghiệm thu ảnh/cử chỉ presenter, front21 hay bố cục Solo. Đây không phải benchmark tốc độ cho một tập dài có nhiều hình/nhân vật.

## UI với dữ liệu/provider thật

Một server nguồn riêng dùng cùng sandbox, không thay ứng dụng đang chạy:

- Dropdown có47 lựa chọn thật; không mock catalog hay lưu profile.
- Lưu Christopher, tải lại vẫn Christopher; project giữ Brian/Roger và video complete không đổi.
- Khôi phục profile thử về Brian sau bài kiểm tra. Zero browser page errors.
- Ảnh `profile-real47.png`, `project-real47.png`; báo cáo `ui-verification.json` cùng sandbox.

## Handoff nội dung và gói YouTube

- Tiếp tục từ cùng project sandbox đã có giọng/mix/render thật: thumbnail được dựng bằng Pillow, chọn favorite qua API, lưu/composition metadata và tải ZIP bằng API production. ZIP **3.559.565 bytes**, CRC đạt; có video, SRT, thumbnail, metadata, transcript và pinned comment. SHA256 video trong ZIP khớp đúng MP4 đã decode. Evidence: `export-verification.json`, `voice-gate-youtube.zip` cùng sandbox.
- Thumbnail suggestions và YouTube metadata ở bài này là fixture biên tập có ghi nhãn; không gọi AI mới, không đăng YouTube. Lần đầu fixture có ba headline giống nhau bị semantic validator từ chối; đổi thành ba ý tưởng khác nhau rồi luồng đạt. Không sửa validator để chấp nhận fixture sai.
- Đọc lại ba script lưu sẵn tại `docs/samples/A1`, `B1`, `C1`: A1 dùng câu ngắn/present simple nhưng có “Totally”/“I know, right?” cần cân nhắc cho người mới; B1 có conditional và phrasal verbs phù hợp hơn; C1 có câu dài/cụm từ đa dạng nhưng nhận định về blue light/circadian rhythm đang quá tuyệt đối. Cả ba ghi mục tiêu2phút, chưa dùng mục tiêu đó thay cho thời lượng đo thực tế.
- Đây là review nội dung của implementer trên mẫu cũ, không phải chứng nhận CEFR hoặc owner acceptance mới. Phase48 không đổi prompt hay script generator; các nhận xét nội dung và owner gates trước đó vẫn giữ riêng.

## Artifact và giới hạn triển khai

- Báo cáo chi tiết: `report.json`, `verification.json`, `ui-verification.json` trong sandbox trên.
- Log: `data/tmp/evolve-20261016/task48.*-pytest*.log`, `voice-media-gate.log`.
- Dữ liệu DB/media thật của owner không sửa; không thay EXE, shortcut hay release. Chỉ có renderer public staging/cache phục vụ thử nghiệm được tạo theo cơ chế hiện có.
- Output/caches theo attempt được giữ để bảo vệ bản trước; chưa có tự dọn lịch sử media production. Catalog/audition có TTL/quota riêng. Không xóa `.remotion/` hoặc dữ liệu owner để làm sạch evidence.
- Edge TTS cần mạng; không thêm engine trả phí/cloning. Voice không khả dụng báo lỗi, không âm thầm đổi sang voice khác.
- Phase47 visual review và B-25/B-26/B-27/B-28 giữ pending. Gate V49 cần front pack thật và demo Solo riêng.

Hướng dẫn: [Chọn giọng cho nhân vật](../user/character-voices.md). API được sinh từ OpenAPI thật ở [API reference](../api.md).
