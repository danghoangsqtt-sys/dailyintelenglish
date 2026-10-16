-- Phase49: extend durable operations without losing existing jobs/checkpoints; immutable illustration assets.
-- Phase 13 -- durable AI generation jobs (additive; script/learning generation moves
-- from a synchronous request/response call to a persisted, resumable job).
-- See docs/implementation/phase-13-local-first-ai-reliability.md section 5.

CREATE TABLE ai_generation_jobs_v2 (
    id TEXT PRIMARY KEY,                    -- UUID
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,                -- script|learning|propose_explainer
    status TEXT NOT NULL,                   -- pending|running|validating|complete|error|cancelled|stale
    stage TEXT NOT NULL,                    -- free-form progress label, e.g. "outline", "section_2"
    progress INTEGER NOT NULL DEFAULT 0,    -- 0-100

    requested_provider TEXT,                -- gemini|local|hybrid (the AI_MODE at creation time)
    actual_provider TEXT,                   -- ollama|gemini (which one actually served the result)
    model TEXT,
    model_digest TEXT,

    input_snapshot_json TEXT NOT NULL,      -- read-only snapshot the worker generated from
    input_hash TEXT NOT NULL,               -- hash of the snapshot, used for staleness checks
    script_hash_at_start TEXT,              -- learning-only: hash of the script it was grounded on
    prompt_hash TEXT,
    template_hash TEXT,
    config_hash TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,

    idempotency_key TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    repair_count INTEGER NOT NULL DEFAULT 0,
    fallback_count INTEGER NOT NULL DEFAULT 0,
    recovery_count INTEGER NOT NULL DEFAULT 0,
    fallback_used INTEGER NOT NULL DEFAULT 0,   -- 0/1
    fallback_reason TEXT,

    cancel_requested INTEGER NOT NULL DEFAULT 0, -- 0/1
    remote_interaction_id TEXT,

    lease_owner TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,

    error_code TEXT,
    error_message TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}',

    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    finished_at TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CHECK (operation IN ('script', 'learning', 'propose_explainer')),
    CHECK (status IN ('pending', 'running', 'validating', 'complete', 'error', 'cancelled', 'stale')),
    CHECK (progress >= 0 AND progress <= 100),
    CHECK (fallback_used IN (0, 1)),
    CHECK (cancel_requested IN (0, 1))
);
INSERT INTO ai_generation_jobs_v2 ("id", "project_id", "operation", "status", "stage", "progress", "requested_provider", "actual_provider", "model", "model_digest", "input_snapshot_json", "input_hash", "script_hash_at_start", "prompt_hash", "template_hash", "config_hash", "pipeline_version", "idempotency_key", "attempt", "repair_count", "fallback_count", "recovery_count", "fallback_used", "fallback_reason", "cancel_requested", "remote_interaction_id", "lease_owner", "lease_expires_at", "heartbeat_at", "error_code", "error_message", "metrics_json", "created_at", "started_at", "updated_at", "finished_at") SELECT "id", "project_id", "operation", "status", "stage", "progress", "requested_provider", "actual_provider", "model", "model_digest", "input_snapshot_json", "input_hash", "script_hash_at_start", "prompt_hash", "template_hash", "config_hash", "pipeline_version", "idempotency_key", "attempt", "repair_count", "fallback_count", "recovery_count", "fallback_used", "fallback_reason", "cancel_requested", "remote_interaction_id", "lease_owner", "lease_expires_at", "heartbeat_at", "error_code", "error_message", "metrics_json", "created_at", "started_at", "updated_at", "finished_at" FROM ai_generation_jobs;


CREATE TABLE ai_generation_checkpoints_v2 (
    id TEXT PRIMARY KEY,                    -- UUID
    job_id TEXT NOT NULL,
    section_index INTEGER NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,                   -- valid|invalid (a section that failed validation
                                             -- is still recorded, but never resumed from)
    input_hash TEXT NOT NULL,
    result_json TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES ai_generation_jobs_v2(id) ON DELETE CASCADE,
    UNIQUE (job_id, stage, section_index)
);
INSERT INTO ai_generation_checkpoints_v2 ("id", "job_id", "section_index", "stage", "status", "input_hash", "result_json", "metrics_json", "created_at", "updated_at") SELECT "id", "job_id", "section_index", "stage", "status", "input_hash", "result_json", "metrics_json", "created_at", "updated_at" FROM ai_generation_checkpoints;

-- Drop the old CHILD first: dropping the parent with foreign_keys enabled would cascade its checkpoints.
DROP TABLE ai_generation_checkpoints;
DROP TABLE ai_generation_jobs;
ALTER TABLE ai_generation_jobs_v2 RENAME TO ai_generation_jobs;
ALTER TABLE ai_generation_checkpoints_v2 RENAME TO ai_generation_checkpoints;


-- Exactly one active (pending|running|validating) job per project+operation.
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_jobs_one_active_per_project_operation
    ON ai_generation_jobs(project_id, operation)
    WHERE status IN ('pending', 'running', 'validating');


-- A duplicate create with the same idempotency key returns the existing row instead
-- of a second job, scoped per project+operation (not globally unique).
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_jobs_idempotency
    ON ai_generation_jobs(project_id, operation, idempotency_key);


-- Startup recovery scans non-terminal jobs ordered by last update.
CREATE INDEX IF NOT EXISTS idx_ai_jobs_status_updated
    ON ai_generation_jobs(status, updated_at);


CREATE INDEX IF NOT EXISTS idx_ai_checkpoints_job ON ai_generation_checkpoints(job_id);

CREATE TABLE project_explainer_assets (
  id TEXT NOT NULL,
  version INTEGER NOT NULL CHECK (version >= 1),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
  path TEXT NOT NULL,
  mime_type TEXT NOT NULL CHECK (mime_type = 'image/png'),
  width INTEGER NOT NULL CHECK (width > 0),
  height INTEGER NOT NULL CHECK (height > 0),
  original_filename TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  PRIMARY KEY (id, version)
);
CREATE INDEX idx_explainer_assets_project ON project_explainer_assets(project_id, created_at);
