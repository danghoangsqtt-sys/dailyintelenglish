# Phase 22 — AI background music (ENH-016) — controlling plan

> **Re-scope D50 (2026-10-05, owner):** the ACE-Step 1.5 output failed the owner's listening test
> ("nhạc quá tệ": messy, wandering rhythm, worst in upbeat and acoustic). The owner chose free music
> libraries over spending resources on generation. The quality spike (turbo `shift=3`, LM thinking,
> SFT 64 steps) was planned but stopped before it ran. Tasks 22.2/22.3 were reverted, and
> `venv-music` and `models/music` were deleted.
>
> **Remaining scope:**
> - **22.7:** licence metadata on library tracks (source site, title, artist, licence,
>   attribution text, source URL), plus a short guide to safe free sources:
>   - YouTube Audio Library;
>   - Pixabay Music;
>   - Mixkit;
>   - Incompetech (CC BY 4.0);
>   - Free Music Archive CC0/CC-BY.
>
>   These sites have no public music API, and their terms forbid automated downloading, so
>   downloads stay manual.
> - **22.5:** YouTube description credit line from the episode's music.
> - **22.4:** speech-aware ducking.
> - **22.6:** Gate B-17.
>
> The sections below are the original D43–D49 plan, kept for history.

## Smart music (D51, owner 2026-10-06)

**Owner request (verbatim intent).** Delete the old AI tracks so the owner can add new ones. The
system then:

- **auto-selects a track by topic and track length**;
- **fits the start and end of the music to the video length**;
- **sets the music volume so it never covers the voice**;
- **fades the sound out at the end of the video**.

The AI tracks were deleted on 2026-10-06 (`data/tmp/music-spike`, 1.8 GB). `data/music_library` is
empty and ready.

**What the code does today (read 2026-10-06):**

- **Audio mix.** `audio_service._mix_project_sync` overlays the music on the speech span only. It
  loops by hard cut (`_loop_to_length`) and caps the music at a flat −18 dBFS ceiling. There is no
  speech-aware ducking and no fades.
- **Enhanced video** = intro 2.5 s + speech mix + outro 5 s (`Episode.tsx`, `types.ts`). The intro
  and outro are **silent**.
- **Standard video** = the speech mix only (`-t audio_duration`).
- **The chosen track** is stored per audio job (`audio_jobs.background_music`).

**Design:**

1. **Library metadata (22.7).** Each library file gets a row with the fields below. A short guide
   to safe free sources goes in `docs/user/free-music-sources.md`. Downloads stay manual: the sites
   have no public music API, and their terms forbid automated downloading.

   | Field | Notes |
   |---|---|
   | title | |
   | artist | |
   | source site | |
   | licence | |
   | attribution text | |
   | source URL | |
   | **mood** | one of `lofi`, `acoustic`, `upbeat`, `calm`, `inspiring` |
   | **tags** | free words |
   | **measured duration** | ffprobe |

2. **Smart bed (22.4).** This is one pure numpy module (`music_bed.py`) used in two places.
   - **Fit.** The bed always starts at the track's own start.
     - If the track is longer than needed, it is cut and then faded out.
     - If it is shorter, it is looped with 3 s equal-power crossfades. There is no hard cut.
   - **Level.** The track is loudness-normalised first (EBU R128), so every file starts from the
     same level. The bed then has two gain states:
     - **open** (intro, outro and pauses ≥ 2.5 s);
     - **under speech** (well below the voice).

     Ramps ease in 0.3 s before a line and release 0.8 s after it. Short gaps between lines stay
     ducked, so the music does not pump.
   - **Fades.** 2 s fade-in from the first frame. A 4 s fade-out that ends **exactly at the last
     frame of the video**.
   - **Where it is used:**
     - **Step 4 mix:** the speech span only, as the preview/podcast. Durations and timestamps are
       unchanged.
     - **Video render:** a **full-video soundtrack**: intro + voice + outro for Enhanced, and voice
       + a 4 s music tail for Standard. It is built from a voice-only stem that Step 4 now also
       writes. Remotion plays the soundtrack from frame 0, and ffmpeg uses it as the audio input.
   - **No music selected** = exactly today's behaviour on both renderers.
