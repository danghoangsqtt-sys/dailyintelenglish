# Brainstorm — Cấu trúc thư mục lưu project theo Topic / Series / Video

## Session Info

- **Date:** 2026-10-23, Asia/Bangkok
- **Status:** Crystallized and implemented; source verification complete, not packaged
- **workflow_version:** 2.19.0
- **Skill:** vp-brainstorm 1.1.0
- **Language:** vi
- **Participants:** Owner, Codex
- **Crystallized plan:** [.viepilot/phases/76-topic-project-folders/PLAN.md](../../.viepilot/phases/76-topic-project-folders/PLAN.md)

## 1. Mục tiêu

Khi người dùng chọn nơi lưu cho một Topic, ứng dụng tự tổ chức tệp theo cấu trúc phân cấp để nhiều series và video không bị trộn chung:

```text
<thư mục gốc>/<Topic>/<Series>/<Tên video>/<các tệp của project>
```

Ví dụ:

```text
D:\Videos\Daily Beyond English\Food & Cooking\The Dinner Party Challenge\Ep 02 - Shopping at the Market\
  video.mp4
  subtitles.srt
  thumbnail.png
  ...
```

## 2. Hiện trạng codebase

- Step 1 và Step 7 đang có cùng một panel chọn thư mục đầu ra (`frontend/static/js/project_folder.js`).
- Mỗi project lưu `output_dir` và danh sách loại tệp được xuất trong `project_exports`.
- Với project thuộc series, đường dẫn đã chọn hiện được hiểu là thư mục series; ứng dụng tự tạo thư mục `Ep NN - <episode title>` bên dưới. Project độc lập ghi thẳng vào đường dẫn đã chọn.
- Các loại tệp có thể đồng bộ gồm video ngang/dọc, phụ đề, thumbnail, metadata YouTube, Shorts, audio, script và learning pack. Chỉ các loại được tích chọn được sao chép; tệp mới/cập nhật được đồng bộ tự động.
- Channel Plan đã có dữ liệu phân cấp `channel_topics -> channel_series -> channel_episodes`; episode liên kết tới project. Đây là nguồn dữ liệu phù hợp cho tên thư mục thay vì suy ra tên Topic/Series từ nội dung tùy ý.
- Đường dẫn xuất không phải thư mục dữ liệu làm việc nội bộ của project (`data/projects/{uuid}/`).

## 3. Yêu cầu và hướng thiết kế

1. Người dùng chọn thư mục gốc để lưu Topic. Ứng dụng tự tổ chức nội dung theo `thư mục gốc / Topic / Series / Ep NN - Tên video`.
2. Nơi lưu gốc được quản lý ở cấp Topic để các project thuộc Topic đó dùng chung. Với series, tên Topic/Series/episode lấy từ Channel Plan; với video lẻ, tên Topic lấy từ nội dung project.
3. Video lẻ lưu theo `thư mục gốc / Topic / Tên video`, không tạo cấp Series giả.
4. Giữ số tập trong tên thư mục episode (ví dụ `Ep 02 - Shopping at the Market`) để phân biệt và tránh trùng tên.
5. Tên thư mục phải an toàn trên Windows, dễ đọc, xử lý ký tự cấm và giới hạn độ dài; bảo đảm tên trùng không khiến project ghi đè lên project khác.
6. Step 1/Step 7 hiển thị cấu trúc đích đã phân giải, cho phép mở thư mục video và thay đổi nơi lưu.
7. Chỉ đồng bộ các loại đầu ra đang được tích chọn (video, phụ đề, thumbnail, script và các loại hiện có). Tiếp tục tự cập nhật các tệp đó khi có phiên bản mới.
8. Các project đã có đường dẫn xuất tiếp tục dùng đường dẫn cũ cho đến khi người dùng đổi nơi lưu. Không tự di chuyển hay xóa các tệp đã có ở đích cũ.

## 4. Quyết định và câu trả lời owner

| # | Chủ đề | Trạng thái |
|---|---|---|
| D1 | Cấu trúc mong muốn | Owner yêu cầu phân cấp `Topic / Series / Tên video / các tệp liên quan` sau khi chọn nơi lưu Topic. |
| D2 | Tên nguồn cho các cấp | Với series, dùng Topic/Series/Tên video trong Channel Plan. Với video lẻ, dùng Topic từ nội dung project. |
| D3 | Video không thuộc Series | Owner chọn `Topic / Tên video`, bỏ cấp Series. Topic lấy từ project. |
| D4 | Project đã có đường dẫn xuất | Owner chọn giữ nguyên đường dẫn cũ; cấu trúc mới chỉ áp dụng sau khi người dùng đổi nơi lưu. Không tự di chuyển các tệp đã xuất. |
| D5 | Tên thư mục episode | Owner chọn giữ số tập trong tên thư mục, ví dụ `Ep 02 - Shopping at the Market`, để tránh trùng. |
| D6 | Phạm vi tệp | Owner chọn các đầu ra đang có trong checkbox; không thêm gói dữ liệu làm việc nội bộ vào phạm vi bản đầu. |

## 5. Câu hỏi còn mở

- Quy tắc dự phòng nếu tên Topic hoặc tên video trống sau khi chuẩn hóa cần xác nhận trong lúc thiết kế kỹ thuật.

## 6. Phạm vi triển khai dự kiến sau khi chốt

- Cấu hình nơi lưu gốc theo Topic và tương thích với project hiện có.
- Hàm phân giải `root / topic / series / video` (với quy tắc cho project không có series), chuẩn hóa tên và tránh trùng tên.
- Hiển thị trước đường dẫn đầu ra ở Step 1/Step 7; cập nhật thao tác chọn/mở/lưu để làm việc trên đúng cấp.
- Đồng bộ đầu ra được chọn vào thư mục video; giữ tệp tại đích cũ khi thay đổi cấu hình.
- Cập nhật kiểm thử phân cấp, tương thích dữ liệu cũ, tên không hợp lệ/trùng, topic không có series và các hook đồng bộ tự động.

## Phases

### Phase 1 — Lưu project theo phân cấp Topic / Series / Video

- Chọn và lưu thư mục gốc ở cấp Topic; các project cùng Topic phân giải về đúng nhánh thư mục.
- Phân giải cấu trúc cho Channel Plan và video lẻ; giữ tên episode có số tập.
- Cập nhật Step 1/Step 7 để xem trước và mở đúng thư mục đích.
- Đồng bộ đúng các đầu ra được tích chọn bằng cơ chế tự cập nhật hiện có.
- Giữ nguyên project cũ cho tới khi người dùng đổi thiết lập; không tự di chuyển hoặc xóa các tệp cũ.
- Chuẩn hóa tên thư mục Windows và bảo vệ khỏi ghi đè khi tên bị trùng.

## Architecture diagram applicability inputs

- **Project complexity**: moderate
- **Services/modules**: multiple — Channel Plan data, project export API/service, Step 1/Step 7 UI
- **Event-driven**: yes — existing output generation hooks trigger selected-file sync
- **Deployment shape**: local-only
- **User flow complexity**: multi-step
- **Integration surface**: low
- **Initial diagram hints**: optional
