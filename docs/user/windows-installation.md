# Cài Daily Beyond English Studio trên Windows

[← Về README](../../README.md)

**Áp dụng cho:** `v1.4.0-rc.1` · Windows x64 · Cập nhật 15/10/2026.

> **Bản 1.5.0 (22/10/2026):** cài từ thư mục chuyển giao và đưa nhân vật/thư viện sang bằng Gói thư viện — xem [Cài lên máy thứ hai](second-machine-1.5.0.md). Các mục dưới đây vẫn đúng cho yêu cầu hệ thống và xử lý sự cố.

> **Cập nhật mã nguồn 16/10/2026:** bộ chọn giọng riêng theo nhân vật/video thuộc Phase 48, hướng đến 1.5.0. [Hướng dẫn tính năng](character-voices.md) áp dụng khi chạy mã nguồn mới; gói EXE 1.4.0-rc.1 bên dưới chưa có bộ chọn này. Chỉ cập nhật thư mục mã nguồn không thay backend/frontend đã đóng trong EXE.

## 1. Hiểu đúng gói cài hiện tại

Gói Windows chứa EXE, Python backend và thư viện đi kèm. Sau khi thiết lập, bạn mở ứng dụng bằng icon logo trên Desktop, không cần gõ lệnh mỗi lần sử dụng.

**Đây là bản ZIP liên kết với runtime bên ngoài.** Bộ cài chưa tự động cài Node.js, renderer, FFmpeg, môi trường AI ảnh hoặc model. Chưa có `Setup.exe` cài toàn bộ các thành phần trên máy mới.