3. **Auto-select (22.8).** Step 4's music dropdown gains **"✨ Auto (best match)"**.
   - **Candidates.** The deterministic score uses:
     - the genre→mood map;
     - topic words against the tags and title;
     - the length fit: covering the video beats looping, and the fewest loops is best;
     - a small penalty for a track used by the last episodes.
   - **The AI** (cloud-first gateway) picks among the top candidates from the topic. It is
     validated against the candidate list, with one repair, else the top score.
   - **The reason is shown.** The pick is resolved at mix time and stored as the job's
     `background_music`, so the video and the credit line use the real file.

**Task order:** 22.7 → 22.4 → 22.8 → 22.5 (credit line) → 22.6 (Gate B-17).

**Status:** planned 2026-10-05 (`/vp-evolve`, Add Feature, complexity L) from the brainstorm
`docs/brainstorm/session-2026-10-05.md` (owner decisions D43–D49).
**Version:** enters at 1.2.0-beta. It closes at **1.3.0-beta** if Gate B-17 passes (MINOR: a new
user-visible feature; uploaded tracks keep working).

## 0. Owner decisions

| ID | Decision |
|---|---|
| D43 | ACE-Step 1.5 (MIT; commercial use stated; licensed/royalty-free training data; <4 GB VRAM), local, in its own venv and subprocess worker under the Task 20.1 GPU lease |
| D44 | One instrumental bed per episode + intro/outro emphasis |
| D45 | The AI writes a music brief, the owner edits it, 3 previews are made, the owner picks one, then the full-length track is generated |
| D46 | Tracks go into the Music Library with a provenance record; YouTube description music credit |
| D47 | The spike decides between full-length generation and a loop with crossfades (owner listens) |
| D48 | Speech-aware ducking from line timestamps |
| D49 | Style families: lofi/chill, acoustic/piano warm, upbeat/corporate bright |

## 1. Architecture (fits the existing pattern)

- **`venv-music/`**, isolated like `venv-image/`: never in `requirements.txt`, never bundled in the
  .exe, and the worker process exit returns all VRAM.
- **`scripts/music_worker.py`:** the same line-delimited JSON protocol as `image_worker.py`
  (handshake / load / generate / unload / stats).
- **`app/services/music/`:**
  - an engine with a worker and a deterministic fake for tests;
  - a background job runner, reusing the visuals job pattern;
  - a brief writer that goes through the AI gateway.
- **Data:** an additive migration `music_tracks` with these columns:
  - id, filename, source (upload | ai), style family, brief/prompt, seed, duration, model,
    licence, app version, created at.

  Uploaded files stay as they are; the table is only provenance + listing metadata.
- **Mix:** `audio_service` gains a timestamp-driven gain envelope (D48). Remotion intro/outro get
  the music at a fuller level. The −16 LUFS master target is unchanged.

## 2. Tasks

| Task | What | Accept when |
|---|---|---|
| 22.1 | **Spike** (GPU): install ACE-Step 1.5 in `venv-music`; measure VRAM, speed and quality for the 3 style families × 2 length strategies; the owner listens. The owner also uploads one track unlisted to YouTube to check Content ID | owner picks the length strategy and confirms the quality bar; VRAM < 8 GB, leaving headroom for the lease |
| 22.2 | Music worker + engine + jobs + `music_tracks` migration + Library UI v2 (source, provenance, standalone "Generate from a brief") | tests green; a real generation lands in the library with provenance |
| 22.3 | AI music brief (gateway, validated, genre→family fallback); Step 4 "AI music" card: edit the brief → 3 previews → pick → full-length → attach to the project | tests green; real run on 1 project |
| 22.4 | Speech-aware ducking + intro/outro levels (ffmpeg and Remotion) | LUFS within ±1 dB; envelope unit-tested; real mix listened to |
| 22.5 | YouTube description credit line + provenance export | tests green |
| 22.6 | **Gate B-17**: owner listening test on 3 real episodes (one per family) | owner PASS → 1.3.0-beta, tag `die-vp-p22-complete` |

## 3. Risks

- **Python/torch compatibility** of ACE-Step 1.5 on Windows. The spike pins a working set, as
  Task 20.2 did.
- **Long-form stability vs loop seams** (D47). The spike measures both.
- **Content ID on AI music.** This is empirical (owner upload in 22.1). The provenance record is
  the fallback for disputes.
- **Download size.** The DiT + LM + VAE are likely several GB, cached under `models/music/`, which
  is gitignored like `models/image/`.
