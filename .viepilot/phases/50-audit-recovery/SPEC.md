# SPEC — Phase50: audit recovery BUG-042 và BUG-044

Owner2026-10-16 gọi `vp-evolve` xử lý các BUG và `vp-auto` triển khai, rà soát hoàn tất49.5b. Đây là corrective scope trong target1.5.0; không phát hành hay thay version runtime.

- BUG-042: cancelled shared write phải rollback trước khi nhả lock; reads/writes kế tiếp không thấy/commit dữ liệu bỏ dở. Giữ shared aiosqlite architecture.
- BUG-044: docs tách publishedrc.1, source verified và planned49.x; renderer docs khớp production subprocess/compositions.
- BUG-043 xử lý ngay tại49.5b vì đã thuộc schema/API Paths của task49.5; không tạo task duplicate.
- Không thay đổi owner DB, installed EXE, pending visual/listening gates hoặc thực hiện49.6–49.10 trong lượt này.

## Acceptance

Focused regressions fail trước fix/pass sau fix, full pytest, Ruff, JS syntax, renderer Vitest/TypeScript; docs path/diagram review. Ghi technical verification riêng owner acceptance, commit/push persistence riêng quality results.
