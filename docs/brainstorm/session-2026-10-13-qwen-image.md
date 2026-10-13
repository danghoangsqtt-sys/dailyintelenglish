# Phiên brainstorm 2026-10-13 (b) — Mô hình tạo ảnh Qwen-Image cho ảnh minh họa hoạt động

## Thông tin phiên

- **Trạng thái:** Hoàn tất / khóa phạm vi 2026-10-13.
- **workflow_version:** vp-brainstorm 1.1.0 (fw 2.19.0)
- **Ngôn ngữ:** Tiếng Việt
- **Bối cảnh:** dự án đã đóng ở `v1.3.0` (Phase 37 chờ Gate B-25). Một người bạn gợi ý cho chủ dự án dùng Qwen-Image 2.1
  ("ảnh siêu chính xác, chạy local, tốc độ cao"). Chủ dự án muốn nghiên cứu và so sánh với mô hình local hiện tại.

## Yêu cầu của chủ dự án

Mô hình vẽ **ảnh minh họa đúng với nội dung lời thoại**, chủ thể chính là **một vài người bất kỳ**. **Không cần** các nhân vật
Alex, Jack hay Lina trong ảnh minh họa. (Ghi nhận thêm từ Gate B-23/B-24: "hơi ít hình minh họa".)

## Hiện trạng đã kiểm chứng (2026-10-13)

- Máy: RTX 3060 **12 GB VRAM**, RAM 32 GB; ổ D: còn 154 GB trống, ổ C: chỉ còn 17 GB (cache mô hình phải nằm ở
  `models/image/hub` trên D:).
- Engine ảnh: `venv-image` (diffusers 0.40, torch 2.11 + cu128), worker `scripts/image_worker.py`. Mô hình chính là
  **RealVisXL V5.0 (SDXL)**, cùng IP-Adapter, ControlNet openpose/depth, SDXL-Lightning và anime-seg (tổng 29 GB).
- Thông số hiện tại: 30 bước, CFG 6.0, ~1024²; đo được **~21–27 giây mỗi ảnh**.
- Ảnh minh họa hoạt động (Task 33.10, D102) do `pipelines.activity_illustrations` sinh ra: chỉ dùng **text2img thuần**
  (`ip="none"`), prompt từ `recipes.activity_illustration_prompt(action, place)`. Ảnh vào Activity Library ở trạng thái chờ
  duyệt, chủ dự án duyệt trong Step 5. Đây là điểm cắm engine thứ hai mà không đụng tới cảnh nền hay shot nhân vật.

## Nghiên cứu (2026-10-13)

| | RealVisXL V5.0 (hiện tại) | Qwen-Image-2.1 / 2.1-Turbo | Qwen-Image-2512 (+ Edit-2511) |
|---|---|---|---|
| Ra mắt | 2024 | 20/9/2026; Turbo 9/10/2026 | 12/2025 |
| Kích thước | ~3,5B | DiT 7B, bộ mã hóa Qwen3-VL 8B | 20B, bộ mã hóa Qwen2.5-VL 7B |
| Giấy phép | dùng thương mại được | **Qwen Research License: cấm dùng thương mại** nếu không có giấy phép riêng (§2b), chỉ cho phép nghiên cứu hoặc đánh giá | **Apache 2.0** |
| Trên 3060 (1024²) | ~21–27 giây (đo thật) | Turbo GGUF Q8: 34 giây khuếch tán, ~60 giây cả quy trình (bộ mã hóa chạy CPU); Q6_K vừa 12 GB (đỉnh 11,2 GB) | Nunchaku 4-bit + Lightning 4–8 bước: ~8–15 giây (cộng đồng tự báo) |
| Cách chạy | diffusers | diffusers bản dựng từ mã nguồn (`QwenImage21Pipeline`), stable-diffusion.cpp hoặc ComfyUI GGUF | diffusers (GGUF và LoRA Lightning) hoặc Nunchaku |
| Điểm mạnh | chân thực; đã nối IP-Adapter và ControlNet | chữ trong ảnh đẹp, ảnh gốc 2K, nhận tới 10 ảnh tham chiếu, RGBA | hiểu prompt nhiều chủ thể tốt, vẽ chữ tốt |

Kết luận nghiên cứu:
1. Qwen-Image-2.1 **không được dùng để sản xuất** cho kênh kiếm tiền khi chưa có giấy phép thương mại; chỉ được chạy để đánh giá.
2. Lời giới thiệu "tốc độ cao" đúng trên card 24 GB (4090 khoảng 7,5 giây mỗi ảnh). Trên 3060, bản 2.1-Turbo chậm hơn hiện tại khoảng 2–3 lần.
3. Ứng viên thay thế thực tế là **Qwen-Image-2512** (Apache 2.0). Mọi con số tốc độ đều do cộng đồng tự báo, nên phải đo thật trên máy.
4. Rủi ro tích hợp: Nunchaku cần bản build khớp torch 2.11/cu128 trên Windows; có thể phải dùng venv riêng. Bản GGUF chạy được trong diffusers nhưng chậm hơn.

