# Brainstorm — Khán giả quốc tế và Việt Nam: giải thích từ vựng bằng tiếng Anh, tiếng Việt hoặc song ngữ

## Session Info

- **Date:** 2026-10-22, Asia/Bangkok
- **Status:** Phạm vi đã chốt với owner; chờ `/vp-crystallize` hoặc `/vp-evolve` để lập Phase 72.
- **workflow_version:** 2.19.0
- **Skill:** vp-brainstorm 1.1.0
- **Language:** vi (theo owner)
- **Nguồn:** owner: "tôi quên mất vì khán giả của tôi là khán giả quốc tế và Việt Nam vì vậy ưu tiên nội dung giải thích từ vựng có thể giải thích bằng tiếng Anh như từ điển hoặc giải thích bằng tiếng Việt tùy người dùng lựa chọn thiết lập"

## 1. Hiện trạng (đã kiểm tra trong mã nguồn 1.6.0)

- **Dữ liệu đã song ngữ.** Mỗi mục học do AI tạo có cả hai ngôn ngữ: từ vựng có `definition_en` + `definition_vi`; thành ngữ và cụm từ có `meaning_en` + `meaning_vi`; mẫu câu có `use_en` + `use_vi`; ngữ pháp có `explanation_en` + `explanation_vi` (`backend/schemas/learning.py`). Vì vậy đổi cách hiển thị **không cần tạo lại** nội dung học.
- **Thẻ từ vựng trong video dài** (`renderer/src/Episode.tsx`) hiện cả EN lẫn VI, cố định.
- **Short học nhanh** (`renderer/src/LearnScene.tsx`: Từ của ngày, Top 5, Đừng nói / Hãy nói) chỉ hiện nghĩa **VI** kèm nhãn "VI" (`learnMath.learningFor` chỉ lấy `definitionVi` / `meaningVi`).
- **8 prompt AI** ngầm hiểu khán giả là "Vietnamese learners": `channel/channel_plan`, `learning/learning_pack`, `script/outline`, `script/script_base`, `shorts/clip_proposal`, `source/topic_ideas`, `thumbnail/thumbnail_suggestions`, `youtube/youtube_package`. Kế hoạch kênh có trường `audience` mặc định "Vietnamese learners of English" (`backend/schemas/channel.py`).
- **Không có cài đặt** nào cho ngôn ngữ giải thích. (Ngôn ngữ giao diện app EN/VI ở Phase 58 là chuyện khác: chỉ là chữ trên nút bấm.)

## 2. Quyết định đã chốt với owner (2026-10-22)

| # | Câu hỏi | Owner chọn |
|---|---|---|
| D1 | Kiểu giải thích | **3 lựa chọn:** Quốc tế (EN kiểu từ điển), Việt Nam (VI), Cả hai (song ngữ: EN trên, VI dưới) |
| D2 | Đặt ở đâu | **Mặc định cho kênh + đổi riêng theo từng series và từng video** |
| D3 | Áp dụng cho | **Chữ trên video và Shorts; mô tả YouTube; khán giả trong prompt AI** |
| D4 | Một hay hai thiết lập | **Một thiết lập "Khán giả"** quyết định tất cả: Quốc tế → EN; Việt Nam → VI; Cả hai → song ngữ |
| D5 | Giọng đọc | **Giữ như cũ, hoàn toàn tiếng Anh.** Owner: "Không cần giọng Việt vì đây là kênh học tiếng Anh chỉ cần giọng như cũ". Nghĩa tiếng Việt chỉ hiện bằng **chữ**. Không thêm giọng `vi-VN`, không đổi lời đọc |
| D6 | YouTube | **Tiêu đề luôn tiếng Anh; mô tả theo khán giả.** Quốc tế = EN; Việt Nam = phần giới thiệu và danh sách từ bằng VI; Cả hai = song ngữ |
| D7 | Mặc định của kênh | **Cả hai** |
| D8 | Chia việc | **Một phase (Phase 72)** |

### Bảng hành vi

