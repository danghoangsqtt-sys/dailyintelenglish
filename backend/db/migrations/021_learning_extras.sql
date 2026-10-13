-- Task 36.1 (D95): collocations, phrasal verbs and sentence patterns in the learning pack.
ALTER TABLE learning_contents ADD COLUMN collocations_json TEXT NOT NULL DEFAULT '[]';   -- [{phrase, meaning_en, meaning_vi, example_sentence}]
ALTER TABLE learning_contents ADD COLUMN phrasal_verbs_json TEXT NOT NULL DEFAULT '[]';  -- same shape
ALTER TABLE learning_contents ADD COLUMN patterns_json TEXT NOT NULL DEFAULT '[]';       -- [{pattern, use_en, use_vi, example_sentence}]
