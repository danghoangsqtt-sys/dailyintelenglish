# Solo Explainer — một người dẫn chính diện

Đây là chức năng trong mã nguồn Phase 49. Bản phát hành đang công bố vẫn là 1.4.0-rc.1; không suy ra EXE đã cài có chức năng mới chỉ vì mã nguồn đã được cập nhật. Target 1.5.0 và nghiệm thu V49 được theo dõi riêng.

Máy hiện tại đã được cập nhật bản thử Desktop ngày 2026-10-16, Build `468f9f7ce4b4`; kiểm tra tại **Settings**. Hồ sơ cũ đã có bộ chọn giọng và tab 21 ảnh. Nếu còn tab trình duyệt mở từ bản cũ, tải lại trang rồi mở hồ sơ trong **Character Library → Profiles**.

## Chuẩn bị 21 ảnh trong hồ sơ nhân vật

1. Mở **Character Library**, chọn hồ sơ Hoang hoặc tạo hồ sơ với mô tả ngoại hình và trang phục cụ thể.
2. Chọn tab **Presenter · 21 pictures**. Mỗi ô có tên hành động, ảnh tham chiếu cần đính kèm, vùng cần sửa, prompt riêng, nút Copy, ô nhập ảnh và nút duyệt.
3. Tạo `calm__closed.png` trước: nhân vật đứng chính diện, toàn thân, nhìn thẳng, hai tay nghỉ, miệng khép. Dùng prompt nguyên văn trong ô và ảnh nhận diện/trang phục nếu có. Xuất PNG 1280×1536, nền xanh phẳng theo prompt; không cắt tóc, bàn tay hay bàn chân.
4. Nhập ảnh vào đúng ô, kiểm tra rồi **Approve**. Sau đó tải đúng ảnh tham chiếu liên kết trong mỗi ô tiếp theo. Ảnh cử chỉ sửa từ ảnh đứng trung tính; khẩu hình mở sửa từ đúng cử chỉ miệng khép; chớp mắt sửa từ ảnh trung tính.
5. Lần lượt tạo talk, point-left, point-right, emphasize, count-1/2/3, think, wave; mỗi cử chỉ có một ảnh miệng khép và một ảnh miệng mở. Thêm calm mở miệng và blink để đủ 21 ảnh.
6. Chỉ sửa vùng được ghi: tay, miệng hoặc mí mắt. Giữ nguyên mặt, tóc, quần áo, tỷ lệ cơ thể, vị trí đầu/chân và kích thước canvas. Point-left/right tính theo phía trái/phải màn hình của người xem. Count phải đúng số ngón duỗi.
7. Có thể tải **Download prompt pack**, tạo ảnh bằng công cụ AI bên ngoài rồi nhập nhiều ảnh theo tên file chính xác. Mỗi kết quả vẫn cần kiểm tra và duyệt. Nếu thay ảnh gốc, các ảnh phụ thuộc có thể cần tạo và duyệt lại.

Không cần gửi ảnh lên nhà cung cấp AI từ Studio. Bạn tự chọn công cụ ngoài, đính kèm ảnh và tạo kết quả. Import chỉ kiểm tra kỹ thuật; người dùng cần kiểm tra khuôn mặt, trang phục, bàn tay và chất lượng ảnh. Bộ Conversation 29 ảnh được quản lý trong tab riêng.

## Giao diện video Solo (từ Phase 55)

Video Solo trông giống video hội thoại: người dẫn đứng **từ eo trở lên** trước một **cảnh nền thật** trong Scene Library; đoạn nào nói về một hoạt động quen thuộc (lái xe, nấu ăn, làm việc với laptop…) thì **ảnh hoạt động** trong Activity Library phủ kín khung phía sau người dẫn; thẻ chữ và sơ đồ nổi bán trong suốt ở phía bên kia. Khi **Propose plan**, AI chọn cảnh nền và ảnh hoạt động cho từng đoạn; ở Step 5 bạn đổi được **Scene behind the presenter** và loại hình **activity** cho mỗi đoạn. Ảnh hoạt động chỉ lấy từ ảnh dùng chung hoặc ảnh riêng của chính người dẫn đã được duyệt. Kế hoạch làm trước Phase 55 cần **Arrange layouts** lại rồi duyệt lại.

