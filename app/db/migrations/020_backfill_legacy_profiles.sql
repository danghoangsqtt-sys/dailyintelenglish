-- Phase 33 (Task 33.2 follow-up): characters made before profiles (Lina, Alex) get the Quick create fields from their
-- structured columns, so they read as ready profiles. Every value stays editable in the Profiles tab.
UPDATE characters
SET appearance = trim(hair || ', ' || eyes || CASE WHEN extra != '' THEN ', ' || extra ELSE '' END)
WHERE appearance = '' AND hair != '';

UPDATE characters
SET outfit = CASE
  WHEN top_item = bottom_item THEN top_color || ' ' || top_item
  ELSE top_color || ' ' || top_item || ' and ' || bottom_color || ' ' || bottom_item
END
WHERE outfit = '' AND top_item != '';

-- The projects of the owner's characters use the American voices; a different accent can be chosen per profile.
UPDATE characters SET default_accent = 'american' WHERE default_accent = '' AND hair != '';
UPDATE characters
SET default_voice_id = CASE gender WHEN 'male' THEN 'en-US-GuyNeural' ELSE 'en-US-JennyNeural' END
WHERE default_voice_id = '' AND default_accent = 'american';
