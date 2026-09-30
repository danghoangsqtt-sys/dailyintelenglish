# Owner-machine runbook r2 — 2026-09-30 retry (Task 21.1b + Task 20.2 image runs)

**Audience:** the executor agent on the owner's Windows PC (e.g. ChatGPT Codex desktop).
You are an **executor**, not a developer. The code was written in the Claude Code cloud
session. This retry exists because the first run (evidence branch
`owner-runs/20260930` @ `f08d59d`) passed steps A and C1b, but:

- **B failed:** `py -3.11 -m venv venv-styletts2` returned `[Errno 13] Permission denied`
  on `venv-styletts2\Scripts\python.exe`. Most likely `venv-styletts2\` already existed
  from the earlier local session and its `python.exe` was held by a leftover process.
- **C2 failed:** `lightning load failed: ... paging file is too small (os error 1455)`.
  This was a real bug in `scripts/image_worker.py`: it built the whole UNet in fp32 in
  RAM (~10.3 GB). It is now **fixed**; measured on a scaled model, peak RAM went from
  4186 MB to 745 MB with pixel-identical output. The runner also lost the `base` results
  that had already succeeded; it now keeps each candidate's partial results.
- The worker `.log` files were silently skipped by git (`*.log` is gitignored), and the
  D2 size command had a PowerShell syntax error. Both are fixed below.

**Do NOT redo** step A (tests: 1235 passed) or the C1b VRAM probe. Both already
succeeded and are on `owner-runs/20260930`.

---

## 0. Hard rules (unchanged in spirit from the first runbook, section 0)

1. **Do not change any git-tracked file.** If something fails, do not fix it; record it
   exactly and continue with the next independent step.
2. **Git:** only the commands written here.
   - Never run `stash`, `reset`, `clean`, `checkout -- <file>`, `rebase` or `merge`, and
     never force-push.
   - Never push to `claude/admiring-knuth-r1d8vc`, `main`, `owner-local/backup-20260930`
     or `owner-runs/20260930`. Your only push is the new branch `owner-runs/20260930-r2`.
3. **Environments:** only `venv-styletts2\` and `venv-image\` may be created or changed.
   Never touch `venv\` or `venv-kokoro\`, and never pip-install globally.
4. **Commands exactly as written.** The only extra is the single documented
   `--vae-tiling` rerun (C1).
5. **`data\app.db` is read-only for you.**
6. **PowerShell, from the repo root.** Every redirect uses the `cmd /c "..."` form as
   written.
7. **Network is required** (PyPI, download.pytorch.org, huggingface.co, github.com, Edge
   TTS). If it is blocked, stop and ask the owner.
8. **Do not abort a command that is still making progress.** Stop waiting only after 90
   minutes with no progress.
9. **Processes:**
   - Do not stop any process **except** where step R or B0 explicitly authorizes it, and
     only after the check written there.
   - Never stop Ollama's server.
10. **Facts only in the results.** The owner fills in the decisions.

## R. Sync and preflight (all must pass, otherwise STOP)

The owner gives you `PINNED_SHA` in the prompt.

```powershell
git fetch origin
git switch claude/admiring-knuth-r1d8vc
git pull --ff-only origin claude/admiring-knuth-r1d8vc
git rev-parse HEAD
git status --porcelain
```

- `HEAD` must equal `PINNED_SHA`.
- `git status --porcelain` may show **only** the 6 known untracked MP4 lines under
  `docs/operations/gate-b12-evidence/` (`22484f26_ffmpeg.mp4`, `22484f26_remotion.mp4`,
  `b330d37f_ffmpeg.mp4`, `b330d37f_remotion.mp4`, `c08ce057_ffmpeg.mp4`,
  `c08ce057_remotion.mp4`). Any other line: STOP.

```powershell
nvidia-smi --query-gpu=name,memory.used,memory.free,memory.total --format=csv
ollama list
Get-PSDrive (Get-Location).Drive.Name | Select-Object Name,Used,Free
Get-PSDrive C | Select-Object Name,Used,Free
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory
netstat -ano | findstr ":8000" | findstr "LISTENING"
```

- The repo drive needs ≥ 25 GB free, and C: needs ≥ 8 GB.
- The memory line is recorded only; it is needed to interpret any new paging error.
- **Port 8000:** if something is listening, run
  `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,Name,CommandLine`.
  - **Authorized:** if it is `python.exe` and its CommandLine contains `uvicorn app.main`
    (this project's app), run `Stop-Process -Id <PID>`, wait 5 seconds, and re-check that
    the port is free.
  - Anything else: STOP and report it.

Create the intermediate output folder (gitignored):

```powershell
New-Item -ItemType Directory -Force data\tmp\owner_runs_20260930_r2 | Out-Null
```

Keep the full output of section R in your notes. It becomes `preflight.txt` in step D.

---

## B. Task 21.1b — StyleTTS 2

### B0. Diagnose the existing `venv-styletts2\` (read-only first)

```powershell
Test-Path venv-styletts2\Scripts\python.exe
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like "*\venv-styletts2\*" } | Select-Object ProcessId,Name,ExecutablePath,CommandLine
```

- **If processes are listed:** they are authorized to stop **only if** every listed
  `ExecutablePath` is inside this repository's `venv-styletts2\`. That makes them leftover
  workers from an earlier run of this project. Run `Stop-Process -Id <PID>` for each, wait
  5 seconds, and re-run the query; it must list nothing. If any listed process is outside
  this repo, STOP step B and report it.
- **Then:**
  - **If `venv-styletts2\Scripts\python.exe` exists:** do **not** re-create the venv.
    Run `venv-styletts2\Scripts\python --version`.
    - If it prints 3.11.x, reuse the venv and go to B1 (skip its first line).
    - If it prints anything else, or fails, record that and **skip step B**.
  - **If it does not exist:** run the first line of B1 as well.

### B1. Environment

```powershell
py -3.11 -m venv venv-styletts2
venv-styletts2\Scripts\pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu128
venv-styletts2\Scripts\pip install --no-cache-dir -r requirements-styletts2.txt
cmd /c "venv-styletts2\Scripts\python -c ""import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"" > data\tmp\owner_runs_20260930_r2\B_env.txt 2>&1"
cmd /c "venv-styletts2\Scripts\pip freeze >> data\tmp\owner_runs_20260930_r2\B_env.txt 2>&1"
```

(The first line is skipped when B0 said the venv already exists.)

`B_env.txt`'s first line must show a CUDA version and `True`. Otherwise record it and skip
the rest of B.

### B2. Run 1: Ollama idle

Run `ollama ps`. For each model listed, run `ollama stop <NAME>`. Run `ollama ps` again; it
must list none. Then:

```powershell
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
cmd /c "venv\Scripts\python scripts\spike_styletts2.py > data\tmp\owner_runs_20260930_r2\B_run1_idle.json 2> data\tmp\owner_runs_20260930_r2\B_run1_idle.err"
Copy-Item data\tmp\phase21_styletts2_spike\styletts2_worker_stderr.log data\tmp\owner_runs_20260930_r2\B_run1_worker.log.txt
```

The first run downloads about 873 MB. Expected result:
- `worker_handshake.status` is `"ready"` with `"device": "cuda"`;
- 6 `styletts2` clips and 6 `edge_tts` clips, all `"status": "ok"`;
- `data\tmp\phase21_styletts2_spike\spike_comparison_styletts2.mp3` exists.

### B3. Run 2: qwen loaded (tests the free-VRAM policy)

```powershell
ollama run qwen3.5:9b "hi"
ollama ps
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
cmd /c "venv\Scripts\python scripts\spike_styletts2.py > data\tmp\owner_runs_20260930_r2\B_run2_qwen.json 2> data\tmp\owner_runs_20260930_r2\B_run2_qwen.err"
Copy-Item data\tmp\phase21_styletts2_spike\styletts2_worker_stderr.log data\tmp\owner_runs_20260930_r2\B_run2_worker.log.txt
```

Expected: the handshake says `"unavailable"` / `"insufficient_vram"`. That is the policy
working, not a failure. `"ready"` is also a valid result; record it as-is.

Save the `ollama ps` and `nvidia-smi` outputs from B2 and B3 to
`data\tmp\owner_runs_20260930_r2\B_gpu_states.txt`.

---

## C. Task 20.2 — images (also produces Task 20.1's eviction evidence)

`venv-image\` already exists and passed its CUDA check in the first run. **Do not
re-create it or re-install anything into it.** Check it once:

```powershell
cmd /c "venv-image\Scripts\python -c ""import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"" > data\tmp\owner_runs_20260930_r2\C_env.txt 2>&1"
```

It must show a CUDA version and `True`. Otherwise record it and skip C.

### C1. Run "idle2" (Ollama idle)

Stop resident models as in B2 (`ollama ps`, `ollama stop <NAME>` for each, then
`ollama ps` shows none). Then:

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label idle2 > data\tmp\owner_runs_20260930_r2\C_idle2.json 2> data\tmp\owner_runs_20260930_r2\C_idle2.err"
```

