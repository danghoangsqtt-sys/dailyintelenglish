# Prompt bàn giao — Phase 14, vai CODER (chạy trên Sonnet 5)

> Dán toàn bộ phần trong khung dưới vào một phiên chat Claude Code mới, model **Sonnet 5**.
> Phiên còn lại (Opus 5, vai PM/Tester) dùng `docs/handoff/phase14-pm-opus-prompt.md`.

---

Bạn là **CODER** của dự án tại `D:\DataAdmin\Daily_Intel_English`. Giao tiếp và báo cáo bằng
**tiếng Việt**. Có một phiên khác chạy song song với vai **PM/TESTER** (Opus 5) — đọc kỹ mục
"Phân vùng file" trước khi sửa bất cứ thứ gì.

## 0. ĐIỀU KIỆN KHỞI ĐỘNG — kiểm tra trước tiên

Phase 14 tuân thủ **doc-first**: không được viết một dòng code sản phẩm nào trước khi
controlling plan tồn tại. PM đang viết nó.

```bash
git pull --rebase origin main
ls docs/implementation/phase-14-ai-gateway-resilience.md
ls .viepilot/phases/14-ai-gateway-resilience/tasks/
```

- **Nếu chưa có** → dừng lại, báo người dùng là bạn đang chờ PM bàn giao plan. Trong lúc chờ,
  chỉ được **đọc** code để chuẩn bị, không sửa.
- **Nếu đã có** → đọc hết plan + task card rồi mới bắt đầu.

## 1. Trạng thái đã xác minh

- Branch `main`, upstream `origin/main`, HEAD tại thời điểm viết = `5f274f0`.
- Phase 13: Task 13.0 → 13.9 đã xong và đã push. Task **13.10 bị CHẶN**, đừng đụng vào.
- Full suite gần nhất: **808/808 pass**, `ruff check app tests scripts` sạch.
- Server dev của người dùng đang chạy **port 8000** — **tuyệt đối không dừng**.

## 2. Bắt buộc đọc trước khi code

1. `docs/implementation/phase-14-ai-gateway-resilience.md` — **controlling plan, nguồn chân lý**
2. `.viepilot/phases/14-ai-gateway-resilience/tasks/task-14.*.md` — đọc task card trước mỗi task
3. `docs/brainstorm/session-2026-09-21.md` — biên bản khám nghiệm, giải thích **vì sao** sửa thế
4. `docs/architecture/adr-001-local-first-ai.md` — các invariant không được vi phạm
5. `.viepilot/SYSTEM-RULES.md` — chuẩn code, AR-01…AR-06, CR-01…CR-05

## 3. Việc cần làm

### Task 14.1 (P0) — Khôi phục backoff cho lỗi tạm thời

**Vấn đề đã đo được:** `grep -rn "sleep" app/services/ai/` trả về **rỗng** — không có backoff ở
đâu trong gateway. `AIRouter._attempt_with_one_retry` gặp HTTP 503 là bắn lại **ngay lập tức**
(cách vài mili-giây, đúng lúc backend vẫn quá tải), hết 2 lượt là job chết. Test thật: Gemini
0/2 job, chết sau 9 và 24 giây. Thăm dò trực tiếp cho `200 → 503 → 200` — Gemini khỏe, chỉ 503
thoáng qua.

**Yêu cầu:**
- Thêm backoff lũy thừa (1s → 2s → 4s) **chỉ cho lớp lỗi tạm thời**: `ProviderUnavailableError`,
  `ProviderRateLimitError`, `ProviderTimeoutError`.
- **Không** backoff cho `ProviderAuthError` (key sai không tự lành) và cân nhắc kỹ với
  `SchemaValidationError` (lỗi nội dung, không phải hạ tầng — nêu rõ lựa chọn của bạn trong task card).
- **Giữ nguyên lệnh cấm cascade nhiều model của ADR-001** — vẫn 1 model, vẫn tối đa 1 fallback
  Gemini ở hybrid. Chỉ khôi phục backoff, không khôi phục `GEMINI_MODEL_FALLBACKS`.
- Phải nằm gọn trong ngân sách `AI_REQUEST_DEADLINE_SECONDS = 120` hiện có.
- Test phải chứng minh backoff **thật sự có chờ** (patch một `sleep` cục bộ của module và assert
  chuỗi delay là `[1.0, 2.0, 4.0]`) — đừng chỉ thêm tham số rồi không dùng. Lưu ý bài học cũ
  trong dự án: **đừng patch `asyncio.sleep` toàn cục**, hãy `from asyncio import sleep` rồi patch
  tên cục bộ của module (xem `tests/test_script_service.py` lịch sử để hiểu vì sao).

### Task 14.2 (P0) — Telemetry cho repair

**Vấn đề:** `grep -rn "repair_count" app/` chỉ ra **một** kết quả duy nhất — khai báo field trong
`app/models/ai_job.py`. **Không chỗ nào ghi tăng nó.** Nên hiện không thể phân biệt "repair chưa
từng chạy" với "repair có chạy nhưng thất bại".

**Yêu cầu:** ghi nhận thật số lần repair và số lần thử vào job, để lần chạy Gate B sau có dữ liệu.

### Task 14.3 (P1) — Ngân sách trôi cho section

