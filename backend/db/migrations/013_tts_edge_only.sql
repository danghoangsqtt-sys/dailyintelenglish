-- D56 (owner 2026-10-06): Edge TTS is the only voice engine. Data-only and additive: existing
-- speakers that still say 'omnivoice' (which always fell back to Edge) are relabelled.
UPDATE speakers SET tts_engine = 'edge_tts' WHERE tts_engine IS NOT 'edge_tts';
