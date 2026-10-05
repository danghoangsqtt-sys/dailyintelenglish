# Phase 22 spike — ACE-Step 1.5 on the RTX 3060 12 GB (Task 22.1)

> **Outcome (2026-10-05): FAIL by the owner's ears ("nhạc quá tệ"); superseded by D50** (free music
> libraries).
>
> - ACE-Step's docs later showed two misconfigurations in these runs:
>   - turbo needs `shift=3.0`, but these runs used 1.0;
>   - instrumentals work best at 30–180 s, but these runs were 8-minute single pieces.
> - The follow-up quality spike was stopped by the owner, so it is unknown whether a correct
>   configuration would pass.
> - The environment, the weights and the code were removed.

**Date:** 2026-10-05
**Script:** `scripts/spike_music.py`, run in `venv-music`, pinned in `requirements-music.txt`
**Model:** ACE-Step 1.5 at commit `ca1e85f`, DiT `acestep-v15-turbo`, planner LMs `acestep-5Hz-lm-1.7B` and `acestep-5Hz-lm-0.6B`

## Verdict so far (Claude)

ACE-Step 1.5 runs locally and fast enough for the product: an 8-minute, 48 kHz stereo bed takes about 34 s. The owner still has to listen before the remaining choices are made (see below).

## Measurements

- Every run was 48 kHz stereo, seed 7, and gave the exact requested length.
- "VRAM (smi)" is the whole-GPU `nvidia-smi` peak. The idle desktop baseline is about 0.5 GB.
- "Loudness" is integrated EBU R128 loudness.

| File | LM | Length | Wall time | torch peak | VRAM (smi) | Loudness |
|---|---|---|---|---|---|---|
| lofi_full_480s | none | 480 s | 34.0 s | 6.8 GB | 7.9 GB | −14.9 LUFS |
| lofi_loopsrc_150s | none | 150 s | 10.8 s | 6.4 GB | 7.4 GB | −17.9 LUFS |
| acoustic_full_480s | none | 480 s | 33.4 s | 6.9 GB | 8.4 GB | −14.0 LUFS |
| acoustic_loopsrc_150s | none | 150 s | 10.6 s | 6.4 GB | 7.4 GB | −17.4 LUFS |
| upbeat_full_480s | none | 480 s | 33.6 s | 6.9 GB | 8.1 GB | −17.7 LUFS |
| upbeat_loopsrc_150s | none | 150 s | 10.6 s | 6.4 GB | 7.4 GB | −18.6 LUFS |
| lofi_150s_lm17 | 1.7B (metadata) | 150 s | 19.3 s | 9.4 GB | 10.1 GB | −16.0 LUFS |
| lofi_480s_lm17 | 1.7B (metadata) | 480 s | 41.6 s | 9.6 GB | 10.3 GB | −16.1 LUFS |
| lofi_150s_lm06 | 0.6B (metadata) | 150 s | 15.7 s | 7.2 GB | 7.8 GB | −18.3 LUFS |
| lofi_480s_lm06 | 0.6B (metadata) | 480 s | 38.1 s | 7.3 GB | 8.4 GB | −17.8 LUFS |

Notes on the table:

- Loading the DiT takes 5.5 s.
- Each `*_looped_480s` file is its 150 s source looped to 480 s with 3 s equal-power crossfades.
  - Making it takes under 1 s on the CPU.
  - Its loudness is within 0.1–0.3 LU of its source.

## Observations

1. **Speed is not a constraint.**
   - One full 8-minute bed takes about 34 s.
   - Three 150 s previews for the pick step (22.3) take about 32 s together.
2. **VRAM:**
   - DiT-only runs peak at 6.4–6.9 GB in torch and 7.4–8.4 GB on the whole card.
     - The card's 7.4–8.4 GB includes about 0.5 GB of desktop use.
     - The 480 s runs therefore sit slightly above the card's 8 GB target.
     - The 150 s runs sit below it.
   - Either way it fits the 12 GB card. Like the image worker, it must run alone under the GPU lease.
3. **Full LM planning is not viable on this card.**
   - In the first run, the default "thinking" mode (the LM writes the audio codes) took about 6 minutes for 480 s.
   - It then failed ACE-Step's own VRAM preflight before decoding: 2.24 GB free, 2.9 GB needed.
   - **Metadata-only LM mode does work.** In this mode the LM fills BPM, key and a rewritten caption, and the DiT makes the audio.
     - 1.7B: about +8 s per run, 10.3 GB peak.
     - 0.6B: about +4–5 s per run, 8.4 GB peak.
4. **Loudness varies by about 4.6 LU between files.**
   - The range is −14.0 to −18.6 LUFS.
   - The product must normalise each bed (for example to −20 LUFS before ducking) and must not trust the raw level. This feeds Task 22.4.
5. **Vocals:**
   - All runs used `lyrics="[Instrumental]"` with `instrumental=True`.
   - No automatic vocal check was made. The owner's listen is the check.

## Files to listen to

Folder: `data/tmp/music-spike/` (ignored by git; the WAV files are about 184 MB each, so listen to the MP3 copies).

- **Length strategy, per family:**
  - `{family}_full_480s.mp3`: one 8-minute piece;
  - `{family}_looped_480s.mp3`: a 150 s piece looped. Listen for the seam about every 147 s.
- **LM choice (lofi only):**
  - `lofi_full_480s.mp3`: no LM;
  - `lofi_480s_lm06.mp3`: 0.6B LM;
  - `lofi_480s_lm17.mp3`: 1.7B LM.

## Licence

- ACE-Step 1.5 code and weights are MIT. This was checked on 2026-10-05 in the repo `LICENSE` and in the `license: mit` front matter of both the checkpoints README and the 0.6B LM card. Commercial use is allowed.
- The checkpoints README says the training data includes "Professionally licensed music tracks".
- The bundled text encoder is Qwen3-Embedding-0.6B. Upstream it is Apache-2.0, but the bundled copy carries no licence file.
- The Content ID question is still open (the owner's unlisted upload, below).

## Claude's recommendation (pending the owner's ears)

1. **Default: DiT-only.** It is the fastest and uses the least VRAM. The LM is only worth adding if the owner hears a clear quality gain.
2. **If the owner hears no difference:**
   - generate the full length directly. The time cost is small and there is no seam.
   - keep looping as the fallback for videos longer than ACE-Step's 600 s limit.
3. **Normalise loudness** in 22.4.

## Owner actions (Task 22.1 stays `in_progress` until these are recorded)

1. Listen to the full and looped versions of each family. Pick the length strategy, or say "no difference".
2. Listen to the three lofi LM files. Pick none, 0.6B or 1.7B.
3. Confirm no vocals in any file, and set the quality bar ("good enough for the channel?").
4. Upload one MP3, for example `acoustic_full_480s.mp3` over a still image, as an **unlisted** YouTube video. Report whether Content ID claims it within 24 h.
