# Cài lên máy thứ hai (bản Full hoặc Lite) và đồng bộ thư viện

[← Về README](../../README.md) · [Hướng dẫn cài Windows đầy đủ](windows-installation.md)

**Applies to:** 2.0.0 local build (not publicly released) | Windows 10/11 x64 | updated 2026-10-23.

The Full and Lite 2.0.0 setup ZIPs are in `dist/2.0/`. Each contains the application folder and `SETUP.txt`; neither ZIP includes the project workspace/source, media library, or AI models. The matching workspace is required for video rendering. This local build has no GitHub release.
Package files: `DailyBeyondEnglishStudio-2.0.0-Full-windows-x64.zip`, `DailyBeyondEnglishStudio-2.0.0-Lite-windows-x64.zip`, and `SHA256SUMS.txt`.

| Tệp | Là gì |
|---|---|
| `DailyBeyondEnglishStudio-2.0.0-Lite-windows-x64.zip` | Ứng dụng bản **Lite**, cho máy không có GPU NVIDIA từ 8 GB (như laptop 4 GB VRAM) |
| `DailyBeyondEnglishStudio-2.0.0-Full-windows-x64.zip` | Ứng dụng bản **Full**, cho máy có GPU NVIDIA từ 8 GB và đã cài mô hình tạo ảnh |
| `SHA256SUMS.txt` | SHA-256 values for the Full and Lite ZIPs under `dist/2.0` |

Gói thư viện **không chứa khoá API** và **không chứa dự án**. Đừng đưa gói lên nơi công khai, vì trong đó có ảnh nhân vật của kênh.

## 1. Máy cấu hình thấp dùng được những gì

Máy thử là laptop có 24 GB RAM và GPU NVIDIA 4 GB VRAM.

| Chức năng | Trên máy đó |
|---|---|
| Toàn bộ giao diện, kế hoạch kênh, Shorts hàng loạt, tự động ban đêm | Chạy bình thường |
| AI viết kịch bản, bài học, nội dung YouTube | Chạy qua cloud (Gemini hoặc OpenRouter). Chọn **Cloud-first** trong Cài đặt → AI |
| Giọng đọc Edge TTS | Chạy qua Internet |
| Dựng video (Remotion) | Dùng CPU và RAM. 24 GB là đủ, chỉ chậm hơn máy chính |
| Tạo ảnh AI trên máy (Qwen) | **Không dùng**: 4 GB VRAM không đủ. Bản **Lite** ẩn hẳn 4 nút này: vẽ ảnh cảnh, vẽ ảnh hoạt động còn thiếu (Bước 5), ảnh chủ đề và thumbnail Cảnh AI (Bước 6). Ảnh có sẵn trong gói thư viện vẫn dùng bình thường |
| AI văn bản trên máy (Ollama) | Không khuyến nghị: chậm. Không cần cài |

## 2. Chuẩn bị một lần

Mở **PowerShell** (không cần quyền admin) và cài Node.js cùng FFmpeg:

```powershell
winget install OpenJS.NodeJS.LTS
winget install Gyan.FFmpeg
```

**Đóng PowerShell rồi mở lại** để nhận PATH mới, sau đó kiểm tra:

```powershell
node --version
ffmpeg -version
ffprobe -version
```

`node` phải là bản **24 trở lên**. Nếu không dùng được `winget`, tải Node.js LTS tại nodejs.org, còn FFmpeg tải bản Windows có cả `ffmpeg.exe` lẫn `ffprobe.exe` rồi thêm thư mục `bin` vào PATH.

## 3. Giải nén

1. Tạo thư mục `C:\Users\<tên-bạn>\Apps\DailyBeyondEnglishStudio`.
2. Extract the matching 2.0.0 project workspace here; it must contain `backend`, `frontend`, `renderer` and `scripts` at its root. The workspace is separate from the application ZIP.
3. Extract the matching Full or Lite ZIP into `data\tmp\desktop-download`; it creates `data\tmp\desktop-download\DailyIntelEnglishStudio\DailyIntelEnglishStudio.exe`.

## 4. Cài phần dựng video và ứng dụng

Mở PowerShell **tại thư mục gốc** `DailyBeyondEnglishStudio` rồi chạy lần lượt:

```powershell
cd renderer
npm ci
npx remotion browser ensure
npm run build:preview
cd ..
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_desktop.ps1 -StageDirectory .\data\tmp\desktop-download\DailyIntelEnglishStudio
```

Nếu PowerShell chặn `npm`, thay bằng `npm.cmd`. Lệnh cuối cài ứng dụng vào `dist\DailyIntelEnglishStudio` và tạo biểu tượng **Daily Beyond English Studio** trên Desktop.

## 5. Mở lần đầu và đưa thư viện vào

