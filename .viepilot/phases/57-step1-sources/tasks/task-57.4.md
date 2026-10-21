# Task 57.4 — Read a photo with the cloud AI

Status: planned 2026-10-21.

## Paths
- backend/ai/llm/contracts.py (`GenerationRequest.images: list[str]` data URLs, default empty)
- backend/ai/llm/openai_compat_provider.py (content parts `text` + `image_url` when images are present)
- backend/ai/llm/ollama_provider.py (refuses image requests as a request error, never retried)
- backend/ai/prompts/source/read_image.txt, backend/content/source_service.py, backend/api/projects.py (`POST /api/projects/read-image`, multipart, kind dialogue|vocabulary)
- tests/test_read_image.py (new)

## File-Level Plan
Accept PNG/JPEG/WebP ≤ 8 MB, downscale to ≤ 1600 px, send as a JPEG data URL. Prompt: "Transcribe the English text in this picture exactly… return {"text": "..."}" with a dialogue variant ("one line per turn, 'Name: words'") and a vocabulary variant ("one word or phrase per line"). The result text is returned for the owner to edit; nothing is saved. Local mode / no vision → "Reading pictures needs a cloud AI with vision (Settings → AI)".

## Tests
Provider payload carries the image part; Ollama refuses; endpoint with a fake router returns the text; a non-image file is refused.
