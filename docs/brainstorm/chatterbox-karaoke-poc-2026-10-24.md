# PoC Chatterbox: 12 hồ sơ giọng và karaoke

Ngày thực hiện: bắt đầu 2026-10-23, hoàn tất bộ xuất 2026-10-24 (Asia/Bangkok). Owner yêu cầu “thử phương án này xem sao”, cho phép PoC thư viện giọng và alignment. Chưa chuyển engine trong app, đổi DB hoặc đóng gói bản cài.

**Phản hồi tiếp theo:** owner đánh giá 12 giọng khá tốt nhưng **không chấp nhận karaoke của video này**, báo chữ chạy trước lời sau biểu cảm. Hắng giọng và nhiều sắc thái nghe lỗi; phạm vi được thu gọn còn cười, thở dài, tức giận. Xem [điều tra và bộ thử R2](chatterbox-karaoke-r2-2026-10-24.md). Các kiểm tra kỹ thuật bên dưới không phải nghiệm thu sync bằng nghe.

## Phạm vi và tệp

- `data/tmp/chatterbox-karaoke-poc-20261023/`: script PoC, nguồn alignment, trọng số aligner, tham chiếu, conditioning profiles và diagnostics.
- Tái dùng model Chatterbox và môi trường CUDA biệt lập từ `data/tmp/english-tts-comparison-20261023/`; không tải lại model TTS hoặc cài thêm dependency vào app env.
- `data/exports/chatterbox-voices-karaoke-20261023/`: `LISTEN.html`, 48 MP3, 48 timing sidecars, 12 WAV tham chiếu, `12_VOICES.mp3`, `KARAOKE_DEMO.mp4`/MP3/WAV, manifest và verification report.
- ZIP cùng tên bên cạnh thư mục xuất. Chạy lại bằng các script trong thư mục tmp theo thứ tự setup_alignment → prepare_voices → generate_voices → align_samples → make_pack → Remotion CLI → verify_pack.

## Kết quả thư viện giọng

Đã mở rộng từ 4 lên **12 hồ sơ tham chiếu**, tạo lại **48 mẫu Chatterbox local**: 12 × câu thường/cười/thở dài/hắng giọng. Audio đầu ra đều tạo sau khi nạp hồ sơ từ đĩa, không chỉ dùng conditioning đang giữ từ bước enroll.

| Nhóm | Giọng tham chiếu |
|---|---|
| US nam | Brian, Guy, Andrew, Christopher |
| US nữ | Jenny, Aria, Emma, Michelle |
| UK nam | Ryan, Thomas |
| UK nữ | Sonia, Libby |

Đây là **8 US + 4 UK, 6 nam + 6 nữ**, khác mục tiêu sơ bộ ba chất giọng mỗi nhóm vì danh mục Edge live có ít giọng UK nam. Tên/accent là nhãn của nguồn tham chiếu, chưa phải kết luận Chatterbox giữ nguyên accent/identity hoặc tất cả 12 giọng đủ khác biệt theo nghe.

Nguồn: các đoạn trung tính sinh bằng Edge, dùng cùng reference text của audition trước; bốn mẫu cũ được tái dùng, tám mẫu mới được sinh thêm. Chưa thử Qwen VoiceDesign hoặc giọng nhập bằng mô tả trong PoC này.

`Conditionals.save/load` hoạt động với 12 hồ sơ. Tensor trước/sau lưu khớp tuyệt đối, và bước verification nạp lại cả 12 trong process mới. Đây là lưu đặc trưng tham chiếu, không phải fine-tuning. Không coi checksum khác nhau là bằng chứng giọng nghe khác nhau; owner nghe trên cùng một câu trong `12_VOICES.mp3`.

## Alignment: vấn đề phát hiện và hướng thử

Gói WhisperX hiện hành 3.8.6 yêu cầu Python <3.14, trong khi môi trường CUDA audition là Python 3.14. Không cài nguyên gói cùng stack ASR/diarization. PoC dùng riêng các module alignment/audio/utils/schema/log_utils từ nguồn WhisperX commit `5d3678b8535698a2826a5db9eb3e4105aef85dd9`, kèm LICENSE BSD-2-Clause và checksum. Đây không phải môi trường full WhisperX được hỗ trợ chính thức.

Model tiếng Anh `facebook/wav2vec2-base-960h`, revision `22aad52d435eb6dbaf354bdad9b0da84ce7d6156`, safetensors 377,607,901 bytes, model card Apache-2.0. Aligner chạy **CPU, 6 threads**, không dùng GPU đồng thời với TTS. Có cảnh báo checkpoint thiếu `masked_spec_embed`; đó là embedding dùng cho masking trong huấn luyện, model được đặt eval. Cần khóa lại stack Python/dependency được hỗ trợ khi triển khai sản phẩm.

Đối chiếu kịch bản đã biết với **MP3 cuối đã giải mã**; bỏ cue và dấu câu khỏi transcript âm học, giữ lại đúng spelling/punctuation cho hiển thị. Không chia đều thời lượng. Đặt `interpolate_method='ignore'` và yêu cầu mỗi từ có start/end/score trực tiếp. Có tổng **684 từ** trong 48 sidecar.