| | Quốc tế | Việt Nam | Cả hai (mặc định) |
|---|---|---|---|
| Thẻ từ / Short học nhanh: chữ | Giải nghĩa EN kiểu từ điển (từ loại, IPA, định nghĩa, ví dụ) | Nghĩa VI (nhãn "VI") | Định nghĩa EN, nghĩa VI ở dưới |
| Giọng đọc | Như cũ, tiếng Anh | Như cũ, tiếng Anh | Như cũ, tiếng Anh |
| Video hội thoại dài | Thẻ từ theo dòng đầu bảng; lời thoại không đổi | như trên | như trên |
| Tiêu đề YouTube | EN | EN | EN |
| Mô tả YouTube | EN | Giới thiệu và danh sách từ bằng VI | Song ngữ |
| Prompt AI (kịch bản, ví dụ, chủ đề) | "international learners of English" | "Vietnamese learners of English" | "international and Vietnamese learners of English" |

## 3. Ý tưởng và lưu ý kỹ thuật (cho crystallize)

- **Lưu thiết lập:** kênh lưu trong `app_settings` (`audience`: `international` | `vietnamese` | `both`, mặc định `both`). Series có cột `audience` (NULL = theo kênh), cần migration. Project có cột `audience` (NULL = theo series, rồi theo kênh). Tập tạo từ series thì kế thừa. Thứ tự ưu tiên: video > series > kênh.
- **Giao diện:**
  - Cài đặt → Chung có "Khán giả của kênh".
  - Kế hoạch kênh: mỗi series có ô chọn Khán giả, mặc định "Theo kênh".
  - Bước 1 và Shorts hàng loạt có ô chọn Khán giả.
  - Trang Tự động dùng thiết lập của series.
- **Renderer:** props mới `audience`. Thẻ từ ở Episode và LearnScene vẽ theo bảng trên; `learnMath.learningFor` trả về cả `meaningEn`. Nhãn "VI" chỉ hiện ở chế độ Việt Nam và Cả hai. Cần chú ý độ dài chữ EN trong khung 9:16 (định nghĩa kiểu từ điển dài hơn nghĩa VI): có giới hạn độ dài trong prompt và vừa khung khi vẽ.
- **Prompt:** thêm biến `{{ audience_line }}` thay cho chữ "Vietnamese learners" viết cứng. Riêng `learning_pack` luôn sinh cả hai ngôn ngữ như hiện nay, để đổi khán giả không phải tạo lại. `youtube_package` nhận khán giả để viết mô tả.
- **Video đã làm:** đổi khán giả của một video đã dựng thì phải **dựng lại** mới thấy chữ mới. Nội dung học không cần tạo lại; mô tả YouTube cần tạo lại (hoặc có nút "Viết lại mô tả").
- **Không đổi:** giọng đọc và lời đọc (tiếng Anh như cũ); ngôn ngữ giao diện app (Phase 58); không xoá tính năng nào.

## 4. Câu hỏi còn mở (xác nhận khi lập kế hoạch)

- Shorts tin tức (news) và chữ trên nền blur có cần theo khán giả không, ví dụ một dòng tóm tắt tiếng Việt dưới tiêu đề tin ở chế độ Việt Nam và Cả hai?
- Quiz đếm ngược và Thử thách nghe: phần giải thích đáp án hiện bằng chữ theo khán giả (EN / VI / song ngữ)?
- Bình luận ghim và hashtag YouTube: theo mô tả (song ngữ khi chọn Cả hai)?

## Phases

### Phase 72 — Khán giả quốc tế / Việt Nam / Cả hai

- Thiết lập "Khán giả" ở kênh, series và video (migration, API, kế thừa).
- Giao diện: Cài đặt → Chung, Kế hoạch kênh (series), Bước 1, Shorts hàng loạt; Tự động dùng thiết lập của series.
- Renderer: thẻ từ video dài và Shorts học nhanh vẽ theo khán giả (EN kiểu từ điển, VI, song ngữ), vừa khung 9:16. Giọng đọc không đổi.
- Prompt AI: biến khán giả thay cho "Vietnamese learners" trong 8 prompt; mô tả YouTube theo khán giả, tiêu đề luôn EN.
- Test: kế thừa thiết lập, renderer (3 chế độ × 16:9 / 9:16), prompt, browser; dựng thật 3 Short mẫu (một cho mỗi chế độ).

## Project meta intake (FEAT-009)

- Bỏ qua: dự án đã có hồ sơ từ các phiên trước (persona full-stack, solo). Không đổi.

## Next steps

- `/vp-evolve` hoặc `/vp-crystallize`: lập Phase 72 (ENH-054) theo phạm vi ở trên; xác nhận 3 câu hỏi còn mở khi lập kế hoạch.
