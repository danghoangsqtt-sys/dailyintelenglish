# Nghiên cứu bổ sung engine giọng và cảm xúc

- Ngày: 2026-10-23, Asia/Bangkok.
- Workflow: vp-brainstorm 1.1.0, framework 2.19.0.
- Trạng thái: nghiên cứu tài liệu và mã nguồn; chưa chốt thay engine mặc định.
- Session chính: [AI vocal cues](session-2026-10-23-tts-emotion.md).
- Phạm vi: ba repository owner cung cấp; không cài dependency, tải trọng số hoặc chạy code của chúng. Chưa có audio mới để owner nghiệm thu.

## Kết quả đề xuất

Đưa **VieNeu v3 Turbo** vào vòng nghe đối chiếu với OmniVoice. VieNeu có bằng chứng mã nguồn cho cả ba cue cần dùng; tiếng Anh, độ tự nhiên và độ ổn định vẫn phải kiểm chứng bằng audio của app. Tham khảo cách OmniVoice Studio tổ chức engine/giọng. SEA-G2P đi cùng VieNeu ở lớp phát âm, không thay thế engine tổng hợp. Giữ Edge là lựa chọn trong giai đoạn đánh giá. Đây là đề xuất nghiên cứu, chưa phải quyết định chuyển 80 speaker hiện có.

## Snapshot đã xem

| Dự án | Commit | Nội dung đọc |
|---|---|---|
| gmossy/omnivoice-studio | `766e2f7284a2f25d154a1fdbb14eb4e6a697222e` | README, LICENSE, pyproject, tts_backend.py, voice-design.md |
| pnnbao97/VieNeu-TTS | `04044e1b8f822f946bafb2c88b716459f4164152` | README, LICENSE, pyproject, v3turbo.py, prompt_v3_turbo.py, phonemize_text.py, voices_v3_turbo.json |
| pnnbao97/sea-g2p | `e825173f235d08ea19315b2b279fb11153b44cea` | README, LICENSE, pyproject |

File nguồn nghiên cứu nằm trong `data/tmp/tts-research-20261023/` để đọc lại, không nằm trong runtime app. Một số yêu cầu raw GitHub timeout; các file Studio còn thiếu đã đọc qua GitHub Contents API. Không thực thi file tải về.

## 1. OmniVoice Studio

Đây là ứng dụng studio bao quanh các engine. Adapter OmniVoice gọi model k2-fsa với text, ref_audio/ref_text, instruct, duration, steps và guidance; không có bằng chứng ở phần đã đọc rằng adapter đó tự nâng chất lượng tiếng cười của model.

Điểm đáng học: giao diện adapter chung, trạng thái engine, chọn giọng cho speaker, workflow voice cloning/design, và công cụ làm việc với audio/video. Backend dùng model manager tái sử dụng model thay vì nạp lại ở mỗi câu. README tự ghi active beta; sự có mặt của một adapter không chứng minh nó đã chạy đạt trên Windows/RTX 3060 trong ứng dụng này.

Giới hạn tích hợp: stack của Studio lớn hơn nhu cầu hiện tại. App hiện có worker riêng và khóa GPU dùng chung với Qwen; không thể mang cách giữ model thường trực vào mà bỏ qua tranh chấp VRAM. Nếu tối ưu tốc độ, cần thử worker theo job/tập, giữ khóa GPU suốt job và giải phóng khi kết thúc.

`LICENSE` và README hiện ghi **FSL-1.1-ALv2**, có điều khoản Competing Use và chuyển sang Apache sau hai năm. `pyproject.toml` vẫn ghi Apache-2.0: metadata không đồng nhất, cần lấy văn bản LICENSE cụ thể làm căn cứ đánh giá việc dùng lại code. Giấy phép ứng dụng Studio cũng không thay thế điều khoản của trọng số engine bên dưới. Đây là ghi nhận tài liệu, không kết luận pháp lý cho sản phẩm của owner.