## Tạo và duyệt tập Solo

Chọn **Solo Explainer** ở Step 1, một người dẫn và cấu trúc **Why / How / List**. Chọn hồ sơ nhân vật, viết hoặc tạo kịch bản, kiểm tra kiến thức và tạo audio. Bạn có thể bắt đầu biên tập kế hoạch ở Step 5 trước khi có audio/ảnh, nhưng bố cục, preview đồng bộ và duyệt sản xuất cần đủ ảnh 21/21 và audio có thời gian từ thực.

Ở **Step 5 → Solo Explainer**:

- **Propose plan** tạo kế hoạch nháp theo kịch bản. Theo dõi tiến độ hoặc hủy bằng **Cancel proposal**. Job có lưu trạng thái; tải lại trang không tạo kế hoạch đã duyệt tự động.
- Mỗi đoạn dùng ảnh, sơ đồ hoặc thẻ chữ. Nhập ảnh dự án bằng ô Import illustration. Với ảnh, có thể kéo đánh dấu vùng quan trọng; ảnh chưa đánh dấu được giữ riêng, không đặt người dẫn đè lên.
- Kiểm tra nội dung, sửa ghi chú nguồn và đánh dấu đã kiểm tra kiến thức cho từng đoạn. Không dùng tick này để thay kiểm chứng nguồn.
- **Arrange layouts** đề xuất vị trí cho cả 16:9 và 9:16. Chọn tỷ lệ để sửa vị trí, chiều cao người dẫn và chuyển động. Trường đã sửa được khóa; bỏ khóa rõ ràng nếu muốn hệ thống đề xuất lại phần đó.
- Thay đổi được lưu tự động theo thứ tự. Khi báo xung đột phiên bản, bản đang nhập được giữ tại trang; xem lại trước khi chọn Reload vì Reload có thể bỏ thay đổi chưa lưu.
- **Refresh preview** mở Player sử dụng cùng SoloScene với renderer. Có thể tua, dừng và xem bố cục dọc riêng. Preview tập trung cửa sổ nội dung/audio; video sản xuất còn có phần chào/kết thương hiệu.
- **Approve reviewed plan** chỉ thành công khi nội dung đã kiểm tra, đủ ảnh/audio, cả hai bố cục hợp lệ và nguồn chưa thay đổi. Sau đó dùng nút dựng video thông thường. Sửa kịch bản, voice, ảnh hoặc bố cục cần duyệt lại; kết quả render đang chạy với nguồn cũ không được công bố làm kết quả hiện hành.

Ảnh dài/chữ nhiều có thể không đủ chỗ trong bố cục dọc. Rút ngắn tiêu đề/nút sơ đồ hoặc tách đoạn; hệ thống sẽ báo lỗi thay vì thu chữ quá nhỏ. Chuyển động là thay ảnh 2D, khẩu hình, chớp mắt và di chuyển có giới hạn, không phải hoạt hình xương 3D.

## Shorts, thumbnail, series và sao chép

Shorts dựng từ cửa sổ frame của cùng tập dọc và giữ thời gian từ thực của tập gốc. Hook nằm ở vùng đầu dành riêng; tiêu đề dài có thể được rút hiển thị. Thumbnail composed dùng một người dẫn chính diện; ngoài AI nhận liên kết đúng ảnh front làm tham chiếu.

Trong Channel, chọn mode Solo cho series, một nhân vật và cấu trúc. Mỗi episode tạo dự án riêng. **Copy settings** trên Dashboard tạo dự án nháp mới, giữ mode/voice/cast; không sao chép kịch bản, audio, video hoặc phê duyệt kế hoạch.

Export của tập Solo thêm `explainer/plan.json`, revision/mode và ảnh của bản được duyệt vào thư mục riêng của tập. Chức năng này không tự đăng YouTube hay phát hành phần mềm.

## Chạy từ mã nguồn

```powershell
npm --prefix renderer ci
npm --prefix renderer run build:preview
.venv\Scripts\python.exe -m uvicorn backend.main:app
```

Nếu báo thiếu preview bundle, chạy lại lệnh build trên. Không cần một máy chủ React/Vite riêng. Quy trình `scripts/build_exe.ps1` tự cài dependency theo lockfile, kiểm tra TypeScript, build widget rồi mới chạy PyInstaller.
