# Phase 87 — Vietnamese VieNeu voice and the "Word roots, prefixes and suffixes" Short (D125–D127, 2026-11-03)

Owner (2026-11-03): academic videos for Vietnamese learners on English word roots, prefixes and suffixes and on easy
grammar, narrated and explained in Vietnamese and English; two sample videos. Then: research VieNeu-TTS, sea-g2p,
vieneu-audio-studio and OmniVoice "for a more expressive Vietnamese voice". Sessions:
[brainstorm](../../../docs/brainstorm/session-2026-11-03-academic-roots-grammar.md),
[voice research](../../../docs/brainstorm/vietnamese-voice-research-2026-11-03.md).

## Decisions (owner, AskUserQuestion 2026-11-03)

- **D125 — Vietnamese voice for the academic templates only.** An exception to D5 (2026-10-22) for `roots` and `grammar`:
  one **VieNeu-TTS v3 Turbo** preset voice reads the whole line, Vietnamese explanation and English words/examples alike
  (bilingual model; the CPU trial read the English example correctly where Edge vi-VN failed). VieNeu runs locally in an
  isolated environment outside the app venv (Apache-2.0, ~0.5 GB model, CPU RTF ≈ 0.45). Edge stays the engine for every
  other template and for the International audience (English narration).
- **D126 — Academic Shorts up to 3 minutes** (aim 90–150 s) for `roots` and `grammar` only; every other Short stays
  ≤ 1 minute.
- **D127 — Brand colours** for the roots look: root in Daily Beyond English green, prefix/suffix in dark ink, yellow
  hand-drawn underline, cream paper. Inspired by the samples' structure, not their identity (fonts, colours, wording).
- Three phases: 87 (voice + roots Short), 88 (grammar Short), 89 (16:9 long versions + series).
- Defaults taken (owner did not change them): roots kinds = root, prefix, suffix + word family; line art = MIT line-icon
  SVG composition plus Qwen line art saved to the library with tag `lineart`.

## Tasks

1. **87.1 VieNeu engine (isolated worker)** — `tts_engine = "vieneu"` beside `edge_tts`. A setup script makes
   `.venv-vieneu` (Python 3.12, `vieneu==3.8.3`, `faster-whisper`) and downloads the pinned model revision; a one-shot
   worker synthesises one line with a preset voice and returns WAV + word timings. Timings come from faster-whisper word
   timestamps aligned to the script words (VieNeu has no WordBoundary), stored in the same word-timestamps file Edge uses,
   so karaoke and caption paging work unchanged. Text sent to the engine is lower-cased for Latin words in ALL CAPS
   (caps are spelled out letter by letter); fixed temperature for stability; readiness status and a clear error when the
   environment is missing. Preset list (25) in the voice settings, Vietnamese labels. Paths: `backend/ai/tts/vieneu_service.py`,
   `backend/ai/tts/vieneu_worker.py`, `backend/ai/tts/tts_service.py`, `backend/core/constants.py`, `backend/core/voice.py`,
   `backend/ai/tts/voice_catalog_service.py`, `scripts/setup_vieneu.ps1`, `.gitignore`, tests.
2. **87.2 `roots` template: data and script** — new Short style `roots` (Solo, voice-only, line-drawn): a word family
   `{kind, head, origin_lang, origin_form, head_meaning_vi/en, head_example_en/vi, words[{word, parts[{text, role,
   meaning_vi, meaning_en}], part_of_speech, ipa, meaning_vi, meaning_en, logic_vi, example_en, example_vi, picture}],
   quiz}`; prompt with the beat structure (hook "Bạn có biết?" → surprise "same root" → promise with the number → origin →
   bare root + example → per word: whole, split, example → quiz → follow line); a curated seed list of roots/prefixes/
   suffixes with checked origins (`backend/content/data/word_roots.json`); the fact check runs on origins and splits; an
   uncertain split is dropped. Narration Vietnamese with English words (audience Việt Nam / Cả hai) or all English
   (Quốc tế). D126 length limit for this style. Editable in Step 2. Paths: `backend/schemas/project.py`,
   `backend/schemas/learning.py` (or a new `word_family.py`), `backend/ai/prompts/script/roots.txt`,
   `backend/content/script_pipeline.py`, `backend/content/script_editor.py`, `backend/content/data/word_roots.json`, tests.
3. **87.3 `RootsScene` renderer** — cream paper, the whole word that splits into prefix + root (+ suffix) with a "+",
   hand-drawn yellow underline that draws itself, Vietnamese meaning in a handwriting font with Vietnamese glyphs
   (bundled OFL font), the one-line breakdown, the line-art picture revealed stroke by stroke, the example sentence with a
   small VI gloss, the root wheel for the promise, the "= ?" quiz card; one-phrase centred caption; Phase 80 short brand.
   Paths: `renderer/src/RootsScene.tsx`, `renderer/src/rootsMath.ts`, `renderer/src/Root.tsx`, `renderer/src/types.ts`,
   `renderer/src/sampleShort.ts`, `renderer/public/fonts/`, `backend/media/video_renderer_remotion.py`, vitest.
4. **87.4 Line-art pictures** — each word's `picture` is either a composition of bundled MIT line icons (`renderer/public/lineart/`,
   chosen by the plan from a fixed list) or a Qwen line-art drawing (prompt recipe: single-weight ink line, flat, cream
   paper, one accent colour, no faces, no text), kept in the library with tag `lineart` and reused. Paths:
   `backend/ai/image/recipes.py`, `backend/ai/image/pipelines.py`, `backend/library/`, `renderer/public/lineart/`, tests.
5. **87.5 UI wiring** — Step 1 Short templates, Shorts batch kind card (topic or a pasted list of roots → one Short per
   root), Channel plan, Automatic videos; voice settings show the VieNeu presets and the engine status; Vietnamese UI copy.
   Paths: `frontend/pages/step1_config.html`, `frontend/static/js/step1_config.js`, `shorts_batch.js`, `channel.js`,
   `automation.js`, `step2_script.js`, `i18n_vi.js`, `backend/channel/batch_service.py`, browser tests.
6. **87.6 Verify** — full pytest and vitest; build and install after the owner's go-ahead; set up VieNeu on this machine;
   make two `roots` Shorts (a root family like PRESS, a suffix family like -tion) into
   `D:\Videos\Kiểm tra Gốc từ 2026-11-xx`; check the transcript of every line (no skipped or spelled-out words),
   karaoke timing, splits, pictures, length ≤ 3 min, frames. Records.

Task cards are written in `tasks/` before each task starts (doc-first gate); 87.1 first.
