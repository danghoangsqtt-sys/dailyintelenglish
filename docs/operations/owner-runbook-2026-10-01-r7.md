# Owner-machine runbook r7 — Task 20.2g quality-tuning spike v5

**Audience:** the executor agent on the owner's Windows PC (e.g. ChatGPT Codex desktop).
You are an **executor**, not a developer. The code was written and tested in the Claude
Code cloud session.

This run executes `scripts/spike_character_v5.py` on **SDXL base**, in the accepted r3
watercolor family. It produces:
- a redesigned male (4 candidates);
- clean references and expressions;
- pose-placed one-pass scenes (2 seeds each);
- a hand-repair pass;
- 1280×720 frames.

The owner judges the sheets. Design: `.viepilot/phases/20-ai-visuals/tasks/task-20.2g.md`.

---

## 0. Hard rules (same as r6)

1. **Git-tracked files:** never modify, create or delete any, except adding new files
   under `owner-runs/20261001-r7/` in step D. **Never touch the 6 Gate B-12 MP4s.**
2. **If something fails**, do not fix code, do not change flags, and **do not retry**.
   Record the exact error and continue.
3. **Git:** only the commands written here.
   - Never run `stash`, `reset`, `clean`, `checkout -- <file>`, `rebase` or `merge`, and
     never force-push.
   - Your only push is the new branch `owner-runs/20261001-r7`.
4. **Environments:** **no installs at all in this run.** `venv-image\` already has
   everything. Never touch `venv\`, `venv-kokoro\` or `venv-styletts2\`, and never
   pip-install anything.
5. **Processes:** stop a process only when it is port 8000 held by this project's
   `uvicorn app.main` (check its CommandLine first). Never stop Ollama's server.
6. **Redirects:** use PowerShell from the repo root, with the `cmd /c "..."` redirect form
   exactly as written.
7. **Network:** huggingface.co may be contacted for cache checks. **No new download is
   expected:** SDXL base, the fp16-fix VAE and the IP-Adapter are cached from r2–r4. Do
   not abort a command that is still progressing.
8. **Facts only in RESULTS.md.** Leave "Owner decisions" empty.
9. **Packaging:** git ignores every folder named `logs/` and every `*.log` file. Logs go
   in `worker-logs\`, renamed to `.log.txt`.

## 1. Sync and preflight

The owner authorizes these 5 commands **before** you read anything else, because this
runbook exists only at the pinned commit. If you are on `owner-runs/20260930-r6`, that is
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
New-Item -ItemType Directory -Force data\tmp\owner_runs_20261001_r7 | Out-Null
```

- The repo drive needs ≥ 5 GB free, and C: needs ≥ 3 GB.
- **Port 8000:** if something is listening, run
  `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,Name,CommandLine`.
  Stop it (`Stop-Process -Id <PID>`, wait 5 s, re-check) **only** if it is `python.exe`
  running `uvicorn app.main`. Otherwise STOP.

Keep the whole section-1 output in your notes; it becomes `preflight.txt`.

## 2. Environment check (no install)

```powershell
cmd /c "venv-image\Scripts\python -c ""import torch, diffusers, onnxruntime; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), diffusers.__version__, onnxruntime.__version__)"" > data\tmp\owner_runs_20261001_r7\L_env.txt 2>&1"
```

`L_env.txt` must show a CUDA version, `True`, `0.40.0` and `1.30.0`. Otherwise record it
and STOP (skip to step D).

## 3. Run the spike (one command, ~25–30 minutes)

Make the GPU idle first: run `ollama ps`, then `ollama stop <NAME>` for each model listed,
then `ollama ps` again; it must show none.

```powershell
cmd /c "venv\Scripts\python scripts\spike_character_v5.py --run-label r7 > data\tmp\owner_runs_20261001_r7\L_r7.json 2> data\tmp\owner_runs_20261001_r7\L_r7.err"
```

Expected: `phases.p1_candidates`, `p2_expressions_encode`, `p3_scenes`, `p4_hands` and
`p5_frames` each have **no `"error"`** key, and `sheets` lists 4 PNGs.

A phase error is a valid result: record it; **do not rerun**.

## D. Package the evidence into `owner-runs\20261001-r7\` and push

The run folder is `data\tmp\phase20g_character_v5\run_r7\`.

```
owner-runs\20261001-r7\
  preflight.txt  RESULTS.md
  L_env.txt  L_r7.json  L_r7.err                (from data\tmp\owner_runs_20261001_r7\)
  sheets\    sheet_candidates.png  sheet_expressions.png  sheet_hands.png  sheet_frames.png
  full\      every *_candidate_*.png (12), every frame_*.png (16)
  worker-logs\  every image_worker_lib_*_stderr.log from the run folder, renamed to .log.txt
```

- A missing file: leave it out and name it in RESULTS.md.
- Never add a file larger than 25 MB.

**RESULTS.md** (facts copied from `L_r7.json`; no opinions):

```markdown
# Owner-machine results r7 (Task 20.2g) 2026-10-01
- Pinned commit: <PINNED_SHA>
- Env: <L_env.txt line>
- Memory (preflight): TotalVisibleMemorySize / FreePhysicalMemory / FreeVirtualMemory
## Per phase (p1_candidates, p2_expressions_encode, p3_scenes, p4_hands, p5_frames)
- wall_sec; error (verbatim or "none"); load.load_sec; load.download_or_cache_sec; lease (free_mb_before, evicted_models)
- per-image wall_time_sec: min / max; peak_vram_allocated_mb: max; peak_vram_reserved_mb: max
- prompt_tokens: max over all images; prompt_truncated: count of images where it is true
- p4: number of hand repairs
## gpu_snapshots: label -> vram_used_mb / vram_free_mb
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Male candidate (1-4)? Attractive and expressive now?:
- Hands: raw vs repaired (sheet_hands) -- better?:
- Actions and left-side placement right?:
- Outfit stable?:
```

```powershell
git switch -c owner-runs/20261001-r7
git add owner-runs/20261001-r7
git status --porcelain
git commit -m "owner-runs r7: Task 20.2g quality-tuning spike v5 evidence (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20261001-r7
git rev-parse HEAD
```

- The pre-commit `git status --porcelain` must show every packaged file as `A  owner-runs/20261001-r7/...`, including the `worker-logs/` files, plus the 6 MP4 lines. Anything else, or any packaged file missing from the list: STOP before committing.
- Never add the MP4s.

## Final report (print exactly this shape)

```
RUNBOOK r7 2026-10-01 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20261001-r7 @ <sha>   (or: NOT PUSHED -- <error>)
phases: p1_candidates <ok|error>, p2_expressions_encode <ok|error>, p3_scenes <ok|error>, p4_hands <ok|error>, p5_frames <ok|error>
untracked leftovers: <list or none>
next: owner looks at owner-runs/20261001-r7/sheets/*.png (and full/), then tells the Claude session the decisions.
```
