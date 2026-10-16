# Chọn giọng nói cho nhân vật

> Tính năng trong mã nguồn Phase 48, hướng đến bản 1.5.0. Bản EXE thử 1.4.0-rc.1 chưa có bộ chọn này.

## Hồ sơ nhân vật

1. Mở **Character Library → Profiles**, chọn nhân vật.
2. Trong **Character voice**, lọc **Voice locale**, **Voice gender**, hoặc tìm tên/ID.
3. Chọn giọng và nhấn **Listen**. Có thể nhập một đoạn tiếng Anh riêng; giữ cùng đoạn và cùng thông số khi so sánh.
4. Chọn **Save voice** để lưu giọng mặc định của nhân vật. Các thông số mặc định speed/pitch/volume cũng nằm ở đây.

Danh sách lấy từ Edge TTS. Lần kiểm tra ngày 16/10/2026 có **47 giọng tiếng Anh**; số lượng phụ thuộc dịch vụ. Bộ chọn hiển thị toàn bộ danh sách khả dụng, có hơn 20 lựa chọn ở lần kiểm tra đó. Brian, Christopher, Roger và Ryan là bốn mẫu đã được chủ dự án nghe và đánh giá tốt; các giọng còn lại có thể nghe thử ngay trong app.

**Listen chỉ tạo mẫu nghe thử riêng.** Nó không thay lời thoại, audio tập phim hay video đã xuất. Thay giọng rồi chưa lưu thì vẫn chỉ là lựa chọn đang sửa; **Reload saved settings** lấy lại cài đặt đã lưu. Khi chuyển sang nhân vật khác, app hỏi trước khi bỏ lựa chọn chưa lưu.

## Giọng của một video

Hồ sơ cung cấp giọng cho lần chọn nhân vật tiếp theo. Video đã chọn nhân vật giữ giọng riêng của nó, kể cả khi hồ sơ được chỉnh sau đó.

Trong **Step 4 — TTS Audio Studio**:

1. Đọc **Project voice** trên thẻ nhân vật để biết giọng video đang dùng.
2. Mở **Choose / listen to English voices**, chọn giọng, nghe thử rồi **Save voice**.
3. Hoặc chọn **Apply profile voice** để lấy giọng hiện tại từ hồ sơ. Tốc độ, cao độ và âm lượng riêng của video được giữ lại.
4. Chọn **Generate All** để tạo lại lời bị ảnh hưởng và ghép audio. Sau đó tạo lại video ngang/video dọc hoặc duyệt và render lại Shorts nếu cần.

Speed/pitch/volume của video vẫn tự lưu. Chờ lưu xong trước khi đổi giọng hoặc tạo audio. Khi một lựa chọn giọng chưa được lưu, nút tạo toàn bộ audio bị khóa để tránh tạo bằng cấu hình cũ.

Hai nhân vật có thể dùng chung một giọng. App có thông báo và nút **Keep shared voices**; không bắt mỗi nhân vật phải khác nhau.

## Cache và các file đã xuất

Lời thoại chỉ được tái sử dụng khi giọng, nội dung và các thông số còn khớp. Đổi giọng một người làm mất hiệu lực cache của người đó; lời của người khác còn khớp được giữ lại. Mốc từ cho karaoke được tạo cùng lần tổng hợp mới.

Kết quả tạo trong lúc giọng/nội dung đã thay đổi sẽ không được công bố. File tốt trước đó được giữ lại; app yêu cầu tạo lại phần phụ thuộc. Sau khi tạo bản ngang mới từ nguồn đã thay đổi, bản dọc cũ không được coi là bản dọc hiện tại: hãy render bản dọc mới.

Các lần tạo dùng thư mục riêng để bảo vệ file trước đó. App chưa tự dọn lịch sử media này; xóa một project trong app sẽ dọn các thư mục dữ liệu của project theo cơ chế hiện có. Không tự xóa thư mục dữ liệu đang dùng.

## Khi có lỗi

| Hiển thị | Cách xử lý |
|---|---|
| Không tải được danh sách | Kiểm tra mạng và chọn **Refresh voices**. Nếu có bản lưu gần nhất, app hiển thị trạng thái danh sách cũ. |
| Giọng đã lưu không có trong danh sách | Refresh hoặc chọn một giọng còn khả dụng. App không âm thầm đọc bằng giọng khác. |
| Không nghe được mẫu | Kiểm tra mạng, thử lại; nếu trình duyệt chặn tự phát, nhấn nút phát trên thanh audio. |
| Settings changed elsewhere | Lựa chọn đang sửa được giữ. Dùng **Reload saved settings**, xem lại rồi lưu. |
| Wait until the voice finishes saving | Chờ yêu cầu lưu hoàn tất rồi chuyển hồ sơ. |
| Audio/video yêu cầu tạo lại | Lưu giọng trước, chạy **Generate All**, rồi render lại các phiên bản cần xuất. |

Edge TTS cần Internet để tải danh sách mới và tạo giọng. Tính năng này dùng engine Edge TTS hiện có; không thêm dịch vụ trả phí hoặc voice cloning.