| Thành phần | Bắt buộc khi nào? | Cách chuẩn bị |
|---|---|---|
| Windows x64, thư mục có quyền ghi, trình duyệt web | Mọi lần sử dụng | Windows 11 x64 đã được kiểm thử |
| Mã nguồn đúng tag | EXE cần liên kết renderer và image-worker path | Tải Source ZIP bên dưới; không cần Git nếu dùng ZIP |
| Node.js ≥ 24 và npm | Dựng video bằng Remotion | [Tải Node.js](https://nodejs.org/en/download) |
| FFmpeg **và ffprobe** | Audio, đọc media, dựng/xuất video | [Trang tải FFmpeg](https://ffmpeg.org/download.html); chọn bản Windows có cả hai EXE và thêm thư mục `bin` vào PATH |
| Phụ thuộc renderer và Chrome Headless Shell | Dựng video | Cài bằng lệnh ở mục 3 |
| Internet | Tải phụ thuộc, Edge TTS và AI cloud | Cấu hình mạng cho các dịch vụ đang sử dụng |
| API key Gemini hoặc OpenRouter | Tạo nội dung bằng AI cloud | Nhập trong Settings; không đi kèm gói tải |
| Python backend riêng | Chỉ chạy/build từ source | Không cần khi sử dụng EXE đóng gói |
| NVIDIA/CUDA, `.venv-image`, model Qwen | Chỉ tạo ảnh AI local | Thiết lập riêng, xem mục 6 |
| Ollama và model | Chỉ AI văn bản local/fallback | Thiết lập riêng, xem mục 6 |

**Cấu hình tham chiếu đã dùng:** Windows 11 Pro x64, khoảng 32 GB RAM, RTX 3060 12 GB VRAM. Chưa có mức RAM/VRAM tối thiểu được xác nhận cho mọi chức năng. Không có bản native macOS, Linux hoặc Windows ARM trong release này.

ZIP ứng dụng khoảng **140,5 MB**, giải nén khoảng **320,8 MB**. Cần thêm dung lượng cho Node dependencies, trình duyệt render, media và video xuất; nếu dùng AI ảnh local, môi trường và model có thể chiếm thêm hàng chục GB.

## 2. Tải đúng phiên bản và chuẩn bị thư mục

Tải hai gói sau:

1. **[Mã nguồn v1.4.0-rc.1](https://github.com/danghoangsqtt-sys/dailyintelenglish/archive/refs/tags/v1.4.0-rc.1.zip)**.
2. **[Ứng dụng Windows x64](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/download/v1.4.0-rc.1/DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip)**.

[Trang phát hành](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/tag/v1.4.0-rc.1) có ghi chú và [tệp checksum](https://github.com/danghoangsqtt-sys/dailyintelenglish/releases/download/v1.4.0-rc.1/DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip.sha256).

Giải nén Source ZIP, đổi tên thư mục gốc thành `DailyBeyondEnglishStudio` rồi đặt ở nơi tài khoản có quyền ghi, ví dụ `C:\Users\<tên-bạn>\Apps\DailyBeyondEnglishStudio`. **Thư mục gốc phải chứa trực tiếp** `backend`, `frontend`, `renderer`, `scripts`.

Mở PowerShell trong thư mục gốc. Giải nén **toàn bộ** gói ứng dụng vào `data\tmp\desktop-download`. Kết quả cần có cấu trúc:

```text
DailyBeyondEnglishStudio/
├── backend/
├── frontend/
├── renderer/
│   ├── package.json
│   └── package-lock.json
├── scripts/
│   └── install_desktop.ps1
└── data/
    └── tmp/
        └── desktop-download/
            └── DailyIntelEnglishStudio/
                ├── DailyIntelEnglishStudio.exe
                ├── _internal/
                └── studio-runtime.json
```

Có thể kiểm tra tệp ZIP đã tải bằng PowerShell, thay đường dẫn ví dụ bằng vị trí thật:

```powershell
Get-FileHash "$env:USERPROFILE\Downloads\DailyBeyondEnglishStudio-1.4.0-rc.1-windows-x64.zip" -Algorithm SHA256
```

SHA-256 của gói phát hành:

```text
0abdb9616593ecc983c152d00c0ee08380ee7240c4aa54e6b94d7916eed91b09
```

## 3. Chuẩn bị renderer và FFmpeg

Sau khi cài Node.js và thêm FFmpeg vào PATH, **mở PowerShell mới** tại thư mục gốc để nhận PATH mới. Kiểm tra:

```powershell
node --version
npm --version
ffmpeg -version
ffprobe -version
```

Node phải là phiên bản **24 trở lên**; cả `ffmpeg` và `ffprobe` phải chạy được. Tiếp theo:

```powershell
Push-Location renderer
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Cài renderer thất bại.' }
npx remotion browser ensure
if ($LASTEXITCODE -ne 0) { throw 'Chuẩn bị trình duyệt render thất bại.' }
Pop-Location
```

Với mã nguồn Phase 49 mới, chạy thêm `npm --prefix renderer run build:preview` tại thư mục gốc để tạo Player trong Step 5. Mã nguồn tại tag phát hành 1.4.0-rc.1 chưa có lệnh này; không áp dụng bước này cho tag cũ.

`npm ci` cài theo lockfile của bản phát hành. `remotion browser ensure` tải/kiểm tra trình duyệt dành cho render; trình duyệt này khác với trình duyệt bạn dùng mở giao diện.

Nếu PowerShell chặn `npm.ps1`/`npx.ps1`, dùng `npm.cmd` và `npx.cmd` tương ứng trong các lệnh trên.

## 4. Cài ứng dụng và tạo icon Desktop

Tại thư mục gốc, sau khi các lệnh ở mục 3 thành công:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_desktop.ps1 -StageDirectory .\data\tmp\desktop-download\DailyIntelEnglishStudio
```

Script sẽ:

- Cài cả thư mục ứng dụng vào `dist\DailyIntelEnglishStudio`.
- Tạo `studio-runtime.json` liên kết đúng mã nguồn và `data` trên máy này.
- Tạo shortcut **Daily Beyond English Studio** trên Desktop với logo ứng dụng.
- Nếu có bản EXE cũ tại vị trí cài, dừng bản đó và giữ bản sao trong `data\backups\desktop-<thời gian>` trước khi thay thế.

**Chờ các tác vụ đang chạy hoàn tất trước khi cài đè.** Script không chờ render hoàn thành. Thư mục staging phải nằm trong thư mục mã nguồn và khác thư mục cài cuối cùng; không dùng `dist\DailyIntelEnglishStudio` làm `-StageDirectory`.

## 5. Mở và kiểm tra lần đầu

1. Nhấn icon **Daily Beyond English Studio** trên Desktop.
2. Giao diện tự mở tại `http://localhost:8000` nếu dùng cổng mặc định.
3. Trong **Settings**, cấu hình AI cloud với key của bạn, hoặc thiết lập Ollama nếu dùng AI văn bản local.
4. Tạo project thử ngắn: tạo kịch bản → tạo audio → chuẩn bị ảnh/cử chỉ bằng thư viện hoặc nhập tài nguyên → render → mở video xuất.
5. Kiểm tra riêng định dạng 16:9 và 9:16 nếu dùng cả hai.

Bạn có thể sử dụng ảnh nhập từ bên ngoài mà không cần cài model tạo ảnh local. Khi cloud lỗi, fallback sang local chỉ hoạt động nếu Ollama/model đã được thiết lập.

**Vận hành hằng ngày**

- Mở bằng icon, không cần chạy lại các lệnh cài renderer.
- Giữ nguyên `dist\DailyIntelEnglishStudio`, `_internal`, thư mục `renderer` và cấu trúc workspace. Không kéo riêng EXE ra Desktop.
- Bấm icon lần nữa khi ứng dụng đã chạy sẽ mở lại giao diện tại cổng đó.
- Đóng tab trình duyệt không dừng dịch vụ. Khi cần dừng hoàn toàn, đợi job hoàn tất, mở Task Manager và kết thúc đúng `DailyIntelEnglishStudio.exe` của ứng dụng này.
- Nếu đổi vị trí thư mục, shortcut cũ không tự cập nhật. Sao lưu rồi cài lại shortcut; việc đổi ổ đĩa còn có thể ảnh hưởng đường dẫn media đã lưu.

## 6. Các thành phần AI cục bộ — tùy chọn

### AI văn bản với Ollama

Cài [Ollama cho Windows](https://docs.ollama.com/windows), chuẩn bị model mà Settings đang sử dụng và bảo đảm dịch vụ truy cập được. Cấu hình mặc định của release dùng `qwen3.5:9b` tại `http://127.0.0.1:11434`.

Xem [hướng dẫn local AI của bản phát hành](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/local-ai.md). Ollama không thay thế Edge TTS; việc tạo giọng đọc vẫn cần Internet.

### Tạo ảnh Qwen trên GPU NVIDIA

Đây là thiết lập riêng, không được tự cài khi chạy EXE:

- Python **3.14** là phiên bản đã được kiểm thử cho môi trường image worker.
- Tạo mới `.venv-image` trên máy đích, cài PyTorch có CUDA và các phiên bản trong [`backend/ai/image/requirements.txt`](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/backend/ai/image/requirements.txt). Tệp này có lệnh cài của môi trường tham chiếu.
- Kiểm tra `torch.cuda.is_available()` trả về `True`. Worker không chấp nhận bản PyTorch chỉ có CPU cho luồng tạo ảnh này. Xem [hướng dẫn cài PyTorch chính thức](https://pytorch.org/get-started/locally/) để đối chiếu driver và bộ cài CUDA.
- Chuẩn bị **đầy đủ** cache model tại `backend\ai\models\image`, theo khai báo trong [`qwen_runner.py`](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/backend/ai/image/qwen_runner.py): Qwen-Image-2.1-Turbo và/hoặc Qwen-Image-Edit-2511 cùng GGUF, text encoder, tokenizer, VAE và LoRA liên quan.
- App đọc model từ cache cục bộ. Chỉ tải một tệp GGUF là chưa đủ; phải giữ cấu trúc Hugging Face cache/snapshot tương ứng. ZIP hiện chưa cung cấp công cụ cài model tự động.

Không sao chép nguyên `.venv-image` từ máy cũ để thay cho cài đặt trên máy mới. Model cache có thể sao lưu/chuyển riêng, nhưng phải kiểm tra lại tính đầy đủ và đường dẫn.

## 7. Xử lý sự cố thường gặp

| Hiện tượng | Kiểm tra / cách xử lý |
|---|---|
| Bấm icon không mở giao diện | Mở `data\logs\desktop.log`, kiểm tra workspace, quyền ghi và cổng. Thử truy cập `http://localhost:8000`. |
| Báo workspace không hợp lệ | Xem `studio-runtime.json`; workspace phải chứa `renderer\package.json` và `backend\ai\image\image_worker.py`. Cài lại bằng script từ đúng mã nguồn tag. |
| Không tìm thấy Node/FFmpeg | Kiểm tra PATH và các lệnh mục 3; khởi động lại ứng dụng sau khi thay PATH. `ffprobe` cũng phải có trong PATH. |
| Thiếu renderer/trình duyệt render | Chạy lại `npm ci` và `npx remotion browser ensure` trong `renderer`. |
| Không tạo được kịch bản | Kiểm tra mạng, API key/model trong Settings; nếu dùng local, kiểm tra Ollama và model. |
| Không tạo được giọng đọc | Kiểm tra kết nối đến dịch vụ Edge TTS; đây là dịch vụ trực tuyến. |
| Không tạo được ảnh AI local | Kiểm tra `.venv-image`, CUDA, VRAM và đầy đủ model cache; trạng thái có venv không chứng minh model đã sẵn sàng. |
| Render chậm hoặc lỗi driver | Bản Windows mặc định dùng ANGLE. Có thể đặt `DIE_REMOTION_GL=auto` trong `.env` ở thư mục gốc và khởi động lại để thử chế độ tự chọn. Xem báo cáo bên dưới. |
| Mở nhầm dịch vụ ở cổng 8000 | Dừng dịch vụ đang chiếm cổng, hoặc chọn cổng khác bằng `DIE_APP_PORT` trong `.env`, rồi khởi động lại ứng dụng. |

File `.env` là cấu hình tùy chọn tại thư mục gốc; nếu chưa có, có thể tạo tệp chỉ chứa các giá trị cần thay đổi. Mặc định timeout render là 3.600 giây, cấu hình bằng `DIE_REMOTION_RENDER_TIMEOUT_SECONDS` trong phạm vi 60–7.200 giây.

[Báo cáo hiệu năng và giới hạn phép đo](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/render-performance-20261015.md) · [Build, smoke test và khôi phục bản cũ](https://github.com/danghoangsqtt-sys/dailyintelenglish/blob/v1.4.0-rc.1/docs/operations/exe-trial-20261015.md).

## 8. Dữ liệu và chuyển từ máy cũ

- Máy mới mặc định tạo dữ liệu riêng trong `data` của workspace sau khi cài bằng script. Gói tải không chứa project của máy đang phát triển.
- Trước khi sao lưu, chờ job hoàn tất và dừng ứng dụng; sao lưu **toàn bộ `data`**, thư mục xuất bên ngoài và tài nguyên/model bổ sung nếu cần.
- Dữ liệu hiện có thể chứa đường dẫn tuyệt đối đến media hoặc thư mục xuất. Chép `data` sang ổ/thư mục khác **không bảo đảm** mọi liên kết media tự đổi theo; cần kiểm tra lại project, thư viện và Project Folder trước khi tiếp tục sản xuất.
- Cấu hình/key cá nhân không được đưa lên GitHub hoặc chia sẻ trong gói công khai. Dùng key riêng trên máy đích và chỉ chuyển bản sao lưu qua kênh tin cậy.
- Không chuyển nguyên `node_modules` hoặc Python venv làm cách cài mặc định; dựng lại môi trường từ lockfile/requirements trên máy đích.

## Phạm vi xác minh

Tài liệu được đối chiếu với mã nguồn, script cài và gói `v1.4.0-rc.1`. Gói đã được smoke test trên máy tham chiếu có runtime; **chưa có kiểm thử cài mới từ đầu trên một máy Windows sạch**. Những yêu cầu trên giúp chuẩn bị đúng thành phần, không thay thế kết quả kiểm thử máy đích.


## Bản thử cục bộ và lỗi mở nhầm bản cũ (Phase 51)

ZIP phát hành `v1.4.0-rc.1` trên GitHub là gói ngày 2026-10-15. Bản thử dựng từ mã nguồn mới có thể vẫn mang số 1.4.0-rc.1. Xem **Settings → Desktop … Build …** để biết bản đang thực sự phục vụ trình duyệt; `/api/system/build` cung cấp cùng nhận diện mà không trả về đường dẫn dữ liệu.

Nếu hồ sơ cũ thiếu **Character voice** hoặc **Presenter · 21 pictures**, kiểm tra bản đang chạy. Chỉ cập nhật mã nguồn hoặc mở một EXE khác trong khi bản cũ giữ cổng 8000 sẽ không nâng cấp tiến trình cũ. Launcher mới chỉ mở lại tiến trình khớp cả build và dữ liệu; nếu khác, nó báo cần hoàn tất tác vụ và cập nhật ứng dụng. Không tự dừng tác vụ khi bấm EXE.

Từ đúng workspace mã nguồn mới, hoàn tất hoặc hủy tác vụ đang chạy, rồi dựng staging và cài:

```powershell
powershell -NoProfile -File scripts/build_exe.ps1 -OutputRoot data/tmp/phase51-exe-stage
powershell -NoProfile -File scripts/install_desktop.ps1 -StageDirectory data/tmp/phase51-exe-stage/DailyIntelEnglishStudio
```

Script cài kiểm tra các job chưa kết thúc và integrity/FK; sao lưu SQLite bằng API backup để giữ cả dữ liệu đã commit trong WAL. Script chỉ dừng EXE tại đường dẫn cài đích, giữ nguyên bản cũ và shortcut trong `data/backups/desktop-<thời gian>/`, rồi thay toàn bộ thư mục ứng dụng. Có cả `app.before-upgrade.db` và `app.at-exit.db`; ảnh/media vẫn ở thư mục dữ liệu hiện có. Script không tự phát hành hoặc tự mở bản vừa cài: bấm lại icon **Daily Beyond English Studio** và kiểm tra Settings.

Trong **Character Library → Profiles**, mở Hoang hoặc hồ sơ cũ: phần **Character voice** nằm trên khu vực ảnh; **Conversation · 29 pictures** và **Presenter · 21 pictures** là hai tab riêng. Tạo/duyệt `calm__closed` trước để mở các ô phụ thuộc; prompt và ảnh tham chiếu đã có trong từng ô. Xem [hướng dẫn Solo](solo-explainer.md).

Nếu cần quay về bản trước, giữ cả backup DB và thư mục EXE/shortcut cùng đợt. Đóng hoàn toàn Studio trước khi khôi phục cặp tương ứng; giữ riêng các chỉnh sửa phát sinh sau nâng cấp, tránh chạy EXE cũ trên schema mới. Việc nâng cấp cục bộ không thay gói GitHub, không xác nhận bộ ảnh thật hoặc nghiệm thu V49. Đây vẫn là thử nghiệm trên máy tham chiếu, không phải kiểm thử cài sạch Windows.
