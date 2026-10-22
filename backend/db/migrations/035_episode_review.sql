-- Phase 67 (ENH-049): the owner's review of a made episode in the review studio -- '' (not reviewed), 'approved'
-- (ready to upload) or 'changes' (with a note).
ALTER TABLE channel_episodes ADD COLUMN review_status TEXT NOT NULL DEFAULT '';
ALTER TABLE channel_episodes ADD COLUMN review_note TEXT NOT NULL DEFAULT '';
