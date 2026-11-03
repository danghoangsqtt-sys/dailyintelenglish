# Phase 87 summary — Vietnamese VieNeu voice and the "Word roots, prefixes and suffixes" Short

Done 2026-11-03 on `owner-runs/20261001-r9` (not pushed, not installed). Decisions D125–D127.

## What changed

- **VieNeu voice** (87.1): `tts_engine = "vieneu"` runs VieNeu-TTS v3 Turbo in its own `.venv-vieneu` (CPU, set up by
  `scripts/setup_vieneu.ps1`) as a persistent worker; Whisper word timestamps of each take are aligned onto the script
  words, so karaoke and captions work as with Edge. Capitalised words are lowered for the engine (it spells them).
  Edge stays the voice of every other template and of the International audience.
- **Roots script** (87.2): one schema-checked word family (checked list of 32 roots, 20 prefixes, 20 suffixes) built
  into the sample video's beats — hook, "same root?", promise wheel, origin, the head, then for each word whole / split /
  example, a quiz and a follow line — in Vietnamese (Việt Nam / Cả hai) or English (Quốc tế). The narrator switches to
  VieNeu for Vietnamese narration. Academic Shorts may last up to three minutes (D126).
- **Roots scene** (87.3): cream paper, hand-lettered word with the family's part in brand green, "COM + PRESS" split,
  self-drawing yellow underline, handwriting meaning and breakdown, karaoke caption (Bangers + Patrick Hand, OFL).
- **Line art** (87.4): Qwen draws one line-art picture per word when the video is made (cached, kept in the Activity
  Library as `lineart`); without Qwen the word's Tabler line icons are drawn stroke by stroke.
- **UI** (87.5): Step 1 template card (1.5 / 2 / 2.5 min), Shorts batch kind with a silent preview, channel plan,
  automatic videos, Step 2 (no editor review; cards kept), Step 4 VieNeu voice picker, Vietnamese UI copy.

## Fixed on the way (real runs)

Setup: `-I` ignores PYTHONIOENCODING (UTF-8 pipes), Windows PowerShell 5.1 stderr under `Stop`, an interrupted venv,
ONNX Runtime refusing hub-cache symlinks. Script: an empty "-" part, base-word splits of suffix families, an empty
origin, skipped picture descriptions, the family's own part not marked, "-tion / -sion" not matched, Chinese characters
in a Vietnamese sentence.

## Real checks (sandbox from source, `D:\Videos\Kiểm tra Gốc từ 2026-11-03`)

`Gốc từ v3`: Gốc PRESS 82.2 s and Hậu tố -tion 122.6 s, 1080×1920, every word drawn, origin beats, Vietnamese voice
Ngọc Huyền. v1 / v2 kept for comparison. Details in [task 87.6](tasks/task-87.6.md).
