# Claude Code Handoff Prompt — Resume Phase 13

Copy the prompt below into Claude Code from the repository root.

---

```text
/vp-auto

Bạn tiếp quản việc triển khai Phase 13 — Local-First AI Reliability trong repo:

D:\DataAdmin\Daily_Intel_English

Hãy giao tiếp và báo cáo bằng tiếng Việt. Đây là phần tiếp tục của một phiên Codex bị
dừng đột ngột vì quota, không phải yêu cầu lập kế hoạch lại từ đầu. Người dùng đã phê
duyệt thực thi toàn bộ kế hoạch và yêu cầu chạy tự động; không cần xin phê duyệt lại cho
các hành động nằm trong task contract. Chỉ dừng tại control point thật sự: rủi ro dữ
liệu/bảo mật, gate thất bại, thay đổi kiến trúc ngoài allowed files, hoặc cần lựa chọn
người dùng có hậu quả đáng kể.

## 1. Bắt buộc đọc trước khi hành động

Đọc đầy đủ, theo thứ tự:

1. `.agents/skills/vp-auto/SKILL.md` hoặc skill `vp-auto` đang được Claude Code cài đặt.
2. `.viepilot/AI-GUIDE.md`
3. `.viepilot/SYSTEM-RULES.md`
4. `.viepilot/ARCHITECTURE.md`
5. `.viepilot/TRACKER.md`
6. `.viepilot/ROADMAP.md`
7. `.viepilot/HANDOFF.json`
8. `docs/brainstorm/session-2026-09-18.md`
9. `docs/implementation/phase-13-local-first-ai-reliability.md` — controlling contract;
   không tự hạ acceptance threshold.
10. `.viepilot/phases/13-local-first-ai-reliability/SPEC.md`
11. `.viepilot/phases/13-local-first-ai-reliability/PHASE-STATE.md`
12. `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.1.md`
13. `docs/architecture/adr-001-local-first-ai.md`
14. File WIP chưa commit: `scripts/qualify_local_ai.py`

Không sửa code trước khi đã đọc và đối chiếu các file trên. `.viepilot/STACKS.md` không
tồn tại; global stack cache không có FastAPI/aiosqlite/httpx summary phù hợp. Áp dụng
`SYSTEM-RULES.md`, dependency đã pin, pattern hiện có và tài liệu provider chính thức.

## 2. Trạng thái Git/checkpoint đã xác minh

- Branch `main`, upstream `origin/main`.
- Commit doc-first đã push:
  `e5ecc43 docs(phase): plan Phase 13 local-first AI reliability`.
- Task 13.0 hoàn tất; Task 13.1 `in_progress`; Tasks 13.2–13.10 `pending`.
- Khi recovery bắt đầu, worktree chỉ có file WIP:
  `?? scripts/qualify_local_ai.py`. Handoff checkpoint đã đưa file này vào Git để không
  bị mất; đây vẫn là WIP, không phải bằng chứng Task 13.1/Gate A đã hoàn tất.
- Runner đã qua ruff và `--help`, nhưng chưa chạy Gate A thật vì model chưa pull.
- Trước khi tiếp tục, chạy lại `git status --short --branch` (kỳ vọng sạch sau handoff)
  và đọc toàn bộ file WIP; không xóa hoặc overwrite file này.

## 3. Task 13.0 đã xong — không lặp lại

- Kế hoạch 595 dòng và 11 task contract đã lưu trước code; hai review read-only đã hợp
  nhất.
- `venv\Scripts\python.exe scripts\verify_ai_baseline.py` đã pass: 3 golden projects,
  4 endpoint contracts.
- DB thật đã backup bằng SQLite Online Backup API:
  `data/backups/app-before-phase13-20260918T164151Z.db`.
- Backup bị gitignore, có thể chứa Gemini API key trong DB; không stage/upload/in raw.
- Size `1,290,240` bytes; SHA-256:
  `ba0359aad4bdcd0222781ce9ffb61278f2c94c6efc893432f687b082538fd033`.
- Source và backup: `integrity_check=ok`, 0 FK violation, 6 migrations, 293 projects,
  573 script lines, 157 learning-content rows.

Không tạo backup mới trừ khi migration mới sắp apply sau khi dữ liệu đã đổi; nếu cần,
vẫn dùng SQLite Online Backup API/`.backup`, không copy file DB đang mở.

## 4. Trạng thái Ollama chính xác sau phiên bị dừng

Ollama đã cài thành công; không cài lại:

- Official winget package `Ollama.Ollama`, version `0.34.2`.
- Binary:
  `C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe`.
- Shell có thể chưa refresh PATH; dùng exact binary hoặc refresh PATH an toàn. Không coi
  `command not found` là chưa cài.
- Đang listen duy nhất trên `127.0.0.1:11434`; API trả version 0.34.2.
- `/api/tags` và `ollama list` đều rỗng: `qwen3.5:9b` CHƯA được pull.
- Model directory: `D:\DataAdmin\OllamaModels`.
- User environment đã lưu:
  - `OLLAMA_HOST=127.0.0.1:11434`
  - `OLLAMA_MODELS=D:\DataAdmin\OllamaModels`
  - `OLLAMA_MAX_LOADED_MODELS=1`
  - `OLLAMA_NUM_PARALLEL=1`
  - `OLLAMA_MAX_QUEUE=4`
  - `OLLAMA_NO_CLOUD=1`
- Server log xác nhận `OLLAMA_NO_CLOUD:true`, `Ollama cloud disabled: true`, và
  `Listening on 127.0.0.1:11434 (version 0.34.2)`.
- Không mở firewall, bind `0.0.0.0`, thêm tunnel/proxy/CORS origin.
- RTX 3060: 12,288 MiB; lần đo trước cài còn 11,351 MiB; driver 616.56 (cao hơn yêu cầu
  Ollama Windows 551.61).

Server ứng dụng hiện có vẫn chạy port 8000, PID lúc bàn giao 33604. Không dừng server
đó; người dùng yêu cầu giữ server để xem UI/project. Server test riêng phải dùng port
không xung đột và log/PID riêng.

## 5. Việc tiếp theo ngay: hoàn tất Task 13.1 / Gate A

### 5.1 Review và hoàn thiện runner

Đọc toàn bộ `scripts/qualify_local_ai.py`; không tin file đúng chỉ vì ruff pass. Kiểm tra:

- Runner gọi `ollama ps` bằng command name trong khi PATH của process Claude có thể chưa
  thấy binary mới. Resolve exact standard binary hoặc truyền path rõ.
- User env mới có thể chưa nằm trong process env của Claude. Evidence phải lấy từ cấu
  hình thực Ollama/API/log hoặc đọc user env có kiểm soát, không chỉ ghi null từ
  `os.environ.get()`.
- Không ghi full prompt/response, API key, filesystem path nhạy cảm hoặc raw provider
  body. Prompt hash/metrics/status là đủ.
- Evidence đặt dưới `data/quality_reviews/phase13/gate-a/` (gitignored), không commit.
- Đo listener loopback, digest/quantization/size, 3 nested-schema probes, cold/warm,
  tokens/s, VRAM/RAM mỗi giây, `ollama ps`, missing-model, server-down, early stream
  close/cancel, unload và post-cancel health.

Chạy lại:
`venv\Scripts\python.exe -m ruff check scripts\qualify_local_ai.py`

### 5.2 Pull đúng model chính chủ

Nếu PATH chưa refresh:
`& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen3.5:9b`

Download khoảng 6.6 GB; chờ xong thật. Không tải challenger. Sau pull, gọi tags/show/list
và ghi exact digest/size/quantization local. Tag official khi lập plan là Q4_K_M, digest
prefix `6488c96fa5fa`; bằng chứng trên máy sau pull mới authoritative.

### 5.3 Chạy Gate A thật

Đảm bảo process env phản ánh các setting mục 4 hoặc runner đọc chúng đúng, rồi chạy:
`venv\Scripts\python.exe scripts\qualify_local_ai.py`

Gate A chỉ PASS khi:

- listener loopback-only;
- nested JSON Schema 3/3 hợp lệ;
- `ollama ps` 100% GPU;
- 16K còn ≥1.5 GiB VRAM và ≥4 GiB RAM;
- không OOM/TDR/OS-GPU instability;
- cold + warm request thành công;
- model-missing, server-down, cancel/early-close được detect;
- unload thành công.

Nếu chỉ memory headroom fail, thử đúng thứ tự và ghi từng cấu hình:
1. context 8192;
2. Flash Attention nếu backend hỗ trợ;
3. KV cache `q8_0`.

Không tự chuyển KV q4, model khác, bind mạng hoặc hạ threshold. Nếu vẫn fail, ghi Gate A
FAIL và tiếp tục Gemini-primary/local-experimental theo plan; không coi đó là thất bại
của toàn Phase 13.

### 5.4 Hoàn tất artifact Task 13.1

Tạo `docs/operations/local-ai.md` gồm:

- install/version/digest/model location;
- loopback/cloud-disabled/concurrency config;
- start/restart/health/pull/update/unload/uninstall;
- runtime auto-update hoặc digest đổi phải cảnh báo và requalify;
- troubleshooting runtime-down/model-missing/VRAM;
- privacy: local prompt không ra Ollama Cloud; hybrid Gemini fallback là luồng cloud;
- exact Gate A evidence và quyết định PASS/FAIL.

Cập nhật ngay sau gate:

- `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.1.md`
- `.viepilot/phases/13-local-first-ai-reliability/PHASE-STATE.md`
- `.viepilot/TRACKER.md`
- `.viepilot/HANDOFF.json`
- `.viepilot/ROADMAP.md` nếu progress/status đổi.

Không ghi CHANGELOG như feature shipped chỉ vì runtime đã cài. Commit explicit files,
không `git add .`; không stage model, DB backup, evidence JSON, log hoặc media. Push sau
verification. Chỉ đánh task done khi worktree sạch, có upstream và unpushed count = 0.

## 6. Sau Gate A: tiếp tục Tasks 13.2 → 13.10

Không dừng khi 13.1 xong. Theo controlling plan, doc-first/state-first trước mỗi task.
Các invariants không được đổi:

- một typed provider gateway; local/gemini/hybrid rõ semantics;
- stable Gemini model phải live-probe/kiểm tra official docs lúc triển khai; không dùng
  tên suy đoán, preview không vào automatic routing;
- SQLite durable job là source of truth; Gemini background chỉ optional capability;
- atomic claim + lease/heartbeat; một active job/project/operation;
- không giữ DB lock khi model/network/backoff/TTS/ffmpeg;
- final save + job complete cùng transaction;
- input/config/script/template/pipeline hashes ngăn stale overwrite;
- cancel idempotent, late response discard, recovery bounded;
- không partial script/learning publication;
- Ollama URL chỉ HTTP loopback, chống SSRF;
- tối đa một cloud fallback, phải visible vì quota/cost/privacy;
- gateway transport cho script, learning, thumbnail, YouTube; chỉ script/learning dùng
  durable jobs;
- legacy sync endpoint giữ response contract một compatibility release, không âm thầm
  đổi 200/full-result thành 202/job;
- ordinary tests không gọi network/model thật;
- Gate B runner dùng live uvicorn HTTP, không TestClient/mock/pytest.

Đọc task card trước từng task. Nếu cần file ngoài allowed list, cập nhật controlling plan,
task card và state trước khi sửa. Không sửa issue ngoài Phase 13.

## 7. Gate B/full operational trial bắt buộc

Không tuyên bố local-primary trước Gate B:

- local-only, fallback OFF;
- 5 lần B1/8 phút liên tiếp không crash/schema failure/invalid speaker/partial write;
- ≥4/5: 720–880 words, speaker 35–65%, không exact duplicate, repeated 8-gram <1%,
  có intro/outro, human CEFR pass;
- first durable progress ≤90s, mỗi section ≤5 phút, toàn script ≤20 phút;
- learning 5/5 deterministic checks và human review không critical defect;
- một run thật: script → Edge TTS tuần tự mọi line → MP3 → midnight 16:9 MP4 →
  download → ffprobe;
- audio/video 432–528s, A/V lệch ≤1.0s, nonzero/readable, codec đúng, không server
  ERROR/traceback;
- lưu IDs, settings/digest, timings, repair/fallback, resource peak, bytes, SHA-256,
  durations/codecs/warnings; không xóa project; giữ server trial chạy cho user xem.

Gate B fail thì ship durable jobs với Gemini-primary/local-experimental. Task 13.10 phụ
thuộc quyết định Gate B, không bắt buộc local pass. Rollback drill
`hybrid → gemini (Ollama stopped) → hybrid` phải không DB repair/data loss.

## 8. Nguồn chính thức Gate A

- https://docs.ollama.com/windows
- https://docs.ollama.com/faq
- https://docs.ollama.com/api/generate
- https://docs.ollama.com/capabilities/structured-outputs
- https://ollama.com/library/qwen3.5/tags

API/model docs thay đổi được; browse lại nguồn chính thức trước khi khóa behavior.

## 9. Báo cáo và persistence

Sau mỗi task: state update ngay, exact commands/results/deviations/risks, atomic commit và
push. Không giấu warning/flake; flake phải rerun isolation + affected group và ghi bằng
chứng. Không in secret. Không dừng port 8000 hiện hữu. Khi phase xong, báo cáo đầy đủ
Gate A, architecture, suite/build, Gate B timings, media durations/sizes/hashes/errors,
rollout mode và rollback drill.

Bắt đầu bằng việc hiển thị trạng thái đã xác minh, review WIP, rồi hoàn tất Task 13.1.
Không cài lại Ollama và không lập kế hoạch mới thay controlling plan.
```

---

## Snapshot at handoff creation

- Created: 2026-09-19, Asia/Bangkok.
- Ollama API 0.34.2 reachable on loopback; cloud disabled in server log.
- Local model inventory empty.
- Existing app server still listens on port 8000.
- Task 13.1 remains `in_progress`.
- Recovered pre-handoff change: `scripts/qualify_local_ai.py`, preserved in the handoff
  checkpoint as WIP rather than left untracked.
