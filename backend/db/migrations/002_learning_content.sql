-- Daily Intel English Studio — Learning Content schema (Sprint 1.5A / Task 1.5)
--
-- Supersedes the `learning_content` table from 001_init.sql: that table was
-- never referenced by any code and used a different shape (collocations_json,
-- comprehension_questions_json, key_takeaways_json, no idioms/questions
-- split). Dropping it here rather than leaving a dead, confusingly similar
-- table name (`learning_content` vs `learning_contents`) alongside the real
-- one — PM-approved (FIX2C follow-up decision, 2026-09-10).
DROP TABLE IF EXISTS learning_content;

CREATE TABLE IF NOT EXISTS learning_contents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    vocabulary_json TEXT NOT NULL DEFAULT '[]',  -- JSON: [{word, part_of_speech, ipa, definition_en, definition_vi, example_sentence}]
    idioms_json TEXT NOT NULL DEFAULT '[]',       -- JSON: [{phrase, meaning_en, meaning_vi, example_sentence}]
    grammar_json TEXT NOT NULL DEFAULT '[]',      -- JSON: [{point, structure, explanation_en, explanation_vi, examples}]
    questions_json TEXT NOT NULL DEFAULT '[]',    -- JSON: [{question, options, correct_answer, explanation}]
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_contents_project_id ON learning_contents(project_id);
