-- Phase 13 -- durable AI generation jobs (additive; script/learning generation moves
-- from a synchronous request/response call to a persisted, resumable job).
-- See docs/implementation/phase-13-local-first-ai-reliability.md section 5.

CREATE TABLE IF NOT EXISTS ai_generation_jobs (
    id TEXT PRIMARY KEY,                    -- UUID
    project_id TEXT NOT NULL,
    operation TEXT NOT NULL,                -- script|learning
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
    CHECK (operation IN ('script', 'learning')),
    CHECK (status IN ('pending', 'running', 'validating', 'complete', 'error', 'cancelled', 'stale')),
    CHECK (progress >= 0 AND progress <= 100),
    CHECK (fallback_used IN (0, 1)),
    CHECK (cancel_requested IN (0, 1))
);

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

CREATE TABLE IF NOT EXISTS ai_generation_checkpoints (
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
    FOREIGN KEY (job_id) REFERENCES ai_generation_jobs(id) ON DELETE CASCADE,
    UNIQUE (job_id, stage, section_index)
);

CREATE INDEX IF NOT EXISTS idx_ai_checkpoints_job ON ai_generation_checkpoints(job_id);