1. Bấm biểu tượng **Daily Beyond English Studio** trên Desktop. Giao diện mở tại `http://localhost:8000`.
2. **Cài đặt → Nhà cung cấp AI:** nhập khoá Gemini hoặc OpenRouter của bạn, bấm Lưu, rồi **Kiểm tra kết nối**.
3. **Cài đặt → AI:** chọn **Cloud-first**.
4. **Cài đặt → Dữ liệu & đồng bộ → Nhập một gói:** chọn `library-<ngày>.zip`, bấm **Nhập**. Gói khoảng 1,3 GB nên mất vài phút. Khi xong, trang hiện số mục đã thêm và đường dẫn bản sao lưu.
5. Mở **Thư viện nhân vật** để kiểm tra: phải thấy Lina, Alex, Jack, Hoang, Kim cùng ảnh và giọng của từng người.
6. **Cài đặt → Chung → Khán giả của kênh:** chọn Quốc tế (giải nghĩa tiếng Anh), Việt Nam (nghĩa tiếng Việt) hoặc Cả hai. Mỗi series trong Kế hoạch kênh và mỗi video ở Bước 1 có thể chọn riêng. Giọng đọc luôn là tiếng Anh.
7. **Cài đặt → Chung → Ảnh AI trên máy này** sẽ ghi "Bản Lite · Đang ẩn". Nếu sau này máy có GPU mạnh và đã cài mô hình tạo ảnh, chọn **Hiện**.
8. Làm thử một Short ngắn, ví dụ "Đừng nói / Hãy nói" ở trang **Shorts hàng loạt**, để kiểm tra dựng video trên máy này.

## 6. Đồng bộ giữa hai máy

Thư viện đồng bộ bằng **Gói thư viện**, theo hướng từ máy vừa sửa sang máy kia:

1. Trên máy có thay đổi (thêm hoặc sửa nhân vật, hoạt động, nhạc, kế hoạch kênh): **Cài đặt → Dữ liệu & đồng bộ → Xuất gói thư viện**. Tệp được lưu ở `data\exports\library-<thời gian>.zip`; có thể bấm tên tệp để tải.
2. Chép tệp sang máy kia qua USB hoặc Drive.
3. Trên máy kia: **Nhập một gói**.

Quy tắc khi nhập:

- **Gộp, không xoá.** Mục mới được thêm. Mục đã có chỉ được thay khi bản trong gói **mới hơn** (theo thời điểm sửa). Ảnh và tệp được chép khi máy này chưa có, hoặc khi bản trong gói mới hơn.
- **Xoá không được đồng bộ.** Nếu xoá một nhân vật ở máy A, hãy tự xoá ở máy B.
- **Tránh sửa cùng một nhân vật trên hai máy giữa hai lần đồng bộ**, vì bản sửa sau cùng sẽ thắng.
- Cơ sở dữ liệu được **sao lưu tự động** vào `data\backups\app-before-library-import-<thời gian>.db` trước mỗi lần nhập.
- Hãy chờ các tác vụ đang chạy (dựng video, tạo giọng) xong rồi mới nhập; app sẽ từ chối nhập khi còn tác vụ đang chạy.
- **Dự án và video không nằm trong gói.** Mỗi máy làm video riêng của mình. Tập trong kế hoạch kênh vẫn được đồng bộ, nhưng liên kết tới dự án chỉ giữ ở máy đã tạo dự án đó.

## 7. Cập nhật bản sau

Khi có bản mới:

1. Đóng hẳn ứng dụng (Task Manager → kết thúc `DailyIntelEnglishStudio.exe`) sau khi các tác vụ đã xong.
2. Giải nén mã nguồn mới đè lên thư mục gốc. Thư mục `data` giữ nguyên.
3. Giải nén gói ứng dụng mới vào `data\tmp\desktop-download`, rồi chạy lại các lệnh ở mục 4.

Trên máy không có Python riêng, script cài sẽ yêu cầu đóng app trước, rồi chép `data\app.db` sang `data\backups\desktop-<thời gian>\` trước khi thay ứng dụng.

## 8. Khi gặp sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Bấm biểu tượng không thấy giao diện | Mở `http://localhost:8000`. Xem `data\logs\desktop.log` |
| Không dựng được video | Kiểm tra `node`, `ffmpeg`, `ffprobe` (mục 2); chạy lại các lệnh `npm` ở mục 4 |
| Dựng video quá chậm hoặc lỗi đồ hoạ | Tạo tệp `.env` ở thư mục gốc với dòng `DIE_REMOTION_GL=auto`, rồi mở lại app. Dựng 9:16 ngắn trước |
| Không tạo được kịch bản | Kiểm tra khoá API, kết nối mạng và chế độ Cloud-first |
| Nhập gói báo "A job is running" | Chờ tác vụ xong, hoặc mở lại app, rồi nhập lại |
| Cần quay lại trước khi nhập | Đóng app, chép tệp `app-before-library-import-….db` trong `data\backups` đè lên `data\app.db` |
