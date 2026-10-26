# Chatterbox Turbo — thư viện giọng tiếng Anh và karaoke

Ngày: 2026-10-23. Trạng thái: nghiên cứu và đề xuất kiến trúc trong brainstorm; chưa triển khai vào ứng dụng.

**Cập nhật 2026-10-24:** owner yêu cầu thử phương án; đã tạo [PoC 12 hồ sơ và karaoke](chatterbox-karaoke-poc-2026-10-24.md). Bộ thử có 48 mẫu local và video dùng renderer hiện có. Alignment nguyên bản gặp lỗi kéo chữ qua tiếng cười; adapter CTC có cue được thử riêng và cần owner nghe/nhìn nghiệm thu. Chưa tích hợp production.

## Yêu cầu và bằng chứng

- Owner đã nghe bộ đối chiếu và nhận xét Chatterbox có chất lượng cao hơn. Đây là đánh giá tổng thể của bộ audition, chưa phải nghiệm thu mọi sắc thái hoặc luồng production.
- Cần nhiều giọng tiếng Anh cho nhiều nhân vật và giữ phụ đề karaoke theo từng từ.
- Bốn giọng trong audition là bốn mẫu tham chiếu từ Edge (Brian/Jenny/Ryan/Sonia), không phải giới hạn hay danh mục preset của Chatterbox. Chưa có ngân hàng Chatterbox sản phẩm được duyệt.

## Phase 1 — giọng nhân vật và đường tổng hợp thống nhất (đề xuất)

Chatterbox Turbo nhận audio tham chiếu qua `audio_prompt_path`. Tài liệu chính thức minh họa mẫu 10 giây. Tạo thêm hồ sơ tham chiếu cho phép bổ sung nhân vật mà không huấn luyện lại model; số hồ sơ lưu được không phải số giọng độc lập đã được chứng minh chất lượng.

Đề xuất ngân hàng khởi đầu **12 hồ sơ**: US/UK × nam/nữ × ba chất giọng dễ phân biệt trong mỗi nhóm. Con số này là mục tiêu tuyển chọn, không phải 12 preset có sẵn hay cam kết tạo được 12 giọng đủ khác biệt. Tuổi, độ trầm/sáng và accent là nhãn biên tập sau nghe duyệt.

Nguồn bổ sung:

1. Upload/thu một đoạn nói tiếng Anh sạch, một người nói, không nhạc, khoảng 10–15 giây, có quyền sử dụng phù hợp. Đánh giá lại trên lời thoại mới vì chất lượng đầu vào không bảo đảm giữ đúng accent hoặc nhận dạng giọng.
2. Chọn các mẫu tổng hợp hiện có làm tham chiếu cho audition mở rộng. Danh mục 47 giọng Edge không đồng nghĩa 47 bản clone sẽ giữ nguyên chất lượng/đặc điểm.
3. Hướng tùy chọn: dùng Qwen3-TTS VoiceDesign để tạo mẫu từ mô tả, rồi đưa WAV đó vào Chatterbox. Qwen có tài liệu Design → Clone trong hệ Qwen; việc dùng mẫu sang Chatterbox là đề xuất của dự án, phải nghe kiểm chứng riêng. Chatterbox Turbo hiện không phải engine thiết kế giọng trực tiếp từ mô tả tiếng Việt/Anh.

Mỗi hồ sơ dự kiến có ID, tên, accent, nhãn giọng, audio tham chiếu, checksum, nguồn, phiên bản và mẫu nghe. Người dùng nghe/chọn giọng rồi gán cho nhân vật. Đổi reference tạo phiên bản mới; project giữ phiên bản đã chọn, tránh sửa thư viện làm đổi giọng các tập cũ.

Source Turbo có `Conditionals.save/load` cho T3 và S3Gen. Có thể tạo và lưu conditioning khi duyệt giọng, sau đó tải lại đúng hồ sơ trong worker. Đây không phải fine-tuning. Cache phải gắn với checksum reference và phiên bản model/code; không mặc định conditioning tương thích giữa các lần đổi SDK/model. Chỉ nạp file conditioning do app tạo, không nhận file pickle tùy ý từ upload.

Giữ cùng hồ sơ cho câu thường, cười, thở dài và hắng giọng; không đổi người nói để tạo cảm xúc. Các tag native được kiểm chứng riêng; không coi `exaggeration`/`cfg_weight` là thanh điều khiển cảm xúc có tác dụng trong Turbo hiện tại. `[clear throat]` không tự bảo đảm phần sau được hạ tông như yêu cầu cũ; cần quyết định/nghe duyệt riêng trước khi hứa tính năng đó.

## Phase 2 — karaoke theo audio Chatterbox thật (yêu cầu, giải pháp đề xuất)

Luồng dự kiến:

```text
Kịch bản có cue + hồ sơ giọng
  → Chatterbox tạo audio cả câu
  → chốt audio cache và giải mã audio cuối
  → forced alignment với lời thoại đã bỏ cue
  → .words.json của câu
  → mixer cộng offset theo timeline thực
  → renderer karaoke hiện có
```

