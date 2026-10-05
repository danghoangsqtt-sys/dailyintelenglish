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
