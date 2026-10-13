-- Daily Intel English Studio — app-level key/value settings (Task 12.1)
--
-- App-global, not per-project, so it doesn't belong on `projects` — currently holds
-- only `gemini_api_key`, but is a plain key/value table so future app-level settings
-- (if any) don't need their own migration.
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
