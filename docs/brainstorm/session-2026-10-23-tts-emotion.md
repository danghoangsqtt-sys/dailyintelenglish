# Brainstorm — AI đặt cảm xúc trong lời thoại và Edge TTS thể hiện giọng

## Session Info

- **Date:** 2026-10-23, Asia/Bangkok
- **Status:** Reopened after the 2.0.0 rebuild: production still uses Edge; expressive engine/default voice and commercial-use decisions pending
- **workflow_version:** 2.19.0
- **Skill:** vp-brainstorm 1.1.0
- **Language:** vi
- **Participants:** Owner, Codex
- **Relation:** Bổ sung cho [inline vocal cues](../operations/inline-vocal-cues.md); không thay thế brainstorm Phase 73 về Scene Library.

## 1. Mục tiêu và hiện trạng

Khi AI tạo lời thoại tiếng Anh, kịch bản xuất ra nên tự có một vài dấu cảm xúc đúng ngữ cảnh. Người dùng nghe thử và sửa/xóa/thêm dấu ngay trong Step 2. Mong muốn cụ thể: tiếng cười có kiểu “ha ha” hoặc “hi hi”; tiếng thở dài gợi “haizzz”; tiếng hắng giọng “ahem” rồi vài từ tiếp theo nói trầm hơn.

Hiện ứng dụng chỉ dùng Edge TTS. Ba thẻ `[cười]`, `[thở dài]`, `[hắng giọng]` đã được Step 2 cho chèn tay; `backend/ai/tts/vocal_cues.py` ánh xạ sang “Ha, ha, ha!”, “Ahh...”, “Ahem.” và `tts_service.py` ghép các đoạn MP3. AI chưa tự thêm thẻ. Tông giọng sau `[hắng giọng]` hiện chưa hạ. Phụ đề và transcript đã bỏ ba thẻ cũ.

Pipeline tạo kịch bản hiện hành (`backend/content/script_pipeline.py`) có kiểm tra CEFR, số từ, lặp câu và speaker trước khi công bố. Hàm `section_word_count` đếm các token cách nhau bằng khoảng trắng; nếu thêm thẻ trong lúc tạo section, thẻ sẽ bị tính thành từ thoại. Luồng legacy `script_service.generate_script` và tái tạo một câu cũng cần tương thích.

## 2. Quyết định với owner

| # | Chủ đề | Quyết định |
|---|---|---|
| D1 | Tần suất | AI tự chèn ít, đúng ngữ cảnh: mặc định tối đa 1–2 dấu mỗi phút. Không ép đủ hạn mức; nhiều tập có thể không cần dấu nào. Người dùng chỉnh tay được. |
| D2 | TTS đầu tiên | Giữ Edge TTS. Tinh chỉnh âm cảm thán và nghe duyệt theo từng giọng; chưa thêm engine/model hay API trả phí. |
| D3 | Hắng giọng | Phát tiếng “ahem” ngắn, rồi hạ tông một đoạn lời thoại ngắn kế tiếp, sau đó trở về tông speaker đã chọn. |
| D4 | Kiểu cười | AI chọn “ha ha” hoặc “hi hi” theo nhân vật/ngữ cảnh; người dùng đổi được. |

## 3. Thiết kế đề xuất

### 3.1 AI chọn dấu sau khi lời thoại đã hợp lệ

1. Chạy tạo outline/section, repair, kiểm tra tổng số từ và CEFR như hiện nay; giữ lời thoại sạch trong các checkpoint đó.
2. Trước khi lưu kịch bản cuối, gọi AI một lượt **annotation** bằng AI router hiện có. AI chỉ trả danh sách chỉ dẫn dạng `{line_index, after_word_index, cue_type, variant}`; không được viết lại lời thoại hoặc đổi speaker. Vị trí được đánh theo từ thoại sạch, không theo byte/Unicode offset.
3. JSON Schema tại gateway và Pydantic kiểm tra enum/vị trí; service kiểm tra hạn mức theo thời lượng, khoảng cách giữa dấu, ngữ cảnh và không lặp cảm xúc dày. Chỉ dẫn sai bị bỏ; nếu lượt annotation lỗi, lưu kịch bản sạch đã tạo thành công.
4. Chèn thẻ vào bản xuất cuối bằng code thuần, theo vị trí đã xác thực. Tái tạo một câu dùng cùng quy tắc với ngữ cảnh ngắn; thao tác sửa tay giữ quyền ưu tiên của người dùng.