Phát hiện quan trọng: forced alignment thông thường có thể kéo từ qua tiếng cười. Mẫu Brian/laugh ban đầu gán “That's” từ **1.727 đến 3.393 giây**, khiến từ này bị tô trong phần cười. Việc đủ số từ và timeline tăng dần không đủ chứng nhận karaoke chính xác.

Đã thử adapter CTC có **trạng thái wildcard tại vị trí cue trong kịch bản**, cho phép hấp thụ âm phi ngôn ngữ. Đây là phần mở rộng PoC của dự án dựa trên recurrence WhisperX, không phải khả năng đã được bảo đảm của WhisperX nguyên bản. Không gán thời lượng cười cố định hoặc sửa tay vị trí từ.

Trên mẫu Brian đó, adapter dành khoảng không tô chữ **1.686–3.172 giây**, “That's” bắt đầu **3.172 giây**. `LISTEN.html` có checkbox đổi về timing WhisperX ban đầu trên cùng audio để đối chiếu. Khoảng này gồm âm cảm xúc và ngắt xung quanh, không phải annotation ranh giới tiếng cười chuẩn do người nghe xác nhận.

Giới hạn: wildcard có thể hấp thụ lời thừa/che sai đọc; forced alignment không thay thế kiểm tra phát âm/bỏ từ. Cần nghe/nhìn duyệt và bổ sung stress cases (nhiều cue, câu dài, cue sát từ, số/tên riêng, cue không thực sự được phát) trước khi production. Bảy từ trong bảy mẫu bị flag theo ngưỡng PoC score <0.5 hoặc thời lượng >0.7s; chủ yếu là từ ngắn “a”, “to”, “and”. Đây là ngưỡng cảnh báo chưa hiệu chỉnh, không phải bảy lỗi đã xác nhận.

## Video và timing

Video **32.2 giây**, hai nhân vật Brian/Jenny, mỗi người ba câu cười/thở dài/hắng giọng; render bằng composition `Episode` và `CaptionBand` hiện có, không sửa renderer. Props và public assets ở PoC/export riêng.

Mix dùng PCM WAV được ghép từ chính các MP3 đã align; cộng offset theo số frame âm thanh và khoảng ngắt 650ms, nên không phát sinh lệch từ một lần encode MP3 trung gian mới. Video H.264/AAC, 1280×720, 30fps. Font Montserrat không có trong public dir PoC, renderer dùng fallback font; caption dùng Arial như source hiện tại.

Số đo trên bộ câu ngắn, không phải benchmark cả tập:

- Median generate: **1.5645 giây/câu**, sau nạp model/hồ sơ.
- Median alignment CPU: **0.2295 giây/câu**, gồm alignment gốc và adapter cue nếu có, chưa gồm encode MP3/I/O.
- Model Chatterbox load: **6.639 giây**. Median kiểm tra+nạp conditioning: khoảng **0.016 giây**, chưa phải phép đo reload thuần vì gồm so tensor.
- Peak Torch allocated TTS: **2875 MiB**, không phải tổng GPU memory của process/driver.

## Nghiệm thu

Owner cần nghe duyệt độ khác biệt/nhất quán của giọng và nhìn độ khớp chữ, đặc biệt khoảng cảm xúc. Kết quả kiểm tra tự động chi tiết ở `verification.json`; không thay thế nghiệm thu bằng nghe.

Đã kiểm tra: 48 MP3 giải mã và không im lặng, checksum audio khớp, 684 mốc từ có thứ tự/nằm trong audio, không lộ cue trong phụ đề; 12 profile nạp được trong process mới. Browser thử đủ 12 lựa chọn × 4 tình huống, không có JavaScript error; tại cùng một thời điểm trong đoạn cười, bản cue-aware không tô từ nào, bản baseline tô sai “That's”. MP4 có H.264 1280×720 và AAC, giải mã toàn bộ thành công; container dài 32.277 giây do video/AAC framing. ZIP kiểm tra CRC qua, kích thước 12,935,964 bytes. Đã xem ba khung hình thực từ MP4: “ladder” sáng khi đến từ, không từ nào sáng giữa khoảng cười, “That's” sáng sau khoảng đó. Đây là kiểm tra hiển thị theo timing, chưa chứng minh sync cảm nhận chính xác đến từng mili giây.

Nếu bộ thử đạt, bước kế tiếp là crystallize tích hợp engine + thư viện giọng có version + aligner vào cùng đường preview/production, xác định runtime được hỗ trợ, migration theo lựa chọn và mẫu dài trước khi thay mặc định. Không đưa nguyên overlay Python 3.14 hoặc file conditioning tùy ý vào bản cài.

Nguồn: [Turbo snapshot](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/tts_turbo.py), [WhisperX source snapshot](https://github.com/m-bain/whisperX/tree/5d3678b8535698a2826a5db9eb3e4105aef85dd9), [English model](https://huggingface.co/facebook/wav2vec2-base-960h).