Expected:
- `candidates.base` and `candidates.lightning` each have 5 images and **no `"error"`
  key**;
- `load.watermark_active` is `false` for both;
- `ip_adapter.scenes` has 6 entries for each;
- `sheets.episodes` lists 5 PNGs.

**One retry only.** If a candidate has an `"error"` containing `OutOfMemoryError`,
`CUDA out of memory` or `os error 1455`, run this once and then continue:

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label idle2_vaetiling --vae-tiling > data\tmp\owner_runs_20260930_r2\C_idle2_vaetiling.json 2> data\tmp\owner_runs_20260930_r2\C_idle2_vaetiling.err"
```

### C2. Run "warm_qwen2" (forces a real qwen eviction: Task 20.1's evidence)

Do not stop Ollama models before this run.

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label warm_qwen2 --warm-qwen --skip-ip > data\tmp\owner_runs_20260930_r2\C_warm_qwen2.json 2> data\tmp\owner_runs_20260930_r2\C_warm_qwen2.err"
```

Expected:
- `qwen[0].ok` and `qwen[1].ok` are `true`;
- `candidates.base.lease.evicted_models` contains `qwen3.5:9b`.

---

## D. Package the evidence and commit to the NEW branch `owner-runs/20260930-r2`

### D1. Copy into `owner-runs\20260930-r2\`

