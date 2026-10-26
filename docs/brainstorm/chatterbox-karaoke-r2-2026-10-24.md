# Chatterbox R2 — thu gọn cảm xúc và kiểm tra lại karaoke

Ngày: 2026-10-24, Asia/Bangkok. Trạng thái: bản thử riêng, chờ owner nghe/nhìn lại; không có thay đổi vào source sản phẩm, DB hoặc bản cài.

## Phản hồi và phạm vi mới

Owner nhận xét **12 giọng khá tốt**, nhưng video 32 giây có cảm giác karaoke chạy nhanh hơn lời thoại sau biểu cảm. Nhiều biểu cảm nghe lỗi, đặc biệt hắng giọng và các sắc thái lạ. Phạm vi mới chỉ giữ **cười, thở dài, tức giận**. Bộ 12 hồ sơ được giữ nguyên để tránh thay đổi biến thử.

- Cười/thở dài: âm phi ngôn ngữ nội tuyến, dùng `[laugh]`/`[sigh]`.
- Tức giận: phong cách nói, thử `[angry]` cho câu; không coi là một khoảng âm riêng để wildcard nuốt/tạo khoảng trống trong karaoke.
- Hắng giọng, hi-hi/chuckle riêng, happy, whisper và các hiệu ứng khác không có trong bộ nghe R2. Đây là thay đổi phạm vi đề xuất; bản cài hiện có chưa bị sửa.

## Điều tra đồng bộ

### Đã xác nhận bằng đo tín hiệu

Giải mã WAV nguồn và audio của MP4 cũ, rồi cross-correlation từng câu (6 cửa sổ, trước/sau nhiều cue): audio MP4 trễ **42.75 ms** tại cả sáu câu, độ phân giải đo 0.25 ms. Độ trễ đo được là hằng số, **không tăng dần sau biểu cảm** trong file này. Vì thế chưa được kết luận số đo này giải thích trọn vẹn cảm giác owner báo.

Ghép lại video với audio encode từ đúng PCM gốc bằng ffmpeg tạo metadata xử lý encoder delay: file kiểm chứng giữ nguyên hình của video cũ có độ lệch đo **0 ms** ở sáu cửa sổ kiểm tra. Bản R2 áp dụng bước này sau Remotion. Không dịch thời gian chữ 43 ms để bù một audio lỗi.

`createTikTokStyleCaptions` giữ nguyên start/end word timestamps. Kiểm tra đủ 6 dòng × 2 biến thể cho thấy helper không co/thay timing. Kiểm tra CTC greedy không ép transcript trên bốn mẫu cười/thở dài Brian/Jenny khớp phần lớn vị trí bắt đầu từ sau cue trong sidecar cũ, sai khác nhỏ theo bước frame; không tái hiện được drift lớn tăng dần từ các phép đo này. CTC greedy và forced alignment dùng cùng acoustic model, không phải hai ground truth độc lập.

### Chưa được chứng minh

- Kiểm tra timeline tăng dần/đủ từ và ảnh chụp không chứng minh sync cảm nhận; kết quả cũ bị owner từ chối vẫn là kết quả không đạt.
- Wildcard CTC vẫn là PoC có rủi ro hấp thụ lời ngoài kịch bản. Không tự đánh dấu alignment là production-ready chỉ vì mốc khớp greedy CTC.
- Cảm giác từ sáng quá sớm có thể cần kiểm chứng thêm với độ trễ trình bày. Không mặc định một giá trị trễ mới cho sản phẩm dựa trên suy đoán.

## Bộ thử R2

Tệp làm việc: `data/tmp/chatterbox-karaoke-revision-20261024/`.

Tệp xuất: `data/exports/chatterbox-karaoke-r2-20261024/`, ZIP cùng tên bên cạnh.

- `LISTEN.html`: chọn bốn giọng Brian/Jenny/Ryan/Sonia, nghe cười, thở dài, câu đối chứng và câu tức giận. Điều chỉnh trễ tô chữ 0/80/120/180 ms; lựa chọn này chỉ đổi trình bày, không đổi audio.
- `KARAOKE_AUDIO_TIME.mp4`: A, word timing theo audio, đã sửa ghép audio.
- `KARAOKE_DELAY_120MS.mp4`: B, cùng audio, word highlight cố ý trễ thêm 120 ms để owner đối chiếu. Chưa chốt làm mặc định.
- `DEMO.mp3`/WAV: soundtrack; video gồm Brian/Jenny lần lượt cười → thở dài → tức giận, dài khoảng **32.24 giây**.
- `12_VOICES.mp3`: bản ngân hàng đã được owner đánh giá khá tốt, giữ nguyên.
- 16 MP3 + timing: **8 cười/thở dài sao chép nguyên byte từ bộ trước**, để chỉ đánh giá khác biệt do timing; **4 tức giận mới + 4 đối chứng không tag** có cùng văn bản.
- `manifest.json`/`verification.json`: provenance, mốc từ, cảnh báo và phép đo audio thực trong hai MP4.

Mẫu tức giận dùng conditioning đã duyệt, cùng seed 42 và temperature 0.65 cho cả hai nhánh. Tài liệu/code Turbo không cung cấp điều khiển CFG/exaggeration có tác dụng; token `[angry]` có trong tokenizer nhưng không đủ bảo đảm chất lượng. Greedy CTC của 8 mẫu tức giận/đối chứng trả đúng cùng lời thoại chuẩn hóa, chưa chứng nhận giọng tức giận đạt. Chưa dùng model khác hoặc hiệu ứng tăng volume/pitch giả làm tức giận.

## Bước nghe quyết định

Kiểm tra bộ xuất: 16 MP3 giải mã/non-silent, 244 word timestamps; 8 mẫu cười/thở dài khớp nguyên byte bản cũ; 8 mẫu tức giận/đối chứng có greedy CTC khớp toàn bộ lời thoại chuẩn hóa. Hai MP4 giải mã toàn bộ qua; audio ở sáu cửa sổ mỗi file khớp PCM nguồn với độ lệch đo 0 ms, độ phân giải 0.25 ms. Browser thử đủ bốn giọng, hai video và độ trễ tô chữ, không lỗi JavaScript. ZIP CRC qua, 6,472,272 bytes. Đã xem khung hình thực cùng timestamp 3.75s: A tô “That's”, B còn để trống theo độ trễ có chủ đích. Các kết quả này chưa thay thế nghiệm thu sync/cảm xúc bằng nghe.

1. Owner so A và B xem phiên bản nào bám giọng hơn, đặc biệt từ đầu tiên và các từ tiếp theo sau cue. Nếu cả hai vẫn sai, dùng timestamp/câu cụ thể để phân biệt lỗi aligner với độ trễ trình phát/thiết bị; không tiếp tục tăng delay tùy ý rồi coi là đã sửa.
2. Nghe tức giận so với đối chứng; nếu tag gây âm lạ hoặc hiệu ứng yếu, không bật tự động. Cần thử profile thể hiện phong cách hoặc engine có điều khiển style rõ ràng sau khi owner chọn hướng.
3. Chỉ sau nghiệm thu bản thử mới lập kế hoạch tích hợp, giữ phạm vi ba cảm xúc; sửa pipeline audio/mux và alignment ở đường preview/production chung. Không thay mặc định hay đóng gói lại ở lượt PoC này.

Nguồn kiểm tra Turbo: [generate implementation](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/tts_turbo.py), [token list](https://huggingface.co/ResembleAI/chatterbox-turbo/blob/main/added_tokens.json).
