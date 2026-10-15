<div align="center">

<img src="docs/assets/logo.png" width="112" alt="Daily Beyond English logo" />

# Daily Beyond English Studio

**Từ ý tưởng đến video hội thoại tiếng Anh — trong một studio.**

Lên kế hoạch series · Viết kịch bản · Tạo giọng đọc · Dựng video · Chuẩn bị nội dung đăng YouTube

[![Windows x64](https://img.shields.io/badge/Desktop-Windows_x64-0078D4?style=flat-square)](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v1.4.0-rc.1) [![Trial 1.4.0-rc.1](https://img.shields.io/badge/Trial-1.4.0--rc.1-D4A843?style=flat-square)](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v1.4.0-rc.1) [![License MIT](https://img.shields.io/badge/License-MIT-26875B?style=flat-square)](LICENSE)

**[Tải bản Windows](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/download/v1.4.0-rc.1/DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip)** · **[Hướng dẫn cài đặt](docs/user/windows-installation.md)** · **[Ghi chú phát hành](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v1.4.0-rc.1)**

</div>

---

## Một không gian làm việc cho cả tập video

Daily Beyond English Studio dành cho người sáng tạo nội dung học tiếng Anh. Ứng dụng kết nối kế hoạch kênh, nội dung học, âm thanh và hình ảnh trong cùng một dự án; bạn có thể xem lại và chỉnh sửa từng bước trước khi xuất bản.

Sau khi thiết lập lần đầu, mở bằng **icon logo trên Desktop**. Ứng dụng khởi động dịch vụ cục bộ và tự mở giao diện trong trình duyệt tại `http://localhost:8000`.

> **Trạng thái:** bản Windows **1.4.0-rc.1**, phát hành ngày **15/10/2026**, đang trong giai đoạn dùng thử. README này mô tả bản phát hành đó; khi cài đặt hãy dùng mã nguồn tại tag `v1.4.0-rc.1`.
>
> **Trước khi tải:** gói hiện tại là ZIP chứa ứng dụng và Python đi kèm, **chưa phải bộ Setup tự cài đầy đủ mọi phụ thuộc**. Máy mới cần thiết lập Node.js, renderer và FFmpeg một lần theo [hướng dẫn cài Windows](docs/user/windows-installation.md). Không cần cài Python riêng chỉ để mở EXE.

## Những gì bạn có thể làm

| Không gian | Khả năng |
|---|---|
| **Kế hoạch kênh** | Quản lý chủ đề, series, tập có số thứ tự, lịch nội dung và tiến độ sản xuất. |
| **Kịch bản & bài học** | Sinh và sửa hội thoại theo trình độ CEFR; chuẩn bị từ vựng, ngữ pháp, cụm từ và câu hỏi luyện tập. |
| **Âm thanh** | Phân giọng Edge TTS theo nhân vật, nghe thử từng câu, điều chỉnh giọng đọc, phối nhạc nền và giảm nhạc khi có lời thoại. |
| **Hình ảnh & nhân vật** | Thư viện cảnh, storyboard, hồ sơ nhân vật và bộ ảnh cử chỉ; nhập hình tạo từ bên ngoài hoặc cấu hình Qwen để tạo ảnh cục bộ. |
| **Video** | Xuất YouTube **16:9**, video dọc **9:16** và clip ngắn; phụ đề karaoke, nhấn từ, chuyển cảnh, intro/outro và chuyển động theo hội thoại. |
| **Thumbnail & nội dung đăng** | Thumbnail ngang/dọc, tiêu đề, mô tả, tags, chapters và bình luận ghim; xuất bộ tài nguyên để đăng thủ công. |
| **Thư mục dự án** | Đồng bộ tài nguyên đã chọn vào thư mục riêng theo **Episode**, tránh ghi chồng các tập trong cùng series. |

### Quy trình sản xuất

| Bước | Công việc | Kết quả |
|:---:|---|---|
| **1** | Chọn chủ đề, trình độ và nhân vật | Cấu hình tập |
| **2** | Tạo, đọc lại và sửa kịch bản | Hội thoại đã duyệt |
| **3** | Chuẩn bị nội dung học | Từ vựng, ngữ pháp, bài tập |
| **4** | Tạo giọng đọc và phối nhạc | Audio của tập |
| **5** | Duyệt storyboard, hình ảnh và dựng video | MP4 ngang/dọc, phụ đề |
| **6** | Chọn và chỉnh thumbnail | Ảnh bìa ngang/dọc |
| **7** | Chuẩn bị thông tin đăng và xuất tài nguyên | Bộ nội dung YouTube/Shorts |

## Tải xuống & cài trên máy khác

### Gói Windows hiện có

| Thành phần | Thông tin |
|---|---|
| Phiên bản | `v1.4.0-rc.1` — Windows x64, bản dùng thử |
| Gói tải | [`DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip`](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/download/v1.4.0-rc.1/DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip) |
| Dung lượng | Khoảng **140,5 MB** tải xuống / **320,8 MB** giải nén; chưa tính renderer, trình duyệt render, dữ liệu và model AI |
| Mã nguồn tương ứng | [Source ZIP tại tag `v1.4.0-rc.1`](https://github.com/danghoangsqtt-sys/dailyintelenglish/archive/refs/tags/v1.4.0-rc.1.zip) |
| Kiểm tra toàn vẹn | [Tệp SHA-256](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/download/v1.4.0-rc.1/DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip.sha256) |

**Giữ nguyên cả thư mục ứng dụng**, bao gồm `_internal` và `studio-runtime.json`. Chỉ chép một tệp `.exe` sang máy khác sẽ không đủ.

### Điều kiện sử dụng

| Nhu cầu | Cần chuẩn bị |
|---|---|
| **Mở ứng dụng** | Windows x64, thư mục có quyền ghi, trình duyệt web và thư mục mã nguồn đúng phiên bản để liên kết runtime. Windows 11 x64 là môi trường đã kiểm thử. |
| **Dựng/xuất video và xử lý audio** | **Node.js ≥ 24**, npm, phụ thuộc trong `renderer/`, Chrome Headless Shell của Remotion, **FFmpeg và ffprobe** trong PATH. |
| **Tạo kịch bản bằng AI cloud** | Internet và API key Gemini hoặc OpenRouter được cấu hình trong Settings. Khả năng sử dụng phụ thuộc tài khoản/model của nhà cung cấp. |
| **Tạo giọng đọc** | Internet để sử dụng Edge TTS. |
| **AI văn bản cục bộ — tùy chọn** | Ollama và model tương ứng; xem [hướng dẫn local AI](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/local-ai.md). |
| **Tạo ảnh Qwen cục bộ — tùy chọn** | GPU NVIDIA hỗ trợ CUDA, driver phù hợp, Python riêng cho `.venv-image`, PyTorch CUDA và đầy đủ model cache. Các thành phần này không nằm trong ZIP. |

**Máy tham chiếu đã kiểm thử:** Windows 11 Pro x64, RAM khoảng 32 GB, NVIDIA RTX 3060 12 GB. Đây là cấu hình tham chiếu, không phải mức tối thiểu đã được xác nhận. GPU NVIDIA không bắt buộc chỉ để mở ứng dụng hoặc dùng AI văn bản cloud; hiệu năng render tùy phần cứng.

### Thiết lập lần đầu

1. Cài Node.js ≥ 24 và FFmpeg/ffprobe.
2. Tải mã nguồn đúng tag và gói Windows ở trên; giải nén theo hướng dẫn.
3. Cài renderer bằng `npm ci`, chuẩn bị trình duyệt bằng `npx remotion browser ensure` trong thư mục `renderer`.
4. Chạy `scripts/install_desktop.ps1` với thư mục staging để cài ứng dụng và tạo icon logo.
5. Mở icon **Daily Beyond English Studio**, cấu hình AI trong Settings và thử một tập ngắn.

**[Xem đầy đủ lệnh PowerShell và cách kiểm tra cài đặt →](docs/user/windows-installation.md)**

## Tài nguyên xuất theo từng Episode

Với project đã liên kết tập trong series, Project Folder tự tạo thư mục tập. Ví dụ, khi chọn thư mục xuất `The Dinner Party Challenge`:

```text
The Dinner Party Challenge/
└── Ep 02 - Shopping at the Market/
    ├── video.mp4
    ├── video_vertical.mp4
    ├── subtitles.srt
    ├── thumbnail.png
    ├── thumbnail_9x16.png
    ├── audio.mp3
    ├── script.txt
    ├── learning_pack.txt
    ├── youtube/
    │   ├── metadata.txt
    │   └── pinned_comment.txt
    └── shorts/
        ├── clip-1.mp4
        ├── clip-1-cover.jpg
        └── clip-1.txt
```

Chỉ những thành phần **đã tạo và được chọn đồng bộ** mới xuất hiện. Project độc lập không gắn Episode sẽ sử dụng thư mục xuất đã chọn.

## Lưu ý của bản dùng thử

- **Chuyển động nhân vật** sử dụng bộ ảnh cử chỉ có sẵn, luân phiên theo cụm thoại và phản ứng người nghe; chưa phải hoạt họa khớp xương hoặc lip-sync thật.
- **Render** vẫn cần nhiều thời gian với video dọc và nhiều hiệu ứng. Bản Windows dùng ANGLE cho compositing; hai phép đo cùng đoạn 40 giây giảm thời gian khoảng 32–35% trên máy tham chiếu. Chưa có số đo đầy đủ cho một tập sau thay đổi này. [Báo cáo đo hiệu năng](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/render-performance-20261015.md).
- **Kết nối mạng:** ứng dụng lưu dự án cục bộ, nhưng Edge TTS và AI cloud cần Internet. Nội dung yêu cầu AI cloud được gửi đến nhà cung cấp đã cấu hình.
- **Model và tài nguyên cá nhân:** ZIP không chứa model Qwen/Ollama, dữ liệu dự án, API key hay thư viện hình/nhạc của người dùng.
- **Đóng tab trình duyệt** không dừng tiến trình ứng dụng đang chạy nền. Xem cách dừng và sao lưu trong hướng dẫn cài đặt.

## Công nghệ & phát triển

| Thành phần | Công nghệ |
|---|---|
| Ứng dụng cục bộ | Python, FastAPI, SQLite |
| Giao diện | HTML, CSS, JavaScript |
| Video | React, TypeScript, Remotion, FFmpeg |
| Giọng đọc | Edge TTS |
| AI văn bản | Gemini / OpenRouter; Ollama tùy chọn |
| AI ảnh tùy chọn | Qwen-Image qua worker Python riêng |
| Đóng gói Windows | PyInstaller, logo ứng dụng và Desktop shortcut |

<details>
<summary><strong>Chạy từ mã nguồn</strong></summary>

Dùng Python **3.14** của môi trường đã kiểm thử, Node.js ≥ 24 và FFmpeg/ffprobe. Các lệnh sau dành cho PowerShell, tại thư mục cha nơi bạn muốn tạo workspace mới:

```powershell
git clone --branch v1.4.0-rc.1 --depth 1 https://github.com/danghoangsqtt-sys/dailyintelenglish.git DailyBeyondEnglishStudio
Set-Location .\DailyBeyondEnglishStudio
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Push-Location renderer
npm ci
npx remotion browser ensure
Pop-Location
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`, cấu hình AI trong Settings. Nếu dùng EXE đã đóng gói thì bỏ qua việc tạo `.venv` backend; môi trường `.venv-image` cho AI ảnh là một thiết lập riêng.

Cấu trúc chính tại tag phát hành:

```text
backend/       API, dịch vụ nội dung/media, AI, database
frontend/      Giao diện studio
renderer/      Compositions và hiệu ứng Remotion
scripts/       Công cụ vận hành, build và cài Desktop
docs/          Tài liệu người dùng và kỹ thuật
data/          Dự án, media, log và cache cục bộ (không đưa lên Git)
```

Kiểm thử trước khi đóng gói `v1.4.0-rc.1`: **1.636 pytest**, **89 Vitest** đã qua; TypeScript và Ruff sạch. Đây là kết quả tại thời điểm phát hành, không phải trạng thái CI trực tiếp. [Biên bản build và smoke test](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/exe-trial-20261015.md).

</details>

## Tài liệu

| Dành cho | Tài liệu |
|---|---|
| Cài đặt trên máy Windows khác | [Hướng dẫn cài đặt & xử lý sự cố](docs/user/windows-installation.md) |
| Viết nội dung | [Prompt guide](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/user/prompt-guide.md) |
| Giọng đọc | [TTS setup](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/user/tts-setup.md) |
| AI văn bản local | [Ollama & cơ chế fallback](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/local-ai.md) |
| Kỹ thuật | [API reference](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/api.md) · [Architecture](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/.viepilot/ARCHITECTURE.md) |
| Lịch sử thay đổi | [Changelog của bản phát hành](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/CHANGELOG.md) |

## Giấy phép

Mã nguồn dự án được phát hành theo [MIT License](LICENSE). Model AI, dịch vụ và tài nguyên hình/nhạc sử dụng giấy phép hoặc điều khoản riêng của từng nguồn.

<div align="center">

**Daily Beyond English** · Create conversations. Build understanding.

<sub>Tên kỹ thuật của repository và tệp thực thi vẫn là <code>dailyintelenglish</code> / <code>DailyIntelEnglishStudio.exe</code>.</sub>

</div>
