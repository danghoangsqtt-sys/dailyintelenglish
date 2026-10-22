-- Phase 63 (ENH-045): how a Solo series is shown -- 'presenter', 'vox', or a 9:16 Short ('news', 'blur'), so the
-- Channel plan (and the Phase 62 automatic production) can make VOX videos and Shorts too.
ALTER TABLE channel_series ADD COLUMN explainer_style TEXT NOT NULL DEFAULT 'presenter';