Ứng viên đầu: lớp alignment của WhisperX + `facebook/wav2vec2-base-960h` cho tiếng Anh. API `align` nhận transcript đã biết; không cần chạy toàn bộ ASR/diarization chỉ để tìm lại kịch bản và nhân vật đã có. Bản sao resample 16 kHz phục vụ aligner không thay đổi audio phát. Model card Wav2Vec2 này công bố Apache-2.0; khóa revision/dependency trước khi tích hợp.

Các điểm tích hợp đã đọc:

- `backend/ai/tts/tts_service.py`: hiện lưu word boundaries từ Edge vào sidecar; engine không có timing chưa có dữ liệu tương đương.
- `backend/media/audio_service.py::_aggregate_word_boundaries`: đọc `{text, offset_sec, duration_sec}` từ `.words.json`, cộng vị trí câu theo audio đã giải mã. Mixer đã có khoảng ngắt giữa các nhân vật.
- `backend/media/video_renderer_remotion.py`, `renderer/src/karaoke.ts` và `CaptionBand.tsx`: đã nhận word timestamps để tô từng từ. Có thể tái dùng khi Chatterbox có sidecar đúng.

Yêu cầu chất lượng:

- Bỏ `[cười]`/`[thở dài]`/`[hắng giọng]` khỏi transcript phụ đề, nhưng giữ thời gian các âm đó trong audio. Khoảng cười/thở dài phải để trống phần tô chữ; đo riêng trường hợp cue ở đầu/giữa/cuối câu vì aligner có thể kéo dài từ qua âm phi ngôn ngữ.
- Căn theo audio cuối được phát, trước trộn nhạc; tính lại nếu đổi tốc độ, cắt/ghép hoặc tạo lại audio. Khớp sidecar bằng checksum audio/transcript, engine/model/reference và phiên bản alignment để tránh dùng timing cũ.
- WhisperX hiện có nội suy timestamp mặc định cho từ không căn được. Adapter phải phát hiện từ có bằng chứng alignment thực (điểm CTC/char alignment), phân biệt với mốc nội suy; không mặc nhiên xuất kết quả nội suy như timing chính xác. Chuẩn hóa số/viết tắt cho aligner và ánh xạ về văn bản hiển thị.
- Từ bị bỏ/đọc sai hoặc timing độ tin cậy thấp phải được báo để nghe/tạo lại hoặc chuyển câu đó về phụ đề thường. Không chia đều thời lượng để giả lập karaoke. Forced alignment không phải chứng nhận model đã đọc đúng mọi từ.
- Chạy worker biệt lập, chia sẻ GPU lease với tạo ảnh/TTS. Có thể căn CPU hoặc tuần tự sau TTS; chọn theo đo thực tế trên RTX 3060, không giữ hai model GPU đồng thời khi chưa đo.
- Karaoke trong video dùng renderer hiện tại. SRT xuất rời vẫn là phụ đề theo câu; nếu cần file karaoke mở bằng phần mềm khác, thêm ASS có word durations là một phạm vi riêng cần chốt, không gán nhãn SRT thường là karaoke.

## Điều kiện trước khi chuyển mặc định

1. Tuyển chọn/nghe duyệt hồ sơ giọng trên nhiều câu, gồm hội thoại hai người, câu dài và ba cue cần thiết. Chấp nhận độ phân biệt và nhất quán nhân vật theo nghe thực tế.
2. PoC alignment trên MP3 cuối và xuất video ngắn để nghe/nhìn karaoke ở vị trí cue. Đã thực hiện ở lần thử 2026-10-24; còn chờ owner nghiệm thu, stress cases và xác định runtime sản phẩm.
3. Đo generation + alignment + VRAM và thời gian khởi động trên đường preview/production chung, không lấy riêng thời gian generate ngắn làm tốc độ cả tập.
4. Sau khi có kế hoạch triển khai được duyệt, bổ sung engine/library/aligner và migration có lựa chọn. Giữ project cũ theo engine/voice cũ; chỉ tạo lại khi người dùng chọn chuyển. Edge có thể giữ làm lựa chọn nhẹ cho máy không GPU; karaoke không bắt buộc giữ Edge nếu alignment Chatterbox đạt.

## Nguồn chính thức

- [Turbo model card và reference example](https://huggingface.co/ResembleAI/chatterbox-turbo).
- [Turbo Conditionals và prepare_conditionals — snapshot đã dùng cho audition](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/tts_turbo.py).
- [WhisperX API và giới hạn](https://github.com/m-bain/whisperX#python-usage-).
- [WhisperX alignment implementation, gồm nội suy](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py).
- [English alignment model card](https://huggingface.co/facebook/wav2vec2-base-960h).
- [Qwen Voice Design then Clone](https://github.com/QwenLM/Qwen3-TTS#voice-design-then-clone).
