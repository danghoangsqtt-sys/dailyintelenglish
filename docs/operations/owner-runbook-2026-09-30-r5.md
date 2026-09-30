# Owner-machine runbook r5 — Task 20.2e character spike v3 (anime model)

**Audience:** the executor agent on the owner's Windows PC (e.g. ChatGPT Codex desktop).
You are an **executor**, not a developer. The code was written and tested in the Claude
Code cloud session.

This run executes `scripts/spike_character_v3.py` on **Animagine XL 4.0** (an
anime-specialised SDXL, CreativeML Open RAIL++-M). It produces:
- two style presets (A `action_webtoon`, B `bright_anime`);
- a redesigned character;
- strict-pose M2 renders, composited two ways (blend vs render-then-cut);
- 1280×720 video-frame mockups.

The owner judges the sheets. Design: `.viepilot/phases/20-ai-visuals/tasks/task-20.2e.md`.

---

## 0. Hard rules (same as r4)

1. **Git-tracked files:** never modify, create or delete any, except adding new files
   under `owner-runs/20260930-r5/` in step D. **Never touch the 6 Gate B-12 MP4s.**
2. **If something fails**, do not fix code, do not change flags, and **do not retry**.
   Record the exact error and continue.
3. **Git:** only the commands written here.
   - Never run `stash`, `reset`, `clean`, `checkout -- <file>`, `rebase` or `merge`, and
     never force-push.
   - Your only push is the new branch `owner-runs/20260930-r5`.
4. **Environments:** **no installs at all in this run.** `venv-image\` already has
   everything. Never touch `venv\`, `venv-kokoro\` or `venv-styletts2\`, and never
   pip-install anything.
5. **Processes:** stop a process only when it is port 8000 held by this project's
   `uvicorn app.main` (check its CommandLine first). Never stop Ollama's server.
6. **Redirects:** use PowerShell from the repo root, with the `cmd /c "..."` redirect form
   exactly as written.
7. **Network is required.**
   - **New download ≈ 6.8 GB:** the Animagine XL 4.0 UNet + text encoders, into
     `models\image\` on the repo drive.
   - IP-Adapter, ControlNet OpenPose, anime-seg and the fp16-fix VAE are cached from
     r3/r4.
   - Do not abort a command that is still progressing.
8. **Facts only in RESULTS.md.** Leave "Owner decisions" empty.
9. **Packaging:** git ignores every folder named `logs/` and every `*.log` file. Logs go
   in `worker-logs\`, renamed to `.log.txt`.

## 1. Sync and preflight

The owner authorizes these 5 commands **before** you read anything else, because this
runbook exists only at the pinned commit. If you are on `owner-runs/20260930-r4`, that is
expected: `git switch` leaves it untouched.

```powershell
git fetch origin
git switch claude/admiring-knuth-r1d8vc
git pull --ff-only origin claude/admiring-knuth-r1d8vc
git rev-parse HEAD
git status --porcelain
```

- `HEAD` must equal the `PINNED_SHA` from the owner's prompt.
- `git status --porcelain` may show **only** these 6 lines. Anything else: STOP.
  ```
  ?? docs/operations/gate-b12-evidence/22484f26_ffmpeg.mp4
  ?? docs/operations/gate-b12-evidence/22484f26_remotion.mp4
  ?? docs/operations/gate-b12-evidence/b330d37f_ffmpeg.mp4
  ?? docs/operations/gate-b12-evidence/b330d37f_remotion.mp4
  ?? docs/operations/gate-b12-evidence/c08ce057_ffmpeg.mp4
  ?? docs/operations/gate-b12-evidence/c08ce057_remotion.mp4
  ```

```powershell
nvidia-smi --query-gpu=name,memory.used,memory.free,memory.total --format=csv
ollama list
Get-PSDrive (Get-Location).Drive.Name | Select-Object Name,Used,Free
Get-PSDrive C | Select-Object Name,Used,Free
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory
netstat -ano | findstr ":8000" | findstr "LISTENING"
New-Item -ItemType Directory -Force data\tmp\owner_runs_20260930_r5 | Out-Null
```

- The repo drive needs ≥ 12 GB free (the 6.8 GB download + outputs), and C: needs ≥ 3 GB.
- **Port 8000:** if something is listening, run
  `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,Name,CommandLine`.
  Stop it (`Stop-Process -Id <PID>`, wait 5 s, re-check) **only** if it is `python.exe`
  running `uvicorn app.main`. Otherwise STOP.

Keep the whole section-1 output in your notes; it becomes `preflight.txt`.

## 2. Environment check (no install)

```powershell
cmd /c "venv-image\Scripts\python -c ""import torch, diffusers, onnxruntime; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), diffusers.__version__, onnxruntime.__version__)"" > data\tmp\owner_runs_20260930_r5\L_env.txt 2>&1"
```

`L_env.txt` must show a CUDA version, `True`, `0.40.0` and `1.30.0`. Otherwise record it
and STOP (skip to step D).

## 3. Run the spike (one command, ~20–30 minutes plus the download)

Make the GPU idle first: run `ollama ps`, then `ollama stop <NAME>` for each model listed,
then `ollama ps` again; it must show none.

```powershell
cmd /c "venv\Scripts\python scripts\spike_character_v3.py --run-label r5 > data\tmp\owner_runs_20260930_r5\L_r5.json 2> data\tmp\owner_runs_20260930_r5\L_r5.err"
```

Expected: `phases.p1_style`, `p2_assets`, `p3_m2` and `p4_frames` each have **no
`"error"`** key, and `sheets` lists 4 PNGs.

A phase error is a valid result: record it; **do not rerun**.

## D. Package the evidence into `owner-runs\20260930-r5\` and push

The run folder is `data\tmp\phase20e_character_v3\run_r5\`.

```
owner-runs\20260930-r5\
  preflight.txt  RESULTS.md
  L_env.txt  L_r5.json  L_r5.err                (from data\tmp\owner_runs_20260930_r5\)
  sheets\    sheet_style.png  sheet_character.png  sheet_m2.png  sheet_frames.png
  full\      every *_scene_*.png (4), every *_candidate_1.png (2), every *_asset_*.png (8),
             every m2_*_cut.png (8), every frame_*.png (8)
             (NOT *_raw.png, *_seg.png or *_blend.png -- the blend versions are in sheet_m2)
  worker-logs\  every image_worker_lib_*_stderr.log from the run folder, renamed to .log.txt
