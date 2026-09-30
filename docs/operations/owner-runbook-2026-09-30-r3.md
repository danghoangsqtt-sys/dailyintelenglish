# Owner-machine runbook r3 — Task 20.2b character-library spike

**Audience:** the executor agent on the owner's Windows PC (e.g. ChatGPT Codex desktop).
You are an **executor**, not a developer. The code was written and tested in the Claude
Code cloud session.

This run executes `scripts/spike_character_library.py`. It produces:
- a Ghibli-like style test;
- one character's 20-asset set;
- 4 pose-controlled actions;
- background-removed cut-outs;
- M1 collage and M2 render composites.

The owner judges the sheets. Design: `.viepilot/phases/20-ai-visuals/tasks/task-20.2b.md`.

---

## 0. Hard rules (same as r2)

1. **Git-tracked files:** never modify, create or delete any, except adding new files
   under `owner-runs/20260930-r3/` in step D. **Never touch the 6 Gate B-12 MP4s.**
2. **If something fails**, do not fix code, do not change flags, and **do not retry**.
   Record the exact error and continue.
3. **Git:** only the commands written here.
   - Never run `stash`, `reset`, `clean`, `checkout -- <file>`, `rebase` or `merge`, and
     never force-push.
   - Your only push is the new branch `owner-runs/20260930-r3`.
4. **Environments:** only `venv-image\` may be installed into, and only with step 2's one
   command. Never touch `venv\`, `venv-kokoro\` or `venv-styletts2\`, and never
   pip-install globally.
5. **Processes:** stop a process only when it is port 8000 held by this project's
   `uvicorn app.main` (check its CommandLine first). Never stop Ollama's server.
6. **Redirects:** use PowerShell from the repo root, with the `cmd /c "..."` redirect form
   exactly as written.
7. **Network is required** (PyPI, huggingface.co). New downloads are about 2.7 GB: the
   ControlNet OpenPose weights (2.5 GB) and anime-seg (176 MB). Do not abort a command
   that is still progressing.
8. **Facts only in RESULTS.md.** Leave "Owner decisions" empty.

## 1. Sync and preflight

The owner authorizes these 5 commands **before** you read anything else, because this
runbook exists only at the pinned commit:

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
New-Item -ItemType Directory -Force data\tmp\owner_runs_20260930_r3 | Out-Null
```

- The repo drive needs ≥ 12 GB free, and C: needs ≥ 5 GB.
- **Port 8000:** if something is listening, run
  `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,Name,CommandLine`.
  Stop it (`Stop-Process -Id <PID>`, wait 5 s, re-check) **only** if it is `python.exe`
  running `uvicorn app.main`. Otherwise STOP.

Keep the whole section-1 output in your notes; it becomes `preflight.txt`.

## 2. Update `venv-image` (adds `onnxruntime==1.30.0`)

```powershell
venv-image\Scripts\pip install --no-cache-dir -r requirements-image.txt
cmd /c "venv-image\Scripts\python -c ""import torch, onnxruntime; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), onnxruntime.__version__)"" > data\tmp\owner_runs_20260930_r3\L_env.txt 2>&1"
```

`L_env.txt` must show a CUDA version, `True` and `1.30.0`. Otherwise record it and STOP
(skip to step D).

## 3. Run the spike (one command, ~10–20 minutes plus downloads)

Make the GPU idle first: run `ollama ps`, then `ollama stop <NAME>` for each model listed,
then `ollama ps` again; it must show none.

```powershell
cmd /c "venv\Scripts\python scripts\spike_character_library.py --run-label r3 > data\tmp\owner_runs_20260930_r3\L_r3.json 2> data\tmp\owner_runs_20260930_r3\L_r3.err"
```

Expected: `phases.p1_style_lightning`, `p1_style_base`, `p2_assets`, `p3_actions`,
`p4_cutouts` and `p6_m2` each have **no `"error"`** key, and `sheets` lists 4 PNGs.

A phase error is a valid result: record it; **do not rerun**.

## D. Package the evidence into `owner-runs\20260930-r3\` and push

**Rename every `.log` to `.log.txt`** (git ignores `*.log`). The run folder is
`data\tmp\phase20b_character_spike\run_r3\`.

```
owner-runs\20260930-r3\
  preflight.txt  RESULTS.md
  L_env.txt  L_r3.json  L_r3.err                (from data\tmp\owner_runs_20260930_r3\)
  sheets\    sheet_style.png  sheet_character.png  sheet_actions.png  sheet_composites.png
  full\      scene_classroom_lightning.png  scene_kitchen_lightning.png
             scene_classroom_base.png  scene_kitchen_base.png
             portrait_lightning_1.png  portrait_base_1.png
             asset_front_happy.png  asset_three_quarter_left_neutral.png  asset_full_body_happy.png
             action_waving.png  action_pointing.png  action_thinking.png  action_cheering.png
             cut_action_waving.png  cut_action_pointing.png
             m1_classroom_naive.png  m1_classroom_integrated.png  m2_classroom.png
             m1_kitchen_naive.png  m1_kitchen_integrated.png  m2_kitchen.png
  worker-logs\  every image_worker_lib_*_stderr.log from the run folder, renamed to .log.txt
```

- **Erratum (after run r3):** the first version of this runbook said `logs\`. The
  repo `.gitignore` ignores every `logs/` folder, so `git add` silently skipped the logs
  and the executor correctly stopped. The folder is `worker-logs\`.

- A missing file: leave it out and name it in RESULTS.md.
- Never add a file larger than 25 MB.

**RESULTS.md** (facts copied from `L_r3.json`; no opinions):

```markdown
# Owner-machine results r3 (Task 20.2b) 2026-09-30
- Pinned commit: <PINNED_SHA>
- Env: <L_env.txt line>
- Memory (preflight): TotalVisibleMemorySize / FreePhysicalMemory / FreeVirtualMemory
## Per phase (p1_style_lightning, p1_style_base, p2_assets, p3_actions, p4_cutouts, p5_m1, p6_m2)
- wall_sec; error (verbatim or "none"); load.load_sec; lease (free_mb_before, evicted_models)
- per-image wall_time_sec: min / max; peak_vram_allocated_mb: max; peak_vram_reserved_mb: max
- p2 encode: wall_time_sec, items, with_ip
- p4 cut-outs: each input -> foreground_fraction, soft_edge_fraction
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Style: Ghibli-like enough? Lightning vs base?:
- Same character across views / expressions / actions?:
- Cut-out quality OK?:
- M1 naive vs M1 integrated vs M2: which looks natural (not stiff)?:
```

```powershell
git switch -c owner-runs/20260930-r3
git add owner-runs/20260930-r3
git status --porcelain
git commit -m "owner-runs r3: Task 20.2b character-library spike evidence (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20260930-r3
git rev-parse HEAD
```

The pre-commit `git status --porcelain` may show only `owner-runs/20260930-r3/` paths plus
the 6 MP4 lines. Never add the MP4s.

## Final report (print exactly this shape)

```
RUNBOOK r3 2026-09-30 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20260930-r3 @ <sha>   (or: NOT PUSHED -- <error>)
phases: p1_style_lightning <ok|error>, p1_style_base <ok|error>, p2_assets <ok|error>, p3_actions <ok|error>, p4_cutouts <ok|error>, p5_m1 <ok|error>, p6_m2 <ok|error>
untracked leftovers: <list or none>
next: owner looks at owner-runs/20260930-r3/sheets/*.png (and full/), then tells the Claude session the decisions.
```
