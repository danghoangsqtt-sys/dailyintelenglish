# Nghiên cứu — Giọng Việt truyền cảm cho video học thuật (2026-11-03)

- **Yêu cầu (owner):** "có thể nghiên cứu tải thêm về VieNeu-TTS, sea-g2p, vieneu-audio-studio và OmniVoice để có giọng Việt Nam truyền cảm hơn".
- **Bối cảnh:** câu Q1 của [session-2026-11-03-academic-roots-grammar.md](session-2026-11-03-academic-roots-grammar.md). Hai template `roots` và `grammar` cần lời giảng tiếng Việt xen từ và câu tiếng Anh. Giọng Edge vi-VN (HoaiMy, NamMinh) đọc đúng nhưng đều đều.
- **Phạm vi:** chỉ nghiên cứu. Đã cài thử VieNeu trong một môi trường Python riêng ở thư mục tạm của phiên. **Không sửa app và không đổi venv của app.**
- **Liên quan:** [tts-engine-research-2026-10-23.md](tts-engine-research-2026-10-23.md) đã xét VieNeu, SEA-G2P và OmniVoice để thêm **cảm xúc cho giọng tiếng Anh**. Sau khi nghe Chatterbox, owner chọn quay về Edge (Phase 77) và Phase 75 OmniVoice bị gỡ. Lần này mục đích khác: **giọng Việt giảng bài**.

## 1. Bốn repo

