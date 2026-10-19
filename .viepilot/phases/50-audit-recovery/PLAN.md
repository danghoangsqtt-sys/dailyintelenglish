# PLAN — Phase 50: audit recovery

Status: execution_authorized2026-10-16. Owner đã yêu cầu cả evolve và auto; không cần một vòng xác nhận triển khai khác.

1. [50.1](tasks/task-50.1.md) — BUG-042 rollback/cancellation, regression tests.
2. [50.2](tasks/task-50.2.md) — BUG-044 docs accuracy, thực hiện sau review 49.5b để mô tả đúng mức verified.

49.5b/BUG-043 vẫn thực hiện trong phase 49; giữ current_phase49. Phase 50 là remediation scope độc lập, không thay dependency chain 49.6→49.10. Không version bump ứng dụng; ghi Unreleased source.

Risk: shared transaction helper ảnh hưởng mọi domain; test cancellation sau write, trong commit/rollback, failure rollback và caller isolation. Metadata-only Node description không đòi cài lại dependencies. Persistence theo user authorization và sandbox approvals; không mark formal acceptance tự động.