Điều này đáp ứng “AI tạo xong đã có cảm xúc” mà không đưa thẻ vào phép đếm từ và repair. Các prompt mới đặt trong `backend/ai/prompts/`; không hardcode lời nhắc trong service.

### 3.2 Cú pháp kịch bản

- Giữ tương thích `[cười]`, `[thở dài]`, `[hắng giọng]` của bản hiện tại.
- Thêm `[cười:ha-ha]` và `[cười:hi-hi]` để AI/người dùng chọn biến thể. Trình sửa có menu chọn kiểu cười, nhưng vẫn cho sửa văn bản trực tiếp.
- `[thở dài]` và `[hắng giọng]` giữ cú pháp ngắn. Không in các thẻ vào SRT, karaoke, Learning Content hay YouTube transcript.
- Chỉ các thẻ được hỗ trợ là chỉ dẫn; dấu ngoặc vuông khác vẫn là chữ thường hoặc bị cảnh báo khi lưu, không biến thành lệnh TTS.

### 3.3 Thuật toán âm thanh cho Edge TTS

- Tách câu theo chỉ dẫn, tổng hợp các đoạn thoại và âm cảm thán bằng cùng speaker/voice; ghép sau khi giải mã để đo thời lượng, dịch word boundaries theo âm thanh thực tế.
- Với tiếng cười, thử các chuỗi âm ngắn “Ha ha”, “Hee hee”/“Hi hi” trên các giọng đang dùng. Với tiếng thở dài, thử “Ahh”, “Haa” và “Haiz” bằng nghe thực tế; không tự nhận đây là tiếng thở sinh học nếu chỉ nghe như chữ được đọc. Với hắng giọng, thử “Ahem” ngắn và có khoảng ngắt nhỏ.
- Sau `[hắng giọng]`, tách một cụm ngắn (đến dấu câu kế tiếp hoặc giới hạn khoảng 4–8 từ) để tổng hợp ở pitch thấp hơn cài đặt hiện tại một mức nhỏ, rồi trở về pitch gốc. Không hạ toàn bộ phần còn lại của câu/tập. Giới hạn pitch/rate theo khả năng Edge và cho phép bỏ hiệu ứng nếu nghe méo.
- Thêm phiên bản công thức âm vào fingerprint cache để thay đổi lựa chọn phoneme hoặc pitch buộc tạo lại audio. Giữ giọng, tốc độ, âm lượng do người dùng đã chọn.

### 3.4 Trải nghiệm biên tập

- Step 2 hiển thị thẻ AI đã đặt ngay trong câu, cho sửa/xóa và chèn tại con trỏ. Menu “cười” chọn được ha ha/hi hi.
- Nút “Nghe” chỉ phát bản đã lưu mới nhất; audio preview cho phép người dùng duyệt từng câu. Có thể ghi chú ngắn rằng Edge đọc **âm mô phỏng** và kết quả tùy giọng.
- Khi người dùng tái tạo một câu, thẻ AI của câu đó được tính lại; các câu khác và chỉnh sửa tay của chúng không đổi. Nếu người dùng chỉ sửa văn bản thủ công, không có AI tự ghi đè dấu đã sửa.

## 4. Giới hạn nghiên cứu và hướng sau

