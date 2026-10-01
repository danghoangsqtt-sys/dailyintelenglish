# Owner-machine runbook r9 — Phase 20 AI Visuals verification (review r1 fixes) + Gate B-14 part 1

**Audience:** the executor agent on the owner's Windows PC (e.g. ChatGPT Codex desktop).
- You are an **executor and checker**, not a developer. **You never edit code.**
- The code was written and fixed in the Claude Code cloud session (Tasks 20.3–20.8, plus the
  review r1 fixes F1–F5 in `.viepilot/phases/20-ai-visuals/review-r1-tasks-20.3-20.8.md`).

This run does two things:
1. **Verifies the code on the real machine:**
   - full pytest;
   - TypeScript and vitest;
   - the fake end-to-end smoke.
2. **Gate B-14 part 1:**
   - two real-GPU smoke runs at the **same seed**, one with the duo regional refine **on** and
     one with it **off**;
   - every raw/final shot kept;
   - a visual checklist filled in by you;
   - the evidence pushed for the owner and the PM.

Part 2 (real episodes in the owner's own library) is a later runbook, after the owner reads
this evidence.

---

## 0. Hard rules

1. **Git-tracked files:** never modify, create or delete any, except adding new files under
   `owner-runs/20261001-r9/` in step D. **Never touch the 6 Gate B-12 MP4s.**
2. **If something fails**, do not fix code, do not change flags, and **do not retry**, except
   where a step says so. Record the exact error and continue with the next step.
3. **Git:** only the commands written here.
   - Never run `stash`, `reset`, `clean`, `checkout -- <file>`, `rebase` or `merge`, and never
     force-push.
   - Your only push is the new branch `owner-runs/20261001-r9`.
4. **Environments:** **no installs at all.**
   - Never pip-install or npm-install anything.
   - Never touch `venv-kokoro\` or `venv-styletts2\`.
5. **Processes:** stop a process only when it is port 8000 held by this project's
   `uvicorn app.main` (check its CommandLine first). Never stop Ollama's server (stopping
   loaded *models* with `ollama stop` is fine).
6. **Redirects:** use PowerShell from the repo root, with the `cmd /c "..."` redirect form
   exactly as written.
7. **Network:** huggingface.co may be contacted for cache checks; no new download is expected.
   Do not abort a command that is still progressing.
8. **Facts only in RESULTS.md**, plus the visual checklist in step 5 (observations, not
   opinions). Leave "Owner decisions" empty.
9. **Packaging:** git ignores every `logs/` folder and every `*.log` file. Logs go in
   `worker-logs\`, renamed to `.log.txt`.

## 1. Sync and preflight

The owner authorizes these 5 commands **before** you read anything else, because this runbook
exists only at the pinned commit.
- If you are on `feature/phase20-ai-visuals` or an `owner-runs/*` branch, that is expected:
  `git switch` leaves it untouched.

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
netstat -ano | findstr ":8000" | findstr "LISTENING"
New-Item -ItemType Directory -Force data\tmp\owner_runs_20261001_r9 | Out-Null
```

- **Disk:** the repo drive needs ≥ 8 GB free, and C: needs ≥ 3 GB.
- **Port 8000:** if something is listening, run
  `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,Name,CommandLine`.
  - Stop it (`Stop-Process -Id <PID>`, wait 5 s, re-check) **only** if it is `python.exe`
    running `uvicorn app.main`.
  - Otherwise: STOP.

Keep the whole section-1 output in your notes; it becomes `preflight.txt`.

## 2. Environment check (no install)

```powershell
cmd /c "venv\Scripts\python --version > data\tmp\owner_runs_20261001_r9\L_env.txt 2>&1"
cmd /c "venv-image\Scripts\python -c ""import torch, diffusers; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), diffusers.__version__)"" >> data\tmp\owner_runs_20261001_r9\L_env.txt 2>&1"
cmd /c "node --version >> data\tmp\owner_runs_20261001_r9\L_env.txt 2>&1"
```

`L_env.txt` must show:
- a Python 3 version;
- a CUDA version, `True` and `0.40.0`;
- a Node version ≥ 18.

If not, record it and skip to step D.

## 3. Automated checks (about 12 minutes)

Run each line once, in order. A non-zero result is a valid result: record it and continue.

```powershell
cmd /c "venv\Scripts\python -m pytest -q > data\tmp\owner_runs_20261001_r9\L_pytest.txt 2>&1"
cmd /c "venv\Scripts\python -m ruff check app tests scripts\smoke_ai_visuals.py > data\tmp\owner_runs_20261001_r9\L_ruff.txt 2>&1"
cmd /c "cd video-renderer && npx tsc --noEmit > ..\data\tmp\owner_runs_20261001_r9\L_tsc.txt 2>&1"
cmd /c "cd video-renderer && npx vitest run > ..\data\tmp\owner_runs_20261001_r9\L_vitest.txt 2>&1"
cmd /c "venv\Scripts\python scripts\smoke_ai_visuals.py --fake > data\tmp\owner_runs_20261001_r9\L_smoke_fake.txt 2>&1"
```

**Expected:**
- **pytest:** the last line says `passed` with **0 failed** (the cloud baseline is 1271+ tests).
- **ruff:** `All checks passed!`. If `No module named ruff`, record "ruff not available".
- **tsc:** empty output.
- **vitest:** `Tests  39 passed (39)`.
- **fake smoke:** a JSON block with `"shot_count": 8`.

## 4. Real GPU smoke: duo refine ON vs OFF at the same seed (about 30–40 minutes)

Make the GPU idle first:
1. Run `ollama ps`.
2. Run `ollama stop <NAME>` for each model listed.
3. Run `ollama ps` again; it must show none.

Then run the two commands, one after the other:

```powershell
cmd /c "venv\Scripts\python scripts\smoke_ai_visuals.py --output-dir data\tmp\gate-b14-r9\refine_on --duo-refine on --seed 20261001 > data\tmp\owner_runs_20261001_r9\L_smoke_on.txt 2>&1"
cmd /c "venv\Scripts\python scripts\smoke_ai_visuals.py --output-dir data\tmp\gate-b14-r9\refine_off --duo-refine off --seed 20261001 > data\tmp\owner_runs_20261001_r9\L_smoke_off.txt 2>&1"
```

- **Pass:** each ends with a JSON block containing `"shot_count": 8`, `"duo_refine": true`
  (`false` for the second) and an `"output_dir"`.
- **Output:** each run writes one subfolder `data\tmp\gate-b14-r9\refine_<on|off>\<stamp>-<id>\`
  containing:
  - `single.png`, `duo_close.png`, `duo_wide.png` (Remotion stills with captions);
  - `contact_shots.png` (each shot: raw | final);
  - `shots\` (16 PNGs: raw and final for 8 shots);
  - `characters\Lan\…` and `characters\Minh\…` (candidates, face, sheet).
- **Worker logs:** each run's temporary data folder is deleted at exit, so its worker logs
  survive only inside the console output. Keep the `L_smoke_*.txt` files.
- **A failure** is a valid result: record its last 30 lines, do not rerun, and continue.

## 5. Visual checklist (you look at the images; observations only)

Open `contact_shots.png` of **each** run, and the 3 stills of each run.

The characters, from the smoke script:
- **Lan:** a female student, long black hair, **yellow sweater, navy blue jeans**.
- **Minh:** a male student, short neat black hair, **light blue slim-fit shirt, black slim
  trousers**.

Each run has 8 shots in 2 scenes: Classroom and Cafe, 4 each (Lan single, Minh single,
`duo_close`, `duo_wide`).

Fill this table for **both runs**, one row per shot, raw and final columns separately. Write
only what you see:

| run | shot label | variant | people visible (count) | Lan top yellow? | Lan bottom navy? | Minh top light blue? | Minh bottom black? | extra person? | hands visibly malformed? (count) | notes (≤ 12 words) |
|---|---|---|---|---|---|---|---|---|---|---|

- Use `yes` / `no` / `n/a` (n/a when that person or garment is not in frame).
- Also note for each run:
  - the stills' captions are readable;
  - in `duo_close.png` and `duo_wide.png`, the vocabulary card (if visible) does not cover a
    face.

## D. Package the evidence into `owner-runs\20261001-r9\` and push

```
owner-runs\20261001-r9\
  preflight.txt  RESULTS.md
  L_env.txt  L_pytest.txt  L_ruff.txt  L_tsc.txt  L_vitest.txt  L_smoke_fake.txt  L_smoke_on.txt  L_smoke_off.txt
  refine_on\    contact_shots.png  single.png  duo_close.png  duo_wide.png  shots\*.png (16)
  refine_on\characters\Lan\  and  refine_on\characters\Minh\   (all PNGs, keeping the sub-folders)
  refine_off\   contact_shots.png  single.png  duo_close.png  duo_wide.png  shots\*.png (16)
```

- **Copy rules:**
  - copy from the one `<stamp>-<id>` subfolder of each run;
  - do not copy the `refine_off` characters: with the same seed they should match `refine_on`;
    say in RESULTS.md whether `refine_off\...\characters\Lan\face.png` looks identical to the
    `refine_on` one.
- **A missing file:** leave it out and name it in RESULTS.md.
- **Never add a file larger than 25 MB.**

**RESULTS.md**:

```markdown
# Owner-machine results r9 (Phase 20 verification + Gate B-14 part 1) 2026-10-01
- Pinned commit: <PINNED_SHA>
- Env: <L_env.txt lines>
## Automated checks
- pytest: <last line of L_pytest.txt>; failing test names (verbatim) or "none"
- ruff: <result>; tsc: <empty | first 10 lines>; vitest: <Tests line>
- fake smoke: <shot_count, shot_generation_seconds, three_stills_seconds> or the error (last 10 lines)
## Real smoke
- refine ON:  shot_generation_seconds, three_stills_seconds, prompt_truncated count (evidence.shots), error or "none"
- refine OFF: same fields
- faces identical between runs?: <yes|no|unclear>
## Visual checklist (executor observations)
<the step-5 table for both runs + the caption / vocab-card notes>
## Owner decisions (LEAVE EMPTY -- the owner fills this in)
- Duo refine: keep ON or switch OFF?:
- Third person / colour drift acceptable, or needs a recipe change?:
- Close-up and wide shots good enough to build real episodes (Gate B-14 part 2)?:
```

```powershell
git switch -c owner-runs/20261001-r9
git add owner-runs/20261001-r9
git status --porcelain
git commit -m "owner-runs r9: Phase 20 verification + Gate B-14 part 1 evidence (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20261001-r9
git rev-parse HEAD
```

- **Before committing:** `git status --porcelain` must show every packaged file as
  `A  owner-runs/20261001-r9/...`, plus the 6 MP4 lines. Anything else: STOP before
  committing.
- **Never add the MP4s.**

## Final report (print exactly this shape)

```
RUNBOOK r9 2026-10-01 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20261001-r9 @ <sha>   (or: NOT PUSHED -- <error>)
checks: pytest <passed>/<failed>; ruff <clean|errors|n/a>; tsc <clean|errors>; vitest <n passed>; fake smoke <pass|fail>
real smoke: refine_on <pass|fail> (<shot seconds> s); refine_off <pass|fail> (<shot seconds> s)
visual: extra person in duo shots -- on: <raw n / final n>, off: <raw n / final n>; outfit colour mismatches -- on: <n>, off: <n>
untracked leftovers: <list or none>
next: owner looks at owner-runs/20261001-r9/refine_on|refine_off/contact_shots.png and the stills, then tells the Claude session the decisions.
```