Nguồn: [adapter](https://github.com/gmossy/omnivoice-studio/blob/766e2f7284a2f25d154a1fdbb14eb4e6a697222e/backend/services/tts_backend.py), [LICENSE](https://github.com/gmossy/omnivoice-studio/blob/766e2f7284a2f25d154a1fdbb14eb4e6a697222e/LICENSE), [README](https://github.com/gmossy/omnivoice-studio).

## 2. VieNeu-TTS v3 Turbo

### Bằng chứng kỹ thuật

- Snapshot SDK ghi version 3.8.3. Có backend ONNX/CPU và PyTorch/GPU; model mặc định là `pnnbao-ump/VieNeu-TTS-v3-Turbo`, subfolder PyTorch `update`, ONNX fp32 `onnx_update`. Cần khóa revision model/checkpoint khớp SDK khi làm PoC.
- Wrapper phonemization giữ cue thành token: cười/chuckle → emotion_1, thở dài/sigh → emotion_2, hắng giọng/clear throat → emotion_3. Các token đi vào prompt của model. Đây là cơ chế khác với yêu cầu Edge đọc chữ mô phỏng.
- v3turbo.py gọi wrapper này ở đường infer, streaming và batch. Tuy nhiên, có ánh xạ token chưa bảo đảm âm nghe đạt; README/model card đều đánh dấu cue là experimental.
- Bộ preset trong snapshot có **25 giọng**, mặc định Hải Đăng. Mỗi preset lưu speaker embedding và reference codes; SDK còn có cache enrollment cho tham chiếu. Có thể sử dụng giọng có sẵn hoặc lưu giọng từ clip ngắn. Không giả định mỗi preset có accent bản ngữ Anh.
- Tham số `style` hiện bị bỏ qua ở v3 Turbo: phong cách đọc theo giọng tham chiếu. Không nên thiết kế UI điều khiển cảm xúc bằng một slider style rồi kỳ vọng SDK thực thi.

### Những điều cần phân biệt

Model card hiện mô tả SDK 3.7.1 với 23 preset và default Minh Quân, khác snapshot source 3.8.3/25 preset. Danh sách thực tế phải lấy từ SDK/model đã khóa phiên bản. v4 là dịch vụ proprietary; nghiên cứu này không coi tính năng v4 hay các công cụ dubbing của app chính thức là tính năng có sẵn trong OSS v3 Turbo.

Dự án hỗ trợ tiếng Việt và Anh/Việt. Đối với video học tiếng Anh, cần nghe riêng độ rõ âm, accent, trọng âm, tốc độ B1 và tính nhất quán nhiều câu. Con số streaming/VRAM trên RTX 3060 được tác giả công bố chưa phải số đo trong workspace này. 48 kHz mô tả định dạng audio, không đủ để kết luận tự nhiên hơn OmniVoice.

### Giấy phép công bố

Repository và model card ghi Apache-2.0. Phần Usage Rights của model card xác nhận áp dụng cho weights, ONNX, tokenizer/config và các preset đi kèm; tác giả cho phép dùng audio preset trong nội dung thương mại/kiếm tiền. Điều này không bao phủ giọng tham chiếu bất kỳ do người dùng tự đưa vào. Codec MOSS-Audio-Tokenizer-Nano cũng có model card Apache-2.0.

Nguồn: [SDK](https://github.com/pnnbao97/VieNeu-TTS/blob/04044e1b8f822f946bafb2c88b716459f4164152/src/vieneu/v3turbo.py), [cue mapping](https://github.com/pnnbao97/VieNeu-TTS/blob/04044e1b8f822f946bafb2c88b716459f4164152/src/vieneu_utils/phonemize_text.py), [preset assets](https://github.com/pnnbao97/VieNeu-TTS/blob/04044e1b8f822f946bafb2c88b716459f4164152/src/vieneu/assets/voices_v3_turbo.json), [model card và Usage Rights](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo#-usage-rights--licensing-faq), [codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano).

## 3. SEA-G2P

SEA-G2P chuẩn hóa text và chuyển sang phoneme, có frontend Việt/Thái/Indonesia với English code-switching, dùng Rust core qua Python hoặc C ABI. Snapshot version 0.10.0; LICENSE Apache-2.0.

Nó không sinh WAV/MP3, không tạo giọng nhân vật hoặc tiếng cười. VieNeu đã phụ thuộc sea-g2p; lớp wrapper VieNeu giữ emotion token trước/sau phonemization. Không cần thêm một pipeline SEA-G2P trùng lặp vào app nếu sử dụng SDK VieNeu.

Đầu ra phoneme của SEA-G2P không được mặc định coi là đầu vào hợp lệ cho OmniVoice. Chỉ nối vào engine khi định dạng phoneme/tokenizer được hỗ trợ và đã kiểm chứng. Vì vậy công cụ này hữu ích cho phát âm Việt/Anh và chuẩn hóa số, không trực tiếp giải quyết vấn đề cảm xúc đang bị owner từ chối.

Nguồn: [README/API](https://github.com/pnnbao97/sea-g2p), [LICENSE](https://github.com/pnnbao97/sea-g2p/blob/e825173f235d08ea19315b2b279fb11153b44cea/LICENSE), [VieNeu wrapper](https://github.com/pnnbao97/VieNeu-TTS/blob/04044e1b8f822f946bafb2c88b716459f4164152/src/vieneu_utils/phonemize_text.py).

## Phases đề xuất để chốt phương án

### Phase 1 — Nghe đối chiếu và khóa lựa chọn

Ưu tiên thử VieNeu v3 Turbo cạnh OmniVoice trên hai nhân vật nam/nữ. Lấy hội thoại tiếng Anh làm tiêu chí chính; thêm một đoạn Việt/Anh ngắn nếu owner muốn hỗ trợ song ngữ. Mỗi engine dùng preset hoặc tham chiếu phù hợp; không tuyên bố chúng là cùng một giọng chỉ vì mô tả giống nhau.

Mẫu cần có câu thường, cười, thở dài; VieNeu thêm hắng giọng. Ghi rõ OmniVoice chưa có tag ahem được công bố. Chạy lại vài câu để đánh giá độ ổn định, rồi một đoạn hội thoại liên tục. Giữ tốc độ/loudness so sánh tương đương; lưu engine, SDK/model revision, tham chiếu, tham số, thời gian và VRAM. Mẫu phải đi đúng nhánh preview/production của app trước khi owner duyệt.

### Phase 2 — Tích hợp lựa chọn đã nghe đạt

Giữ UI hiện có; thêm profile giọng cố định gắn engine và phiên bản tài nguyên. Tái dùng preset/reference cho nhân vật qua nhiều tập, version hóa fingerprint cache. Mỗi speaker dùng một engine đã chọn; không đổi âm sắc giữa câu thường và câu có cue bằng cách chuyển engine tự động. Bộ sinh lỗi cần báo lỗi thực tế. Nếu cần karaoke, lập kế hoạch alignment theo audio thật; không giả định SDK mới cung cấp WordBoundary.

Worker và model nằm ngoài app venv. GPU phải dùng cùng cơ chế lease với Qwen; CPU/ONNX là nhánh đánh giá thêm cho Lite. Chỉ quyết định default và chuyển project cũ sau khi owner nghe đạt và chốt mục đích dùng. Bản 2.0 hiện tại chưa được sửa/cài lại trong nghiên cứu này.

## Những điểm còn chờ

- Owner có dùng video cho thương mại/kiếm tiền và có chấp nhận giọng mới hay không: câu hỏi từ lượt brainstorm trước vẫn chưa có trả lời.
- Chưa sinh audio VieNeu, chưa đo CPU/GPU, chưa thử ba cue trên app. Không có kết luận engine thắng về chất lượng.
- Mẫu OmniVoice được duyệt trước đây chỉ có hai audio nữ Mỹ, một có laughter và một câu thường; manifest không có đầy đủ seed/steps. Chưa có nghiệm thu sigh/ahem hoặc nhiều nhân vật từ mẫu đó.
