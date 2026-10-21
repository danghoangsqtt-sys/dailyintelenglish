# Brainstorm — Tạo nội dung tự động và Shorts viral (tin tức tiếng Anh, chữ trên nền blur, các dạng viral)

## Session Info

- **Date:** 2026-10-22, Asia/Bangkok
- **Status:** Phạm vi đã chốt với owner; chờ `/vp-crystallize` hoặc `/vp-evolve` để lập Phase 62 (Tạo nội dung tự động), rồi Phase 63+ (Shorts viral).
- **workflow_version:** 2.19.0
- **Skill:** vp-brainstorm 1.1.0
- **Language:** vi (theo owner)
- **Nguồn:** tin nhắn owner sau Phase 61: "thôi không cần làm video hoạt hình nữa như hiện tại là được rồi. Làm thêm các dạng video như tin tức tiếng Anh ảnh thay đổi liên tục và có nội dung chữ trên nền màu trơn blur, hay nhiều dạng video viral hiện nay được không?"

## 1. Bối cảnh

- Hướng video hoạt hình (truyện tranh động, AI tạo video Wan/FramePack/Veo) **đã bỏ** theo owner; không tải model nào.
- Ba loại video hiện có giữ nguyên: Hội thoại, Thuyết minh (Solo), VOX. Không xóa tính năng cũ.
- Nền tảng tái dùng: Remotion (9:16 safe zone đã có), TTS giọng nhân vật, phụ đề karaoke, Scene/Activity Library, ảnh AI (Qwen trên máy / Gemini), "Use my picture" + prompt AI ngoài (Phase 59), chuyển cảnh/hiệu ứng VOX (Phase 61).

## 2. Quyết định đã chốt với owner (2026-10-22)

| # | Câu hỏi | Owner chọn |
|---|---|---|
| D1 | Nhóm dạng video | **Cả 4**: A Tin tức tiếng Anh · B Chữ trên nền blur · C Shorts học nhanh · D Tương tác |
| D2 | Khung hình | **Chủ yếu Shorts 9:16** (15–60 s) |
| D3 | Nguồn tin tức | **Cả 3**: dán bài báo/link · AI gợi ý tin mới · chỉ nhập chủ đề |
| D4 | Vị trí trên Step 1 | **Một thẻ thứ 4 "Shorts viral"** + chọn mẫu bên trong |
| D5 | Sản xuất | **Từng video + lô nhiều video** (1 chủ đề → 5–10 Shorts) |
| D6 | Nguồn ảnh | Thư viện có sẵn · Ảnh AI (Qwen/Gemini) · Ảnh của tôi + prompt AI ngoài · (Pexels/Unsplash: owner chọn **chưa cần**) |
| D7 | Giọng đọc | **Giọng nhân vật có sẵn**; Chat / Would you rather dùng 2 giọng |
| D8 | Thứ tự giai đoạn | **Đồng ý** thứ tự ở mục 4 |

## 2b. Tạo nội dung tự động (owner 2026-10-22)

Owner: "thêm tính năng TẠO NỘI DUNG TỰ ĐỘNG người dùng sẽ treo máy và bật ứng dụng tự động tạo theo lịch hẹn và kế hoạch đã xác định trước"

| # | Câu hỏi | Owner chọn |
|---|---|---|
| A1 | Máy tự làm tới đâu | **Làm hết, chờ tôi duyệt**: kịch bản → giọng/âm thanh → kế hoạch hình (Solo/VOX tự duyệt khi không có lỗi) → render → gói YouTube (tiêu đề, mô tả, thumbnail). Tập có lỗi hoặc cảnh báo số liệu/sự thật thì **dừng ở bước đó và báo**, không tự bỏ qua |
| A2 | Tự đăng YouTube | **Không** — video và gói YouTube sẵn sàng, owner tự đăng |
| A3 | Lịch chạy | **Khung giờ đêm + làm trước N ngày** (vd 23:00–06:00, các tập có ngày đăng trong N ngày tới); giữ máy không ngủ trong khung giờ |
| A4 | Tự khởi động | **App tự mở cùng Windows** (đăng nhập Windows) và chờ tới khung giờ; owner để máy mở |
| A5 | AI khi chạy đêm | **Theo Cài đặt** (cloud hoặc local) + **giới hạn N video mỗi đêm**; cloud lỗi thì thử local |
| A6 | Nguồn kế hoạch | **Channel plan** (tập có ngày đăng) + **Lịch Shorts định kỳ** (vd mỗi ngày 1 Tin tức + 1 Từ vựng — khi các mẫu Shorts có) |
| A7 | Báo kết quả | **Báo cáo trong app** (đã làm gì, cái nào chờ duyệt, cái nào lỗi và vì sao) + thông báo Windows |
| A8 | Ưu tiên | **Tự động trước** Shorts viral |

Spec sơ bộ:
- Trang mới "Tự động" (Automation): bật/tắt, khung giờ, N ngày làm trước, giới hạn/đêm, loại video mặc định cho tập chưa có, giọng/nhân vật mặc định; nút "Chạy thử ngay".
- Hàng chờ có trạng thái từng tập: chờ → đang làm (bước nào) → chờ duyệt / lỗi (lý do + nút làm tiếp từ bước lỗi); không làm lại bước đã xong.
- Chạy tuần tự từng tập, dùng lại các job hiện có (AI job, audio, explainer approve, video render, YouTube package); khi owner mở app làm việc tay thì bộ chạy tạm nhường.
- An toàn: không xóa/ghi đè dự án owner đã sửa tay; sao lưu DB trước mỗi đêm chạy; dừng khi ổ đĩa còn ít dung lượng.
- Tự mở cùng Windows: shortcut trong Startup của người dùng (bật/tắt trong app); giữ máy thức trong khung giờ (SetThreadExecutionState).

