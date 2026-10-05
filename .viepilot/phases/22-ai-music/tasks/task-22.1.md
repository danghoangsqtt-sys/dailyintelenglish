# Task 22.1 — Spike: ACE-Step 1.5 on the owner's RTX 3060 (doc-first card)

## Objective

Before any product code, measure these on the owner's machine:

- whether ACE-Step 1.5 installs and runs locally;
- its VRAM use and speed;
- whether it makes good **instrumental** beds for the three style families (D49);
- which length strategy the product should use (D47).

## Paths

- `requirements-music.txt` (new; isolated venv, like `requirements-image.txt`)
- `scripts/spike_music.py` (new; not shipped)
- `docs/operations/phase22-spike-music.md` (new report)
- `.gitignore` (`models/music/`, `venv-music/`)

## File-Level Plan

1. **Environment:**
   - create `venv-music` with the newest Python that ACE-Step 1.5's own requirements accept (try
     3.12, else 3.11), plus CUDA torch;
   - install the package from its official source (`ace-step/ACE-Step-1.5`) and pin the
     resolved versions in `requirements-music.txt`;
   - put the weights from `ACE-Step/Ace-Step1.5` (MIT, checked on the Hub 2026-10-05) in
     `models/music/`.
2. **spike_music.py:** for each family × strategy, generate audio and log wall time, peak VRAM
   (nvidia-smi + torch), sample rate and duration.
   - Families, all instrumental with no vocals:
     - lofi/chill: "lofi hip hop, mellow, soft keys, vinyl crackle";
     - acoustic/piano: "acoustic guitar and warm piano, gentle";
     - upbeat/corporate: "bright upbeat corporate, light percussion, ukulele".
   - Strategies:
     - (a) one 8-minute piece;
     - (b) one 150 s loopable piece, looped to 8 minutes with a 3 s crossfade.
   - For one family, also compare the 0.6B and 1.7B LMs to pick the default.
3. **Report** `docs/operations/phase22-spike-music.md`:
   - the measurement table;
   - the file list (WAV/MP3 under `owner-runs/music-spike/` for the owner to listen to);
   - observations;
   - licence notes.
4. **Owner actions:**
   - listen, then pick the strategy and the quality bar;
   - upload one track as an unlisted YouTube video and report whether Content ID claims it.

## Verification

- All 6 family × strategy outputs exist.
- The owner hears no vocals.
- VRAM stays under 8 GB.
- The time per 8-minute bed is reported.
- The owner verdict is recorded in this card and in PHASE-STATE.

## Results (Claude part done 2026-10-05; report `docs/operations/phase22-spike-music.md`)

- **Environment:**
  - Python 3.11 venv-music, built with uv from ACE-Step's own uv.lock (commit `ca1e85f`) and pinned in `requirements-music.txt`.
  - The Python 3.12 attempt was skipped: ACE-Step's lock targets 3.11.
- **All 6 family × strategy outputs exist, plus 4 LM-comparison files.** They are 48 kHz stereo at the exact requested length.
- **Time:** an 8-minute bed takes **~34 s** DiT-only. The 0.6B LM adds ~4 s and the 1.7B LM adds ~8 s.
- **VRAM:**
  - DiT-only peaks at 6.4–6.9 GB in torch and 7.4–8.4 GB on the whole card (incl. ~0.5 GB desktop).
  - So it is under 8 GB for 150 s, and up to 8.4 GB for a single 480 s piece.
  - 1.7B LM: 10.3 GB.
- **Deviations:**
  - The full-LM ("thinking") mode is not viable on 12 GB: ~6 min, then the VRAM preflight failed. The LM was tested in metadata-only mode instead.
  - Loudness varies −14.0 to −18.6 LUFS between files, so 22.4 must normalise each bed.
- The script grew a `--only-lm` option, used to rerun the 0.6B comparison after its separate download (1.3 GB).
- **Pending owner verdict:** length strategy, LM mode, no-vocals and quality bar, Content ID unlisted upload.

## Owner verdict 1 (2026-10-05): quality FAIL

- Owner: "nhạc quá tệ" (the music is too bad). It is messy, with a wandering rhythm, and worst in
  upbeat and acoustic.
- The owner chose "try higher quality" over switching models or pausing AI music.

## Amendment B: quality spike (doc-first, before any code change)

**Root causes found in ACE-Step 1.5's own docs (`docs/en/INFERENCE.md`), all misconfigurations on
our side:**

1. **Turbo needs `shift=3.0`.** The default 1.0 is applied as-is. Every run so far used 1.0.
2. **"Instrumental: 30–180 seconds works well."** The 8–10-minute single pieces are outside that
   range.
3. **"For best quality": the base or SFT model**, with `inference_steps` 64, `use_adg=True`,
   `guidance_scale` 7–9 and `shift=3.0`.
4. **Captions should be specific (genre + instruments).** BPM, key and time signature can be fixed
   when known.

**Variants:** each family, 150 s, the same seed, with a new specific caption that asks for a steady
groove and fixed metadata:

| Family | BPM | Key | Time signature |
|---|---|---|---|
| lofi | 80 | A minor | 4/4 |
| acoustic | 90 | G major | 4/4 |
| upbeat | 112 | C major | 4/4 |

- **B:** turbo, `shift=3`, fixed metadata.
- **C:** turbo, `shift=3`, LM 1.7B "thinking" (the LM writes the audio codes). This is measured
  at 150 s only, since 480 s failed.
- **D:** SFT (`acestep-v15-sft`, MIT, 4.79 GB, download approved by the owner's choice), 64 steps,
  CFG 7, ADG, `shift=3`, fixed metadata.
- **A:** the existing baseline files (turbo, `shift=1`, vague caption), for comparison.

Then the owner picks the best variant (or none), and the winner's 150 s piece is looped to 8
minutes with crossfades. The script is `scripts/spike_music_quality.py`; the output goes to
`data/tmp/music-spike/quality/`.

## Owner decision D50 (2026-10-05): stop AI music generation

- The quality spike (Amendment B) was **not run**: the owner stopped it before the first variant.
- Owner: "theo tôi lấy các nguồn nhạc từ các nguồn nhạc background miễn phí sẽ tốt hơn thay vì tốn
  tài nguyên cho tạo nhạc" (free background music sources are better than spending resources on
  generating music).
- Chosen:
  - **remove the AI music code completely** (Tasks 22.2 and 22.3 reverted);
  - get music by **manual download from free libraries**, with the licence recorded;
  - **delete `venv-music` and `models/music`**.
- Task 22.1 closes as **FAIL / superseded**. Phase 22 is re-scoped to a free-music library
  (licence + attribution metadata, YouTube credit line, ducking).
