# Phase 83 — A default save folder (2026-10-28)

Owner (2026-10-28): "trong lập trình thêm thiết lập thư mục mặc định để lưu video tránh trường hợp các video tạo tự
động bị lưu sai chỗ khó quản lý", then make short and long test videos in D:\Videos to check each feature.

## Finding

Phase 80.6 added one main save folder (`app_settings.main_output_dir`), but it is empty until the owner picks one. The
live app has none, so every project made by Automation, the Channel plan or the Shorts batch keeps its files only inside
the app's data folder (`data/projects/...`); nothing reaches a folder the owner manages.

## Tasks

1. **83.1 Default main folder** — when no main folder is saved, the app uses a default one: `D:\Videos` when drive D:
   exists, otherwise `<user>\Videos\Daily Beyond English` (setting `DIE_DEFAULT_OUTPUT_DIR`: `auto` (default), a full
   path, or `off`). `export_service.main_folder` returns the saved folder or the default; the default folder is created
   when first used. "Stop using it" becomes "Use the default folder" (clears the saved choice; it no longer turns the
   main folder off). The API view adds `is_default` and `default_dir`; the shared widget shows "(default)". Projects that
   already exist are still only given a folder through the explicit "apply" action; nothing is moved. Tests run with
   the default `off` (autouse fixture) except the new tests, so no test writes to D:\Videos.
   Paths: `backend/core/config.py`, `backend/content/export_service.py`, `backend/api/export.py`,
   `frontend/static/js/main_folder.js`, `frontend/static/js/i18n_vi.js`, `tests/conftest.py`, `tests/test_main_folder.py`.
2. **83.2 Test videos** — with the installed app (owner's request; its main folder set to `D:\Videos`), make one video
   of each kind through the app's own flows: Shorts batch templates (news, text on blur, Don't say / Say, Word of the
   day, Top 5, quiz, listen, chat, would you rather, slow podcast, flashcards, presenter, Vox) and long episodes
   (two-character conversation, Solo presenter), plus highlight clips cut from a long episode. Record for each: result,
   length, folder, and what stopped it (for example the fact review that news / Vox wait for, by design).
3. **83.3 Verify and record** — full pytest, records; offer build and install.