Nguồn: [Qwen-Image-2.1 trên GitHub](https://github.com/QwenLM/Qwen-Image-2.1) và
[LICENSE](https://github.com/QwenLM/Qwen-Image-2.1/blob/main/LICENSE);
[Qwen-Image-2.1-Turbo GGUF (số đo trên 3060)](https://huggingface.co/DogukanUrker/Qwen-Image-2.1-Turbo-GGUF);
[Nunchaku Qwen-Image-2512](https://huggingface.co/QuantFunc/Nunchaku-Qwen-Image-2512);
[Qwen-Image GGUF + Lightning cho diffusers](https://huggingface.co/OzzyGT/qwen-image-lighting-gguf);
[Nunchaku trên RTX 3060](https://medium.com/coding-nexus/nunchaku-made-ai-image-editing-possible-on-mid-range-gpu-nvidia-rtx-3060-12gb-605589b5467c).

## Quyết định

- **D110 (chủ dự án):** mục tiêu là ảnh minh họa đúng nội dung lời thoại, chủ thể là vài người bất kỳ, **không** có
  Alex/Jack/Lina. Vì vậy không đưa Qwen-Image-Edit-2511 (giữ nhân vật từ ảnh tham chiếu) vào spike.
- **D111:** spike so sánh 3 engine: **RealVisXL V5.0** (mốc so sánh), **Qwen-Image-2512** (ứng viên sản xuất, Apache 2.0) và
  **Qwen-Image-2.1-Turbo** (**chỉ để đánh giá**, theo đúng giấy phép research/evaluation; không đưa vào sản xuất khi chưa có
  giấy phép thương mại).
- **D112:** nếu Qwen thắng, nó chỉ thay engine cho **ảnh minh họa hoạt động** (Task 33.10 / Activity Library / insert còn
  thiếu ảnh). RealVisXL giữ nguyên cho cảnh nền, shot nhân vật và thumbnail.
- **D113 (tiêu chí thắng):** chủ dự án chấm ảnh Qwen **đẹp hơn hoặc đúng nội dung hơn ở đa số mẫu**, **và** thời gian mỗi
  ảnh **không quá khoảng 30 giây** trên 3060 (gồm cả bộ mã hóa văn bản, đo khi mô hình đã nạp sẵn).
- **D114 (an toàn kỹ thuật):** mô hình Qwen chạy trong venv riêng nếu không tương thích với `venv-image`. Không đổi
  phiên bản torch/diffusers của `venv-image` khi chưa có Gate. Cache mô hình đặt trên ổ D:. Một GPU dùng chung qua bộ
  điều phối hiện có (không chạy song song với render hay RealVisXL).

## Phases

### Phase 39 — Qwen-Image cho ảnh minh họa hoạt động (D110–D114; đánh số lại 39 vì Phase 38 là tái cấu trúc thư mục)

- **38.1 Spike so sánh (bắt buộc làm trước):**
  - Bộ prompt: 12 prompt lấy từ các insert thật của storyboard (tập "Choosing the Menu", "The New Neighbor"…). Có cảnh 1 người,
    2–3 người, tay cầm đồ vật, ngoài trời/trong nhà, chữ trên biển hiệu.
  - Mỗi engine: cùng prompt, 2 seed, ảnh 1344×768 (khung 16:9 của video).
  - Đo: thời gian khi nạp sẵn và khi chạy lần đầu, VRAM đỉnh, RAM, dung lượng tải về.
  - Lỗi cần đếm: thừa ngón tay hoặc tay méo, người thừa, sai hành động, chữ sai.
  - Bảng ảnh **ẩn tên engine** để chủ dự án chấm.
  - Báo cáo: `docs/operations/phase38-spike-qwen-image.md`.
- **38.2 Tích hợp (chỉ khi spike đạt D113):**
  - Engine `qwen` cho `activity_illustrations`, với prompt viết riêng cho Qwen (ngôn ngữ tự nhiên, nhiều chủ thể).
  - Cài đặt chọn engine cho ảnh minh họa; nếu Qwen lỗi hoặc thiếu mô hình thì quay về RealVisXL.
  - Có test.
- **38.3 Gate B-26:** dùng một tập thật; chủ dự án duyệt ảnh minh họa mới trong Step 5 rồi xem video.

## Câu hỏi còn mở (mặc định)

- Nếu chủ dự án thích Qwen-Image-2.1 hơn hẳn: phải liên hệ `model-business@notice.qwencloud.com` để xin giấy phép thương mại.
  Mặc định là không dùng.
- Nunchaku trên Windows với torch 2.11: nếu không cài được, spike dùng bản GGUF + Lightning trong diffusers, rồi ghi lại tốc độ.

## Project meta intake (FEAT-009)

Bỏ qua (waiver): dự án một người, đã có `PROJECT-META.md`; `profile_id: none / not configured`. Không tạo agent stakeholder.

## Hành động tiếp theo

1. `/vp-evolve` thêm Phase 38 theo D110–D114.
2. `/vp-auto --phase 38`: chạy spike 38.1 trước, rồi dừng chờ chủ dự án chấm ảnh.

## Bổ sung (2026-10-13, sau phiên)

- **D116 (chủ dự án):** benchmark mở rộng cho 4 nhiệm vụ của hệ thống: ảnh minh họa hoạt động, ảnh nền cảnh, ảnh thumbnail/chủ đề, và shot có nhân vật. Riêng shot nhân vật dùng Qwen-Image-Edit-2511 để so với IP-Adapter của RealVisXL; D110 vẫn áp dụng cho ảnh minh họa. Được phép tải khoảng 72 GB. Chỉ áp dụng vào dự án sau khi so sánh xong (Phase 39).
- **D115:** tái cấu trúc thư mục dự án trước (Phase 38).