| Repo | Là gì | Snapshot | Giấy phép | Kết luận |
|---|---|---|---|---|
| [pnnbao97/VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) | Engine TTS tiếng Việt chạy trên máy. Bản mở là **v3 Turbo** (48 kHz). Huấn luyện **10.000+ giờ song ngữ Việt–Anh**, đọc được câu trộn Việt–Anh. **25 giọng có sẵn** chia 3 miền, 10 giọng được chọn lọc; có clone giọng 3–8 giây, cue `[cười]` `[thở dài]` `[hắng giọng]`, API kiểu OpenAI, LoRA fine-tune. CPU (ONNX, không cần torch) RTF ≈ 0,5; GPU RTX 3060 RTF ≈ 0,02. Bản v4 đóng, chỉ có qua API trả phí. | commit `04044e1`, model HF `61b85e3` | Code và model đều Apache-2.0 | **Ứng viên chính** |
| [pnnbao97/sea-g2p](https://github.com/pnnbao97/sea-g2p) | Bộ chuyển chữ → âm vị (Rust) cho tiếng Việt/Thái/Indo, có xử lý trộn tiếng Anh và chuẩn hoá số, email, đơn vị. | `e825173` | Apache-2.0 | Không phải engine tạo giọng. Đi kèm VieNeu như một phụ thuộc, **không cần tích hợp riêng** |
| [sonlovinbot-team/vieneu-audio-studio](https://github.com/sonlovinbot-team/vieneu-audio-studio) | App "AI Audio Studio" (giao diện web cục bộ cổng 8001) bọc VieNeu: kho 25 giọng có nghe thử, clone giọng có nhãn cảm xúc, hội thoại nhiều giọng, API/MCP. 4 sao, cài bằng `irm … \| iex`. | `c656875` | Apache-2.0 | **Chỉ tham khảo giao diện và cách tổ chức giọng.** Không cài vào app: trùng chức năng với SDK, cài kiểu chạy script từ mạng và tự chạy khi mở máy |
| [danghoangsqtt-sys/OmniVoice](https://github.com/danghoangsqtt-sys/OmniVoice) | **Bản fork** của [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), chưa có thay đổi riêng (commit cuối là của upstream, 2026-05-06). OmniVoice hỗ trợ 600+ ngôn ngữ, **có tiếng Việt (≈ 8.482 giờ dữ liệu)**, clone giọng và voice design. Cần PyTorch + GPU. | `d8b22ae` | Apache-2.0 | Dự phòng. App đã từng tích hợp (Phase 75) rồi gỡ (Phase 77). Tiếng Việt không phải ngôn ngữ chính của model |

## 2. Thử thật VieNeu v3 Turbo

**Cách thử:**
- Môi trường `uv` Python 3.12 riêng, chỉ dùng CPU (ONNX), cài `vieneu==3.8.3`.
- Model `pnnbao-ump/VieNeu-TTS-v3-Turbo` (495 MB, trong bộ nhớ đệm HF).
- 5 giọng chọn lọc × 3 câu mẫu của template học thuật. So với Edge `vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`, `en-US-AvaMultilingualNeural`.
- Chép lại lời bằng faster-whisper `small` để phát hiện chữ bị bỏ hoặc đọc sai. Lưu ý: Whisper chạy ở chế độ tiếng Việt nên chép từ tiếng Anh không hoàn hảo; dùng để so sánh, không phải để chấm điểm tuyệt đối.

**File nghe thử:** `D:\Videos\Nghe thu giong Viet 2026-11-03\` (30 file mp3, tên dạng `{câu}_{engine}-{giọng}.mp3`).

| Điều đo được | VieNeu v3 Turbo | Edge vi-VN (HoaiMy / NamMinh) | Edge Ava Multilingual |
|---|---|---|---|
| Tốc độ dựng (CPU) | 2,3–4,9 giây cho câu 6–11 giây (RTF ≈ 0,45) | qua mạng, nhanh | qua mạng, nhanh |
| Độ dài câu "compress" | 7,8–9,4 giây (đọc nhanh, gọn) | 12,2–13,1 giây | 10,1 giây |
| Bỏ sót chữ | **Không** ở cả 15 file | Không | Không |
| Câu tiếng Anh trong câu Việt | *"We compress the files to save space"* chép ra **đúng ở 5/5 giọng** | **Đọc hỏng** ("Quy cùng pt philet tosay spacer") | Đúng |
| Từ VIẾT HOA (PRESS, EXPRESS, COM) | **Đánh vần từng chữ cái** ("EX-Phaser-ESS") | Cũng đánh vần | Lẫn lộn |
| Cùng câu, viết chữ thường | *express*, *impress*, *press* **đọc đúng** | (không thử) | (không thử) |
| Giọng | 25 giọng 3 miền, có giọng "kể chuyện", "tin tức", "đọc truyện" | 2 giọng | 1 giọng, chất Mỹ |
| Ổn định | Lấy mẫu ngẫu nhiên (temperature 0,4): hai lần chạy cùng câu có thể khác nhau (một lần "bảy" thành "bày") | Ổn định | Ổn định |
| Mốc thời gian từng từ (karaoke) | **Không có.** Cần căn chỉnh sau khi dựng | Có (WordBoundary) | Có |
| Watermark | Chỉ khi cài thêm `resemble-perth`; bản thử không có | — | — |
| Giấy phép | Apache-2.0 (code + model) | dịch vụ Microsoft | dịch vụ Microsoft |

Đánh giá "truyền cảm" là việc **owner phải nghe**. Số liệu trên chỉ cho biết độ đúng chữ và tốc độ.

## 3. Đề xuất

1. **VieNeu v3 Turbo** là ứng viên giọng Việt cho riêng hai template học thuật (`roots`, `grammar`). Edge vẫn là mặc định cho mọi thứ khác (Phase 77). Lý do:
   - Được huấn luyện song ngữ, **một giọng đọc được cả câu trộn Việt–Anh**.
   - Câu ví dụ tiếng Anh đọc đúng, trong khi giọng Edge Việt đọc hỏng.
   - Nếu owner thấy tiếng Anh của VieNeu đạt, có thể bỏ việc ghép hai giọng (phương án A ở Q1). Nếu chưa đạt thì giữ phương án A: VieNeu giảng tiếng Việt, giọng Edge tiếng Anh của kênh đọc câu ví dụ.
2. **Quy tắc kịch bản cho TTS:** từ tiếng Anh viết HOA chỉ để hiển thị trên hình. Văn bản đưa vào TTS phải là chữ thường (`PRESS` → `press`), nếu không engine sẽ đánh vần.
3. **Cách tích hợp (khi owner duyệt):**
   - Worker VieNeu chạy trong **venv riêng ngoài venv app**, gọi qua tiến trình con. Đây là mẫu cô lập của Phase 75, nhưng chỉ cho giọng Việt.
   - Chạy CPU là đủ nhanh. GPU dùng chung khoá với Qwen nếu bật.
   - Cố định giọng preset cho từng series. Đặt temperature thấp hoặc seed cố định để ổn định. Tự chép lại lời để kiểm tra, câu nào sai thì dựng lại.
   - **Karaoke:** thêm bước căn mốc thời gian từng từ (faster-whisper word timestamps hoặc forced alignment) vì VieNeu không trả WordBoundary.
4. **Không dùng:**
   - **vieneu-audio-studio:** app riêng, cài bằng script từ mạng, trùng chức năng với SDK. Chỉ tham khảo cách bày kho giọng và nghe thử.
   - **SEA-G2P:** đã nằm sẵn trong VieNeu.
   - **OmniVoice (fork):** giống upstream. Chỉ thử lại nếu VieNeu không đạt. Cần cài PyTorch GPU (khoảng vài GB) và từng bị gỡ ở Phase 77.
5. **Việc owner cần làm:** nghe thư mục mẫu, chọn 1–2 giọng (gợi ý nghe trước: Thiện Minh "kể chuyện", Ngọc Huyền "tự nhiên", Mai Anh "tin tức"), và quyết định một giọng đọc cả câu hay ghép hai giọng.

## 4. Dấu vết

- Môi trường thử (có thể xoá): `…\scratchpad\vieneu-venv` (752 MB, kèm faster-whisper). Model: `~/.cache/huggingface/hub/models--pnnbao-ump--VieNeu-TTS-v3-Turbo` (495 MB).
- Script: `…\scratchpad\scripts\vieneu_samples.py`, `vieneu_lower.py`, `transcribe.py` (thư mục tạm của phiên 137adefd).
- App, `.venv` của app và cơ sở dữ liệu **không bị thay đổi**.