```

- A missing file: leave it out and name it in RESULTS.md.
- Never add a file larger than 25 MB.

**RESULTS.md** (facts copied from `L_r5.json`; no opinions):

```markdown
# Owner-machine results r5 (Task 20.2e) 2026-09-30
- Pinned commit: <PINNED_SHA>
- Env: <L_env.txt line>
- Memory (preflight): TotalVisibleMemorySize / FreePhysicalMemory / FreeVirtualMemory
- base_repo / scheduler (from phases.p1_style.load): <base_repo> / <scheduler>
## Per phase (p1_style, p2_assets, p3_m2, p4_frames)
- wall_sec; error (verbatim or "none"); load.load_sec; load.download_or_cache_sec; lease (free_mb_before, evicted_models)
- per-image wall_time_sec: min / max; peak_vram_allocated_mb: max; peak_vram_reserved_mb: max
- p2 encode: per style -> wall_time_sec, items, with_ip, do_cfg
- p3 renders: each style/scene/action -> wall_time_sec, peak_vram_reserved_mb, segment.foreground_fraction, cut_sec
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Style A (action_webtoon) or B (bright_anime)? Looks like the anime you want?:
- Character OK now (design + identity across assets and actions)?:
- Halo gone (blend vs cut in sheet_m2)?:
- Frames OK?:
```

```powershell
git switch -c owner-runs/20260930-r5
git add owner-runs/20260930-r5
git status --porcelain
git commit -m "owner-runs r5: Task 20.2e character spike v3 evidence (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20260930-r5
git rev-parse HEAD
```

- The pre-commit `git status --porcelain` must show every packaged file as `A  owner-runs/20260930-r5/...`, including the `worker-logs/` files, plus the 6 MP4 lines. Anything else, or any packaged file missing from the list: STOP before committing.
- Never add the MP4s.

## Final report (print exactly this shape)

```
RUNBOOK r5 2026-09-30 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20260930-r5 @ <sha>   (or: NOT PUSHED -- <error>)
phases: p1_style <ok|error>, p2_assets <ok|error>, p3_m2 <ok|error>, p4_frames <ok|error>
untracked leftovers: <list or none>
next: owner looks at owner-runs/20260930-r5/sheets/*.png (and full/), then tells the Claude session the decisions.
```