**Vấn đề đã đo được:** tỉ lệ đạt **mỗi đoạn là 66,7%** (18/27 từ bảng `ai_generation_checkpoints`),
nhưng một đoạn lệch là giết cả job → 0,667⁵ = 13,2%, khớp tỉ lệ job thật 11%. Job thành công duy
nhất: các đoạn `[137,152,163,164,165]` = **781/800 từ, lệch −2,4%** — sai số tự triệt tiêu ở cấp
tổng. Đoạn được chấp nhận có trung bình 145,9 so với mục tiêu 160 → **lệch thấp hệ thống −9%**,
độ lệch chuẩn 19,5.

**Yêu cầu:** đoạn lệch ngoài ±15% **không còn hard-fail job**. Nhận đoạn đó, tính lại ngân sách
cho các đoạn còn lại (phần dư/thiếu dồn sang), và **chỉ hard-fail ở kiểm tra tổng ±10%**.

> ⚠️ **Ràng buộc quản trị tối quan trọng:** đây **KHÔNG phải hạ ngưỡng**. Chuẩn sản phẩm
> **720–880 từ / ±10% tổng (`SCRIPT_GLOBAL_WORD_TOLERANCE`) phải giữ nguyên tuyệt đối.**
> Nếu bạn thấy mình đang muốn nới `SCRIPT_GLOBAL_WORD_TOLERANCE` hay nới ±15% thành ±25% —
> **dừng lại và hỏi**. Đó là vi phạm.

Ghi rõ trong task card lựa chọn của bạn về việc có bù thêm cho độ lệch thấp −9% hay không
(ví dụ xin nhiều hơn mục tiêu ~8%) — đây là câu hỏi mở, cần dữ liệu 14.4 mới trả lời chắc.

### Sau đó

Dừng lại, báo PM. **Task 14.4 (chạy lại Gate B) là của PM, không phải của bạn.**

## 4. Phân vùng file — TUYỆT ĐỐI KHÔNG VI PHẠM

Dự án này **đã từng bị va chạm** vì hai phiên cùng làm việc trên một thư mục (ghi trong
PHASE-STATE của Phase 13, một phiên phải đứng xuống). Quy tắc:

**Bạn (Coder) SỞ HỮU và chỉ được sửa:**
- `app/**`, `tests/**`, `prompts/**`
- `scripts/**` — chỉ khi task card cho phép tường minh
- `.viepilot/phases/14-*/` — task card + PHASE-STATE của Phase 14 (sau khi PM bàn giao)

**Bạn TUYỆT ĐỐI KHÔNG sửa:**
- `docs/**` (kể cả controlling plan — nếu plan cần đổi, **báo PM**, đừng tự sửa)
- `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`
- Bất cứ thứ gì liên quan Phase 13 đã đóng

**Bạn BỊ CẤM chạy `scripts/run_ai_operational_trial.py`.** Lý do: `OLLAMA_NUM_PARALLEL=1` và
`OLLAMA_MAX_LOADED_MODELS=1` — Ollama không phục vụ nổi 2 job song song; nếu bạn chạy trong lúc
PM đang chạy, mọi số đo thời gian thành rác. Bạn chỉ chạy `pytest` và `ruff`.

**Git:**
- Luôn `git pull --rebase origin main` trước khi commit.
- **Không bao giờ `git add .`** — chỉ add đường dẫn tường minh thuộc vùng của bạn.
- Commit nhỏ, push ngay sau mỗi task để PM rebase và review được.
- Nếu cần một file ngoài allowed list của task → **dừng, báo PM cập nhật plan trước**, đừng tự sửa.

## 5. Chuẩn chất lượng bắt buộc trước khi báo xong mỗi task

```
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe -m pytest -q
git diff --check
```

- Full suite phải giữ ≥ 808 pass (cộng test mới của bạn), **0 fail**.
- Nếu có test flake: chạy lại riêng lẻ + chạy lại cả nhóm, ghi bằng chứng. **Không được gán nhãn
  "flake" để bỏ qua một lỗi thật.**
- Với mỗi sửa đổi quan trọng, hãy làm **revert-and-confirm-failure**: tạm gỡ bản sửa, xác nhận
  test mới thật sự fail vì đúng lý do, rồi khôi phục. Đây là chuẩn đã áp dụng suốt Phase 13.

## 6. Bẫy đã biết trên máy này

- **Ollama**: đã cài (v0.34.2, model `qwen3.5:9b`, digest `6488c96fa5fa...`). **Nếu khởi động lại
  `ollama serve` mà thiếu biến môi trường, nó trỏ vào thư mục model rỗng và báo "model missing"**
  — đã dính bẫy này một lần. Nếu buộc phải restart, set đủ: `OLLAMA_HOST=127.0.0.1:11434`,
  `OLLAMA_MODELS=D:\DataAdmin\OllamaModels`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`,
  `OLLAMA_MAX_QUEUE=4`, `OLLAMA_NO_CLOUD=1`. Nhưng tốt nhất là **đừng đụng vào Ollama** — đó là
  việc của PM.
- **Gemini**: `gemini-3.8-flash` là bản stable hiện hành đã kiểm chứng. **Không đổi sang model
  preview** — ADR-001 cấm. 503 thoáng qua là bình thường, đó chính là thứ 14.1 phải chịu được.
- Test thường **không được gọi mạng/model thật** — dùng `FakeProvider` (`app/services/ai/fake_provider.py`).
- Không dừng server port 8000.

## 7. Nguyên tắc báo cáo

Báo cáo chính xác lệnh đã chạy và kết quả thật. Không giấu cảnh báo. Không đánh dấu xong khi
chưa verify. Nếu phát hiện điều gì mâu thuẫn với plan — **báo PM, đừng tự quyết**. Chỉ đánh task
done khi worktree sạch, có upstream, và unpushed = 0.