Every `.log` file is renamed to `.log.txt`, because git ignores `*.log`.

```
owner-runs\20260930-r2\
  preflight.txt  RESULTS.md  sizes.txt
  B\  B_env.txt  B_gpu_states.txt  B_run1_idle.json  B_run1_idle.err  B_run2_qwen.json  B_run2_qwen.err
      B_run1_worker.log.txt  B_run2_worker.log.txt
      spike_comparison_styletts2.mp3              (from data\tmp\phase21_styletts2_spike\)
  C\  C_env.txt  C_idle2.json  C_idle2.err  C_warm_qwen2.json  C_warm_qwen2.err
      (C_idle2_vaetiling.json / .err only if that rerun happened)
      sheet_ep1.png ... sheet_ep5.png  sheet_ip_adapter.png   (from data\tmp\phase20_image_spike\run_idle2\, or run_idle2_vaetiling\ if the rerun happened)
      image_worker_base_stderr.log.txt  image_worker_lightning_stderr.log.txt   (same run folder, renamed)
```

- Everything except the mp3 and PNGs comes from `data\tmp\owner_runs_20260930_r2\`.
- Missing files: leave them out and name them in RESULTS.md.
- Never add a file larger than 25 MB.

### D2. Footprint (corrected command)

```powershell
$(foreach ($d in "venv-styletts2","venv-image","models\styletts2","models\image") { if (Test-Path $d) { $s = (Get-ChildItem $d -Recurse -File -Force | Measure-Object Length -Sum).Sum; "$d $s" } }) | Out-File -Encoding ascii owner-runs\20260930-r2\sizes.txt
```

### D3. RESULTS.md (facts copied verbatim; no opinions)

```markdown
# Owner-machine results r2 2026-09-30
- Pinned commit: <PINNED_SHA>
- Memory (from preflight): TotalVisibleMemorySize / FreePhysicalMemory / TotalVirtualMemorySize / FreeVirtualMemory
## B. Task 21.1b StyleTTS 2
- B0: venv existed <yes/no>; leftover processes stopped <list of PIDs or none>; python --version <...>
- env: <first line of B_env.txt>
- run1 handshake: <status / device / free_vram_mb>
- run1 clips ok: <n>/12; mp3 present: <yes/no>
- run1 per clip: engine, voice, line_index, duration_sec, wall_time_sec, rtf (styletts2 clips only)
- voice_picks + voice_measurements median_f0_hz: <copied>
- run2 handshake: <status / reason / free_vram_mb>
- errors: <verbatim or "none">
## C. Task 20.2 images (+ 20.1 evidence)
- env: <C_env.txt line>
- vae-tiling rerun: <yes/no>
- per candidate (base, lightning): load.load_sec, load.watermark_active, load.timestep_spacing, per-image wall_time_sec, peak_vram_allocated_mb, peak_vram_reserved_mb, rss_mb, error (if any)
- ip_adapter per candidate: load.vram_added_mb, load.load_sec, per-scene wall_time_sec + peak_vram_allocated_mb
- lease per candidate (idle2 and warm_qwen2): min_free_mb, free_mb_before, free_mb_after_eviction, evicted_models, waited_seconds, or "refused"
- qwen (warm_qwen2): warm wall_sec, reload_after_eviction wall_sec
- gpu_snapshots (warm_qwen2): label -> vram_used_mb / vram_free_mb
- errors: <verbatim or "none">
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- 21.1b StyleTTS 2 vs Edge TTS (spike_comparison_styletts2.mp3):
- 20.2 base vs lightning vs today's template (sheet_ep1..5.png):
- 20.2 same character across scenes? (sheet_ip_adapter.png):
```

### D4. Commit and push (new branch only)

```powershell
git switch -c owner-runs/20260930-r2
git add owner-runs/20260930-r2
git status --porcelain
git commit -m "owner-runs r2: 2026-09-30 retry evidence for 21.1b + 20.2 (+20.1 eviction) (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20260930-r2
git rev-parse HEAD
```

The `git status --porcelain` before the commit may show only paths under
`owner-runs/20260930-r2/` plus the 6 known MP4 lines. Never add those MP4s.

## Final report (print exactly this shape)

```
RUNBOOK r2 2026-09-30 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20260930-r2 @ <sha>   (or: NOT PUSHED -- <error>)
B 21.1b: B0 <venv existed yes/no, processes stopped>, run1 <ok|failed: reason>, run2 <handshake status>
C 20.2: idle2 <ok|partial|failed: reason>, vae-tiling rerun <yes|no>, warm_qwen2 <ok|failed: reason>
untracked leftovers: <list or none>
next: owner listens to owner-runs/20260930-r2/B/spike_comparison_styletts2.mp3, looks at owner-runs/20260930-r2/C/sheet_*.png, then tells the Claude session the decisions.
```
