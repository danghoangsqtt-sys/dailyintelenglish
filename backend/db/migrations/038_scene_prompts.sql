-- Keep the owner's request and reusable image prompt alongside scene metadata.
ALTER TABLE scenes ADD COLUMN source_request TEXT NOT NULL DEFAULT '';
ALTER TABLE scenes ADD COLUMN image_prompt TEXT NOT NULL DEFAULT '';