- [Dự án edge-tts](https://github.com/rany2/edge-tts#custom-ssml) xác nhận endpoint chỉ cho một voice/prosody, không cho SSML tùy biến để ra lệnh cảm xúc hay chèn file âm trực tiếp. [Tác giả edge-tts](https://github.com/rany2/edge-tts/discussions/176) cũng nói không hỗ trợ emotion qua custom SSML. Vì vậy hạ pitch/rate và tổng hợp âm cảm thán thành nhiều đoạn là **suy luận kỹ thuật cho ứng dụng này**, không phải tính năng emotion gốc của Edge.
- [Azure Speech SSML](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice) có style và chèn âm ghi sẵn, nhưng là dịch vụ riêng, không thuộc engine hiện hành.
- [Qwen3-TTS chính thức](https://github.com/QwenLM/Qwen3-TTS) hỗ trợ hướng dẫn cảm xúc bằng ngôn ngữ tự nhiên. Nó là ứng viên nghiên cứu cho giai đoạn sau nếu âm Edge không đạt; chưa được owner chọn tích hợp. Không giả định Qwen chính thức nhận trực tiếp cú pháp thẻ của ứng dụng.

## 5. Rủi ro và tiêu chí chấp nhận đề xuất

| Rủi ro | Cách xử lý |
|---|---|
| AI lạm dụng cảm xúc hoặc đặt sai tình huống nghiêm túc | Hạn mức cứng, ví dụ âm nhạy ngữ cảnh; không ép quota; duyệt tay. |
| Thẻ làm sai budget/CEFR/đánh giá lặp | Chỉ annotate sau validation; mọi phép tính từ thoại dùng bản bỏ thẻ. |
| Âm ghép nghe gãy hoặc “haiz” thành từ khác | Bảng mẫu nghe theo từng voice; khoảng ngắt/fade ngắn; fallback không hiệu ứng. |
| Karaoke và phụ đề lệch | Đo MP3 sau giải mã, không đưa âm cue vào word boundaries, kiểm tra SRT và preview. |
| Thay công thức mà tái dùng cache cũ | Version hóa công thức trong line fingerprint. |
| AI annotation lỗi | Lưu lời thoại sạch; thông báo cue stage không thành công nếu UI có trạng thái. |

Tiêu chí chấp nhận: kịch bản AI có 0–2 dấu/phút đúng ngữ cảnh; AI chọn được hai kiểu cười; người dùng sửa/xóa được; `[hắng giọng]` có tiếng ngắn và cụm tiếp theo trầm hơn; giọng quay về cấu hình gốc; phụ đề/transcript không chứa thẻ; preview và audio xuất dùng cùng kết quả; lỗi annotation không làm mất kịch bản.

## Mở lại sau bản 2.0.0 — chênh lệch mẫu nghe và audio thực tế

Ngày 2026-10-23, owner phản hồi chất lượng cười/thở dài/hắng giọng trong app không giống mẫu OmniVoice đã được nghe và hỏi có nên thay engine hiện tại bằng OmniVoice.

### Bằng chứng từ workspace (chỉ đọc)

- DB hiện có 80 speaker, tất cả `tts_engine=edge_tts`; 5 nhân vật đều mặc định Edge. Đây là trạng thái lưu trong DB, không phải phép nhận diện engine từ một file audio cụ thể owner đang nghe.
- `.venv-omnivoice/Scripts/python.exe` chưa tồn tại; kiểm tra service báo OmniVoice chưa sẵn sàng. Bản 2.0 đã tích hợp UI/worker nhưng chưa hoàn thành môi trường/model và chưa có nghiệm thu inference local.
- Mẫu được owner khen trước đó là cặp audio Voice Design từ Hugging Face Space, không phải output từ luồng Edge trong app.
- `vocal_cues.py` biến dấu thành chữ `Ha, ha`, `Ahh`, `Ahem`; `tts_service.py` tổng hợp bằng Edge rồi ghép. Do đó chất lượng không tương đương âm phi ngôn ngữ gốc của OmniVoice.
- Nhánh OmniVoice hiện gửi `instruct` cho mỗi câu; chưa lưu mẫu tham chiếu hoặc `VoiceClonePrompt` của nhân vật. Các kiểu ha-ha/hi-hi cùng đổi thành `[laughter]`, chưa điều khiển riêng hai kiểu cười.
- RTX 3060 có 12 GiB VRAM; snapshot kiểm tra còn 9954 MiB trống. Chưa đo mức dùng thực tế hoặc tốc độ OmniVoice trên GPU này.

### Nghiên cứu chính thức và giới hạn

- [OmniVoice README](https://github.com/k2-fsa/OmniVoice#non-verbal--pronunciation-control): có `[laughter]`, `[sigh]`; danh sách công bố chưa có throat-clear/ahem. Không đồng nhất “hằn giọng” với “hắng giọng”: giọng căng/trầm là phong cách lời thoại; ahem là một âm riêng.
- [Voice cloning](https://github.com/k2-fsa/OmniVoice#voice-cloning): dùng audio và transcript tham chiếu, có thể lưu `VoiceClonePrompt` để tái dùng. Đây là hướng đề xuất để giữ giọng nhân vật; chưa được chứng minh ổn định trong project này.
- [Tips](https://github.com/k2-fsa/OmniVoice/blob/master/docs/tips.md): đoạn 1–2 giây có thể không ổn định khi thiếu tham chiếu. Không nên kỳ vọng chỉ lặp cùng mô tả Voice Design là luôn giữ đúng một giọng.
- [Model card OmniVoice](https://huggingface.co/k2-fsa/OmniVoice#license) ghi code Apache-2.0 nhưng trọng số CC-BY-NC. Cần làm rõ quyền dùng theo mục đích kênh trước khi chọn làm engine sản xuất thương mại; đây là ghi nhận nội dung model card, chưa phải kết luận pháp lý về output.
- [Chatterbox Turbo](https://huggingface.co/ResembleAI/chatterbox-turbo) là ứng viên đối chiếu nếu cần lựa chọn có model card MIT: tiếng Anh, tag `[laugh]`, `[chuckle]`, `[cough]`, dùng audio tham chiếu. Chưa thử trên máy, chưa xác nhận sigh/ahem. Không dùng cough thay ahem rồi coi như đã đáp ứng.

### Đề xuất và quyết định còn chờ

Đề xuất sinh trọn câu kèm cảm xúc bằng engine có hỗ trợ âm phi ngôn ngữ. Với mỗi nhân vật, chọn mẫu giọng được owner duyệt và tái sử dụng làm tham chiếu; preview và audio xuất đi cùng một đường tổng hợp. Chỉ chuyển mặc định sau khi nghe nghiệm thu bằng chính pipeline app. Test parser/API và đóng gói không thay thế nghiệm thu chất lượng âm thanh.

Chưa có quyết định thay mặc định hoặc chuyển dữ liệu. Hai câu hỏi đã gửi owner: chấp nhận giọng OmniVoice mới hay cần gần giọng Edge hiện tại; kênh có dùng thương mại/kiếm tiền hay không. Việc chỉ đổi engine không tự tái tạo audio đã xuất hoặc bảo đảm đúng giọng Brian/Jenny.

## Phases

### Owner decision superseding the speech experiments — 2026-10-24

Owner found video B much better than A, but male sighs could change into an animal-like growl and female emotion was unclear. Owner requested returning the entire product to the old Edge voices and removing emotion insertion from scripts. [Phase 77](../../.viepilot/phases/77-edge-plain-speech/PLAN.md) implements this direction. Chatterbox/OmniVoice emotion integration is no longer an active follow-up; the audition recordings remain historical. The 12-profile bank's earlier listening preference is not authorization to ship those voices. No audition-only 120ms delay is adopted by the Edge renderer.

### Điều chỉnh mới nhất — 2026-10-24

Owner đánh giá bộ **12 hồ sơ giọng khá tốt**, nhưng từ chối karaoke của video PoC 32 giây: chữ chạy nhanh hơn giọng sau biểu cảm. Thu gọn phạm vi Chatterbox chỉ còn **cười, thở dài và tức giận**, loại hắng giọng và các sắc thái khác khỏi vòng thử tiếp theo. Tức giận là style lời thoại, không phải cue âm phi ngôn ngữ. [Bộ thử R2](chatterbox-karaoke-r2-2026-10-24.md) giữ nguyên audio cười/thở dài để đối chiếu, sửa độ trễ MP4 đo được và cung cấp hai phương án hiển thị timing; cả karaoke và tức giận còn chờ owner nghiệm thu. Đây là điều chỉnh cho hướng Chatterbox mới, không sửa lại lịch sử implementation Phase 74/75 hoặc tự đổi bản cài hiện tại.

### Phase 74 — AI vocal cues và Edge TTS prosody

- Annotation sau kiểm tra kịch bản, áp dụng hạn mức và tương thích tái tạo một câu.
- Parser các biến thể cười, âm cảm thán theo giọng, hạ tông ngắn sau hắng giọng, cache version và đồng bộ mốc từ.
- Step 2 cho đổi biến thể, nghe duyệt; cập nhật phụ đề/transcript và tài liệu.
- Nghe nghiệm thu trên những giọng Edge được cấu hình, gồm nam/nữ và nhiều accent, trước khi đóng gói.

### Bổ sung — Phase 1: Kiểm chứng engine cảm xúc và giọng nhân vật (đề xuất, chưa chốt)

Nghiên cứu ba repository owner bổ sung được ghi tại [báo cáo so sánh engine](tts-engine-research-2026-10-23.md). Điều chỉnh đề xuất: đưa VieNeu v3 Turbo vào vòng nghe đối chiếu với OmniVoice vì có ánh xạ cả ba cue và model card công bố quyền dùng thương mại cho preset/weights; chưa kết luận chất lượng tiếng Anh. OmniVoice Studio là nguồn tham khảo workflow/adapter có LICENSE FSL; SEA-G2P là lớp phát âm đã nằm trong SDK VieNeu.

Owner sau đó xác định **chỉ quan tâm tiếng Anh và cảm xúc/sắc thái**, yêu cầu đếm giọng, chọn dự án và tạo mẫu thật. [English audition](english-tts-audition-2026-10-23.md) cập nhật đề xuất sang Chatterbox Turbo: danh mục Edge live có 47 giọng; Chatterbox mở rộng bằng tham chiếu, không có danh mục cố định tương đương. Đã sinh local 32 mẫu Chatterbox và 32 mẫu Edge cho bốn giọng tham chiếu, xuất trang nghe A/B và MP3. Owner sau đó xác nhận Chatterbox có chất lượng cao hơn; chưa nghiệm thu riêng từng sắc thái hoặc thay engine sản phẩm. Yêu cầu tiếp theo là mở rộng giọng và hỗ trợ karaoke, được phân tích tại [thư viện giọng và karaoke](chatterbox-voices-karaoke-2026-10-23.md).

- Chọn ứng viên theo nhu cầu sử dụng và thông tin giấy phép. Chuẩn bị giọng tham chiếu được phép dùng theo mục đích đã chọn.
- Nghe đối chiếu ít nhất hai giọng trên câu thường, câu có cười và thở dài; đánh giá độ nhất quán qua nhiều câu, tiếng Anh dễ nghe, nhịp nối và việc đọc sai/bỏ từ.
- Sinh qua đúng đường preview và production của app; so sánh WAV/MP3 đầu ra. Đo thời gian và đỉnh VRAM thực tế. Phân biệt hạ/trầm giọng với tiếng hắng giọng, kiểm chứng riêng khả năng từng hiệu ứng.

### Bổ sung — Phase 2: Mặc định mới và chuyển project (đề xuất, phụ thuộc Phase 1)

- Lưu giọng đã duyệt cho từng nhân vật, tái dùng cho các câu và các tập; không chỉ thiết kế lại giọng độc lập ở từng câu.
- Chọn engine mặc định cho project mới theo kết quả nghe; project cũ chuyển theo thao tác rõ ràng và cần tái tạo audio. Cache phải xét engine, tham chiếu giọng và tham số tạo.
- Thông báo cue không hỗ trợ và engine thực dùng. Owner đã yêu cầu karaoke với Chatterbox: bổ sung forced alignment từ audio thật vào sidecar hiện có, ưu tiên khảo sát WhisperX alignment tiếng Anh; nghe/nhìn kiểm chứng ở vị trí cười/thở dài/hắng giọng trước khi chuyển mặc định. Chi tiết và hai giai đoạn thư viện giọng/alignment ở tài liệu bổ sung trên.

Owner tiếp tục yêu cầu “thử phương án này xem sao”. [PoC 2026-10-24](chatterbox-karaoke-poc-2026-10-24.md) tạo 12 hồ sơ lưu/nạp lại và 48 mẫu local, thử alignment CPU và xuất video bằng renderer hiện có. Phát hiện WhisperX thông thường kéo chữ qua tiếng cười; adapter CTC có cue là phần thử nghiệm riêng, chưa nghiệm thu production. Bộ xuất ở `data/exports/chatterbox-voices-karaoke-20261023/`; chưa thay cấu hình engine/project hay bản cài.

## Câu hỏi còn mở

- Sau phản hồi bản 2.0, cần chốt giọng mới cho từng nhân vật và mục đích sử dụng thương mại trước khi crystallize phần thay engine. Ngưỡng chấp nhận âm thanh phải quyết định bằng mẫu nghe từ đúng pipeline app.
- Nếu thử nghe cho thấy Edge không đủ tự nhiên, quay lại owner để quyết định engine TTS mới; không tự động chuyển engine trong Phase 74.

## Project meta intake (FEAT-009)

- **status:** inherited_none (existing brownfield profile)
- **profile_id:**
- **profile_path:**
- **binding** (.viepilot/META.md):

Feature này không đổi hồ sơ tổ chức của dự án.

## Crystallization

[Phase 74 plan](../../.viepilot/phases/74-ai-vocal-cues/PLAN.md), [specification](../../.viepilot/phases/74-ai-vocal-cues/SPEC.md), phase state and four bounded task cards were created 2026-10-23. Implementation and 276 targeted checks later completed; a real Edge sample was produced. The owner reports its laughter is not satisfactory, so audible acceptance remains open.

## Follow-up brainstorm — tiếng cười Edge chưa đạt, nghiên cứu OmniVoice (2026-10-23)

### Tín hiệu từ lần nghe thật

Owner nghe [mẫu Edge](../../data/tmp/phase74-vocal-cues-en-US-BrianNeural.mp3) và phản hồi rằng kết quả gần như không nghe ra tiếng cười, nên Phase 74 hiện **chưa đạt tiêu chí âm thanh**, dù parser, annotation và các kiểm tra tự động đã qua. Không nên tiếp tục tinh chỉnh “ha ha/hi hi” như thể đó là tiếng cười tự nhiên.

### Nghiên cứu repository chính thức

- README OmniVoice mô tả hỗ trợ ký hiệu phi ngôn ngữ trong chính văn bản TTS; ví dụ cụ thể dùng `[laughter]` trong cùng câu thoại. Danh sách được README ghi rõ còn có `[sigh]`, nhưng **không nêu tag throat-clear/ahem**. Đây là hướng phù hợp hơn với tiếng cười/thở dài do model sinh cùng lượt với câu thoại, thay vì Edge đọc các âm tiết thành từ. Nguồn: [OmniVoice README — Non-Verbal & Pronunciation Control](https://github.com/k2-fsa/OmniVoice#non-verbal--pronunciation-control).
- Có hai cách tạo giọng: `instruct` cho **Voice Design** không cần audio tham chiếu (giới tính, tuổi, pitch, accent/style); `ref_audio`/`ref_text` cho **Voice Cloning**. Tài liệu nói cloning là chế độ ổn định hơn, Voice Design được huấn luyện cho tiếng Trung và tiếng Anh, nhưng điều đó không chứng minh rằng `[laughter]` sẽ nghe tự nhiên với mọi voice. Nguồn: [OmniVoice README — Voice Design and Voice Cloning](https://github.com/k2-fsa/OmniVoice#python-api).
- README khuyến nghị môi trường ảo mới và đưa ví dụ cài PyTorch CUDA 12.8 riêng, rồi cài package OmniVoice. Vì ứng dụng hiện dùng `.venv` cho Edge và môi trường có GPU RTX 3060, cần kiểm tra model/package/CUDA hiện có trước khi thử; không cài dependency lớn vào app env trong giai đoạn brainstorm. Thư mục model OmniVoice và package trong `.venv` không có ở workspace tại lần kiểm tra này.

### Hướng thử đề xuất

Làm một proof-of-concept độc lập, chưa đổi pipeline sản phẩm: dùng voice design với giọng nam American và nữ American/British; chạy cùng một bộ câu cho `[laughter]`, `[sigh]`, câu thoại thường và đối chứng Edge. Nghe tiếng cười trước khi quyết định tích hợp. Nếu chất lượng cười đạt, mới đánh giá lựa chọn TTS toàn câu bằng OmniVoice Voice Design so với cloning từ audio tham chiếu **do owner cung cấp/cho phép**. Không ghép riêng tiếng cười OmniVoice chồng lên giọng Edge cho production nếu chưa chứng minh nối âm và độ khớp giọng; hai engine có thể nghe thành hai người khác nhau. Giữ Edge là fallback cho tới khi owner chốt sau mẫu nghe.

### Quyết định còn cần từ owner

1. PoC trước bằng Voice Design, không cần thu âm tham chiếu, chấp nhận giọng OmniVoice có thể không khớp chính xác voice Edge đang gán cho nhân vật.
2. Chỉ thử Voice Cloning nếu owner chọn và cung cấp/cho phép dùng một mẫu giọng tham chiếu cho từng nhân vật.
3. Ưu tiên khảo sát nguồn âm cười ghi sẵn/phi ngôn ngữ riêng, ghép với Edge, nếu cần giữ nguyên đúng giọng Edge; sẽ phải giải quyết license/quyền dùng và khớp giọng.

Chưa cài đặt model/package, chưa gọi GPU inference và chưa sửa kiến trúc Phase 74. Kết quả thử âm là cổng trước mọi quyết định tích hợp.

## OmniVoice Voice Design PoC — kết quả nghe thử (2026-10-23)

Owner đã chọn thử **Voice Design trước**. Không tích hợp OmniVoice vào pipeline sản phẩm ở bước này.

### Âm thanh tạo được

Tạo cặp đối chiếu bằng OmniVoice Voice Design qua **Hugging Face Space API công khai** (không phải inference local trên RTX 3060): cùng giọng thiết kế nữ trẻ, pitch trung bình, accent Mỹ, một câu có `[laughter]` và một câu gần tương đương không tag.

- Audio ghép: `data/tmp/omnivoice-voice-design-poc/outputs/omnivoice-voice-design-poc.mp3` (MP3, 192 kbps, 9.84 giây).
- WAV từng đoạn và thứ tự nghe: cùng thư mục `outputs/`; xem `LISTENING.txt` và `manifest.json`.
- Space hết quota ZeroGPU ẩn danh trước khi sinh biến thể nam Anh và `[sigh]`; hai biến thể đó chưa có trong bản này. Chưa nghe/đánh giá thay owner; cần owner nghe để xác định tiếng cười có tự nhiên hơn Edge không.

### Giới hạn của thử nghiệm local

Đã xác nhận gói OmniVoice 0.2.1 nạp được trong môi trường PoC riêng trên Python 3.14, PyTorch 2.11.0+cu128 và nhận CUDA. Tải trọng số local từ Hugging Face bị chậm/đứng ở khoảng 0.5 GB đã tải; dừng trước inference local. Môi trường ứng dụng và `.venv-image` không bị cài package mới; PoC dùng `data/tmp/omnivoice-poc-venv`. Có cache tải dở tại `data/tmp/omnivoice-hf-cache`.

### Kết luận nghiên cứu cập nhật

OmniVoice vẫn đáng thử tiếp vì hỗ trợ tag nội tuyến `[laughter]` và `[sigh]` ngay trong câu, còn Voice Design điều khiển giới tính/tuổi/pitch/accent mà không cần audio tham chiếu. Đây là hướng có thể sinh cùng giọng trong một lượt thay vì yêu cầu Edge đọc các âm tiết cười như từ. Tuy nhiên, hiện chỉ có một cặp audio từ Space công khai; chưa đủ kết luận chất lượng, độ ổn định, hiệu năng RTX 3060 hoặc chi phí tích hợp. README chỉ liệt kê các tag cười/thở dài và một số tag biểu cảm; không liệt kê tag hắng giọng/ahem. Voice Design được tài liệu mô tả là huấn luyện cho tiếng Anh và tiếng Trung.

**Bước quyết định tiếp theo:** owner nghe file MP3 và cho biết tiếng cười đã đạt chưa. Nếu đạt, tiếp tục kiểm chứng local với thêm giọng/câu `[sigh]` và đo VRAM/thời gian; nếu chưa đạt, chưa đưa OmniVoice vào Phase 74. Nguồn: [OmniVoice README](https://github.com/k2-fsa/OmniVoice#non-verbal--pronunciation-control), [Hugging Face Space](https://huggingface.co/spaces/k2-fsa/OmniVoice).
### Phản hồi nghe thử của owner

Owner đã nghe cặp MP3 Voice Design và phản hồi: “rất tốt quá tuyệt vời”. Ghi nhận tiếng cười OmniVoice trong mẫu này đạt kỳ vọng nghe thử ban đầu. Đây là đánh giá cho cặp giọng nữ Mỹ được sinh qua Hugging Face Space; các biến thể `[sigh]`, giọng khác và inference local vẫn cần xác nhận riêng trước khi quyết định tích hợp.

## Integration authorization ? Phase 75 (2026-10-23)

After listening to the public Space Voice Design laughter sample, the owner said ?r?t t?t qu? tuy?t v?i? and explicitly requested integration. Phase 75 therefore makes OmniVoice an optional, explicit per-speaker local engine; Edge remains the default. Step 4 includes a Voice Design description and isolated sample preview. Production synthesis uses an offline-only one-shot worker under the shared GPU lease. `[laughter]` and `[sigh]` are mapped to native model tags; `[h?ng gi?ng]` is rejected without fallback. The accepted sound was produced remotely through the public Space; local model setup, GPU measurement and owner listening to local output are still pending. This decision supersedes the earlier brainstorm's ?no integration yet? recommendation.
