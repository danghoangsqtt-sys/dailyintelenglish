# Task 52.1 — BUG-046 ignore the voice preview cache

Status: implemented_verified 2026-10-19. `git check-ignore` matches `.gitignore:32`; `git status` clean of previews.

## Objective

Stop Phase 48 voice audition MP3s (`data/tts_preview/`, written by `backend/ai/tts/voice_preview_service.py`) from appearing as untracked files.

## Paths

- .gitignore
- .viepilot/requests/BUG-046.md

## File-Level Plan

- Add `data/tts_preview/` directly under `data/tts_cache/` in the "Data (runtime)" block.
- No files are deleted; existing previews stay on disk (they expire by TTL).

## Verification

`git status --short` no longer lists `data/tts_preview/`; `git check-ignore -v data/tts_preview/x.mp3` points to the new line.