## 3. Mô tả các mẫu Shorts (spec sơ bộ)

### A. Tin tức tiếng Anh (9:16)
- Nguồn: dán bài báo hoặc link (AI tóm tắt và **viết lại bằng lời mình**, không chép nguyên văn, ghi "Source: …"), chủ đề tự do, hoặc AI gợi ý tin mới (Phase 4).
- Viết lại theo CEFR của dự án; 3–6 ý, mỗi ý 1 ảnh; mở đầu bằng câu móc (hook) 2–3 giây.
- Hình: ảnh đổi mỗi 3–5 s với zoom/lia (Ken Burns) và chuyển cảnh Phase 61; dải tiêu đề "BREAKING / ENGLISH NEWS" (lower-third), dòng chữ chạy, từ vựng khó bật lên kèm nghĩa tiếng Việt; phụ đề karaoke.
- Không dùng ảnh chụp lại từ báo (bản quyền): ảnh lấy từ thư viện, ảnh AI hoặc ảnh owner.

### B. Chữ trên nền blur (9:16)
- Nền: ảnh làm mờ mạnh hoặc màu trơn/gradient chuyển nhẹ theo thương hiệu (xanh lá + vàng).
- Chữ lớn ở giữa hiện theo từng từ khớp giọng đọc (chữ nảy Phase 61); từ khóa tô vàng.
- Nội dung: câu chuyện ngắn, câu nói hay, "a day in the life", kể chuyện kiểu story-time.

### C. Shorts học nhanh (Phase 2)
- ❌ Đừng nói … ✅ Hãy nói … (2–4 cặp, có giải thích ngắn).
- Từ vựng của ngày: từ, IPA, nghĩa VI, ví dụ, ảnh.
- Top 5 cụm từ người bản xứ dùng, số đếm ngược.

### D. Tương tác (Phase 3)
- Quiz với đồng hồ 3‑2‑1 rồi hiện đáp án.
- Would you rather (2 lựa chọn, 2 giọng).
- Chat giả lập: bong bóng tin nhắn giao diện chung (không giả iMessage/thương hiệu), mỗi nhân vật một giọng.
- Thử thách nghe: nghe → đoán → hiện phụ đề.

## 4. Phases

| Phase | Nội dung |
|---|---|
| **Phase 1** (→ Phase 62) | **Tạo nội dung tự động**: trang Automation, bộ chạy nền theo khung giờ đêm cho các tập Channel plan (Hội thoại/Thuyết minh/VOX), làm hết tới "chờ duyệt", giới hạn/đêm, báo cáo + thông báo Windows, tự mở cùng Windows, giữ máy thức |
| **Phase 2** (→ Phase 63) | Thẻ thứ 4 "Shorts viral" + khung Shorts 9:16; mẫu **Tin tức tiếng Anh** (dán bài/link, chủ đề) và **Chữ trên nền blur**; nguồn ảnh: thư viện, ảnh AI, ảnh của tôi + prompt; Shorts vào được lịch tự động định kỳ |
| **Phase 3** | Shorts học nhanh: Đừng nói/Hãy nói, Từ vựng của ngày, Top 5 cụm từ |
| **Phase 4** | Tương tác: Quiz đếm ngược, Would you rather, Chat giả lập, Thử thách nghe |
| **Phase 5** | Làm hàng loạt (1 chủ đề → 5–10 Shorts); AI gợi ý tin mới trong ngày (AI có tìm kiếm web) |
| Sau | Pexels/Unsplash (khi có API key); tự đăng YouTube (owner chọn không); Telegram/email (owner chọn không); cắt Shorts từ video dài |

## 5. Rủi ro

- Chạy đêm không người: lỗi AI/giọng/render phải dừng an toàn từng tập, không làm hỏng dự án; chi phí cloud bị chặn bởi giới hạn/đêm.
- Máy ngủ/Windows Update khởi động lại: app tự mở lại khi đăng nhập, tiếp tục từ bước dở.
- Bản quyền tin tức: chỉ tóm tắt/viết lại, ghi nguồn; không dùng ảnh/đoạn văn gốc của báo.
- Tin "mới trong ngày" cần AI có truy cập web; nếu provider không có thì chỉ dùng dán bài/chủ đề.
- Chat giả lập không được giống giao diện ứng dụng thương hiệu thật.
- Video ngắn cần hook mạnh trong 2–3 giây đầu: prompt phải bắt buộc câu mở đầu.

## 6. Câu hỏi còn mở (không chặn Phase 1)

- Độ dài mặc định từng mẫu (đề xuất: Tin tức 45–60 s, Nền blur 20–40 s).
- Có chèn lời chào/đăng ký (Phase 60) vào Shorts không, hay chỉ CTA ngắn cuối video.
- Nhạc nền mặc định cho từng mẫu.

## Project meta intake (FEAT-009)

Binding đã có từ các phiên trước (dự án đang hoạt động, Phase 1–61); không chạy lại intake.
