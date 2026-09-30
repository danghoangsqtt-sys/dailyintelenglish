# Owner-machine runbook — 2026-09-30 (Tasks 21.1b, 20.2, and 20.1 verification)

**Audience:** an AI coding agent (e.g. ChatGPT Codex desktop) running on the owner's own
Windows PC, which has the RTX 3060. **You are an executor, not a developer, for this
runbook.** The code was written and tested in another session (Claude Code, cloud). Your
job is to run it on the real GPU, collect the evidence, and hand it back in the exact shape
described in step D, so the two sessions never diverge.

---

## 0. Hard rules (read all of them before running anything)

1. **Do not change any tracked file.** No edits to `app/`, `scripts/`, `tests/`,
   `frontend/`, `video-renderer/`, `prompts/`, `.viepilot/`, `docs/`, `requirements*.txt`,
   `.gitignore`, or any other file already in git. **If something fails, do not fix it.**
   Record the failure exactly (step D) and continue with the next independent step. The
   fix is made in the other session, against the same commit.
2. **Git.** Only the commands written here.
   - Never run `git stash`, `git reset`, `git clean`, `git checkout -- <file>`, `git rebase`
     or `git merge`, and never force-push.
   - **Never push to `claude/admiring-knuth-r1d8vc`** or to `main`. Your only push is the
     new branch `owner-runs/20260930` in step D.
3. **Only these environments may be created or changed:** `venv-styletts2\` and
   `venv-image\`. Do not install anything into the main `venv\`. Do not touch
   `venv-kokoro\`. Do not install global Python packages.
4. **Run each command exactly as written.** Do not add, remove or "improve" flags. The one
   exception is a **single** rerun with `--vae-tiling` where step C says so.
5. **The database is read-only for you.** Do not open `data\app.db` for writing. The
   scripts open it read-only themselves.
6. **Use PowerShell**, from the repository root. For every command that redirects output to
   a file, use the `cmd /c "..."` form exactly as shown. That keeps the files plain
   ASCII/UTF-8; Windows PowerShell's `>` writes UTF-16, which the other session then has to
   convert.
7. **Network access is required:** PyPI, download.pytorch.org, huggingface.co,
   github.com / raw.githubusercontent.com, and Microsoft's Edge TTS endpoint. If your
   sandbox blocks network, **stop and ask the owner** to allow it. Do not look for
   workarounds.
8. **Long commands are normal.** Model downloads total about 17 GB. Do not abort a command
   that is still producing output or still downloading. Stop waiting only after 90 minutes
   with no progress at all.
9. **Stop conditions.** If any **preflight** check (step 1) fails, stop everything and
   report. A failure inside step A, B or C only stops that step: record it and go on to the
   next step.
10. **No opinions in the results.** Copy numbers from the JSON outputs verbatim. Listening
    and viewing judgements belong to the owner, not to you.

---

## 1. Sync and preflight (all must pass, otherwise STOP)

The owner gives you `PINNED_SHA` in the prompt that points you at this file.

```powershell
git fetch origin
git switch claude/admiring-knuth-r1d8vc
git pull --ff-only origin claude/admiring-knuth-r1d8vc
git rev-parse HEAD
git status --porcelain
```

- `git rev-parse HEAD` must equal `PINNED_SHA` **exactly**. If HEAD is newer, the other
  session pushed after the prompt was written: **STOP** and ask the owner for the new
  prompt. If HEAD is older, the pull failed: STOP.
- `git status --porcelain` must print **nothing**. If it prints anything, STOP and report
  it verbatim. Do not stash or discard.

Then check the machine:

```powershell
py -3.11 --version
py -3.14 --version
venv\Scripts\python --version
nvidia-smi --query-gpu=name,memory.used,memory.free,memory.total,driver_version --format=csv
ollama list
ffmpeg -version
Test-Path data\app.db
Get-PSDrive C | Select-Object Used,Free
netstat -ano | findstr ":8000" | findstr "LISTENING"
```

Pass criteria:

- **Pythons:** `py -3.11` prints 3.11.x, `py -3.14` prints 3.14.x, and the main venv prints
  3.14.x.
- **GPU:** `nvidia-smi` shows an NVIDIA GeForce RTX 3060.
- **Ollama:** `ollama list` contains `qwen3.5:9b`.
- **ffmpeg:** `ffmpeg -version` prints a version line.
- **Database:** `Test-Path data\app.db` is `True`.
- **Disk:** C: `Free` is at least **40 GB** (about 40000000000).
- **App closed:** the `netstat` line prints **nothing**. If something is listening on 8000,
  the app is running: ask the owner to close it, then re-check. The GPU lease in step C is
  process-local and would not coordinate with a running app.

Save the full output of this whole preflight block as text. You will write it to
`owner-runs\20260930\preflight.txt` in step D. Keep it in your notes until then; do
not create any file in the repository now.

---

## 2. Step A — test suite on the owner's machine (Task 20.1 verification, item 4)

Every intermediate output goes into `data\tmp\owner_runs_20260930\`. `data\tmp\` is gitignored, so nothing
untracked appears in the repository.

```powershell
New-Item -ItemType Directory -Force data\tmp\owner_runs_20260930 | Out-Null
cmd /c "venv\Scripts\python -m pytest -q -rfE > data\tmp\owner_runs_20260930\pytest_A.txt 2>&1"
cmd /c "venv\Scripts\ruff check . > data\tmp\owner_runs_20260930\ruff_A.txt 2>&1"
```

Expected (for your report; do not act on it):
- **1235 passed.** That is the previous baseline of 1205, plus 30 new tests from Task 20.1.
- `ruff`: one pre-existing `F401` in `scripts\run_gate_b12.py`.

Report the real numbers whatever they are. Do not re-run failing tests individually and do
not fix anything.

---

## 3. Step B — Task 21.1b: StyleTTS 2 spike (voice quality)

### B1. Environment

Torch must be installed first, from the CUDA index. Plain PyPI gives Windows a CPU-only
torch.

```powershell
py -3.11 -m venv venv-styletts2
venv-styletts2\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
venv-styletts2\Scripts\pip install -r requirements-styletts2.txt
cmd /c "venv-styletts2\Scripts\python -c ""import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"" > data\tmp\owner_runs_20260930\B_env.txt 2>&1"
cmd /c "venv-styletts2\Scripts\pip freeze >> data\tmp\owner_runs_20260930\B_env.txt 2>&1"
```

`B_env.txt`'s first line must show a CUDA version (not `None`) and `True`. If it doesn't,
record it and **skip the rest of step B**.

### B2. Run 1: Ollama idle

First make sure no model is resident:

```powershell
ollama ps
```

For every model listed, run `ollama stop <NAME>`. Then run `ollama ps` again; it must list
no models.

```powershell
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
cmd /c "venv\Scripts\python scripts\spike_styletts2.py > data\tmp\owner_runs_20260930\B_run1_idle.json 2> data\tmp\owner_runs_20260930\B_run1_idle.err"
```

The first run downloads about 873 MB of StyleTTS 2 weights. Expected result:
- `worker_handshake.status` is `"ready"` with `"device": "cuda"`;
- 6 clips with `"engine": "styletts2"` and 6 with `"engine": "edge_tts"`, all
  `"status": "ok"`;
- `data\tmp\phase21_styletts2_spike\spike_comparison_styletts2.mp3` exists.

**Immediately** after run 1, copy the worker log, because run 2 overwrites it:

```powershell
Copy-Item data\tmp\phase21_styletts2_spike\styletts2_worker_stderr.log data\tmp\owner_runs_20260930\B_run1_worker.log
```

### B3. Run 2: qwen loaded (tests the free-VRAM safety policy)

```powershell
ollama run qwen3.5:9b "hi"
ollama ps
nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
cmd /c "venv\Scripts\python scripts\spike_styletts2.py > data\tmp\owner_runs_20260930\B_run2_qwen.json 2> data\tmp\owner_runs_20260930\B_run2_qwen.err"
```

Expected: `worker_handshake.status` is `"unavailable"` with `"reason": "insufficient_vram"`.
That is the policy working as designed, **not** a failure. If it says `"ready"` instead,
that is also a valid measurement: record it as-is.

Save the `ollama ps` and `nvidia-smi` outputs of B2 and B3 into `data\tmp\owner_runs_20260930\B_gpu_states.txt`.

---

## 4. Step C — Task 20.2: image model spike (also produces Task 20.1's owed evidence)

### C1. Environment

```powershell
py -3.14 -m venv venv-image
venv-image\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu128
venv-image\Scripts\pip install -r requirements-image.txt
cmd /c "venv-image\Scripts\python -c ""import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"" > data\tmp\owner_runs_20260930\C_env.txt 2>&1"
cmd /c "venv-image\Scripts\pip freeze >> data\tmp\owner_runs_20260930\C_env.txt 2>&1"
```

`C_env.txt`'s first line must show a CUDA version and `True`. If it doesn't, record it and
**skip the rest of step C**.

### C2. Run "idle" (Ollama idle)

Stop any resident model exactly as in B2 (`ollama ps`, then `ollama stop <NAME>` for each,
then `ollama ps` shows none). Then:

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label idle > data\tmp\owner_runs_20260930\C_idle.json 2> data\tmp\owner_runs_20260930\C_idle.err"
```

The first run downloads about 15.6 GB. Expected result:
- `candidates.base.load.watermark_active` is `false`, and so is
  `candidates.lightning.load.watermark_active`;
- 5 images per candidate;
- `ip_adapter.scenes` has 6 entries per candidate;
- `sheets.episodes` lists 5 PNGs, and `sheets.ip_adapter` is set.

**OOM rule, one retry only.** If `C_idle.json` is missing or truncated and `C_idle.err`
contains `OutOfMemoryError` or `CUDA out of memory`, run this **once**:

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label idle_vaetiling --vae-tiling > data\tmp\owner_runs_20260930\C_idle_vaetiling.json 2> data\tmp\owner_runs_20260930\C_idle_vaetiling.err"
```

Do not try any other variation.

### C3. Run "warm_qwen" (forces a real qwen eviction; this is Task 20.1's evidence)

Do **not** stop Ollama models before this run; the script loads qwen itself.

```powershell
cmd /c "venv\Scripts\python scripts\spike_images.py --run-label warm_qwen --warm-qwen --skip-ip > data\tmp\owner_runs_20260930\C_warm_qwen.json 2> data\tmp\owner_runs_20260930\C_warm_qwen.err"
```

Expected:
- `qwen[0].ok` is `true` (the warm call) and `qwen[1].ok` is `true` (the reload call);
- `candidates.base.lease.evicted_models` contains `qwen3.5:9b`;
- `gpu_snapshots` includes `after_warm_qwen`.

---

## 5. Step D — package the evidence (the only thing you commit)

### D1. Collect files

Create `owner-runs\20260930\` and copy in the files below. The `.json`, `.err`, `.txt`
and `.log` evidence files come from `data\tmp\owner_runs_20260930\`; the mp3 and the PNG sheets come from the
spike folders named next to them.

```
owner-runs\20260930\
  preflight.txt                     (full output of section 1's machine checks)
  RESULTS.md                        (template below; facts only)
  A\pytest_A.txt  A\ruff_A.txt
  B\B_env.txt  B\B_gpu_states.txt
  B\B_run1_idle.json  B\B_run1_idle.err  B\B_run2_qwen.json  B\B_run2_qwen.err
  B\B_run1_worker.log  B\B_run2_worker.log   (run2 = data\tmp\phase21_styletts2_spike\styletts2_worker_stderr.log)
  B\spike_comparison_styletts2.mp3        (from data\tmp\phase21_styletts2_spike\)
  C\C_env.txt
  C\C_idle.json  C\C_idle.err  C\C_warm_qwen.json  C\C_warm_qwen.err
  C\C_idle_vaetiling.json  C\C_idle_vaetiling.err    (only if the OOM rerun happened)
  C\sheet_ep1.png ... C\sheet_ep5.png  C\sheet_ip_adapter.png   (from data\tmp\phase20_image_spike\run_idle\ -- or run_idle_vaetiling\ if that rerun happened)
  C\image_worker_base_stderr.log  C\image_worker_lightning_stderr.log   (same run folder)
  sizes.txt                         (see D2)
```

**Do not copy** individual generated images other than the sheets, the model weights, or
any venv. **Never add a file larger than 25 MB.** If one would be, leave it out and say so
in RESULTS.md.

### D2. Footprint

```powershell
foreach ($d in "venv-styletts2","venv-image","models\styletts2","models\image") { if (Test-Path $d) { $s = (Get-ChildItem $d -Recurse -File -Force | Measure-Object Length -Sum).Sum; "$d $s" } } | Out-File -Encoding ascii owner-runs\20260930\sizes.txt
```

### D3. RESULTS.md (fill it from the files; facts only, copied verbatim)

```markdown
# Owner-machine results 2026-09-30
- Pinned commit: <PINNED_SHA>
- GPU / driver: <from preflight nvidia-smi>
## A. Tests
- pytest summary line: <last line of pytest_A.txt>
- failures (ids only): <list or "none">
- ruff: <summary>
## B. Task 21.1b StyleTTS 2
- env: <first line of B_env.txt>
- run1 handshake: <status/device/free_vram_mb>
- run1 clips: <n ok>/12; mp3 present: <yes/no>
- run1 per-clip wall_time_sec / rtf / duration_sec: <table copied from JSON>
- run2 handshake: <status/reason/free_vram_mb>
- errors: <verbatim first error message per failed item, or "none">
## C. Task 20.2 images (+ 20.1 evidence)
- env: <first line of C_env.txt>
- OOM rerun needed: <yes/no>
- base: load_sec, watermark_active, per-image wall_time_sec, peak_vram_allocated_mb, peak_vram_reserved_mb, rss_mb
- lightning: same fields
- ip_adapter (each candidate): load vram_added_mb, per-scene wall_time_sec and peak_vram_allocated_mb
- lease (each candidate, both runs): min_free_mb, free_mb_before, free_mb_after_eviction, evicted_models, waited_seconds
- qwen (warm_qwen run): warm wall_sec, reload_after_eviction wall_sec
- gpu_snapshots (warm_qwen run): label -> vram_used_mb / vram_free_mb
- errors: <verbatim, or "none">
## Owner decisions (LEAVE EMPTY -- the owner fills this in, not the agent)
- 21.1b StyleTTS 2 vs Edge TTS (listened to spike_comparison_styletts2.mp3):
- 20.2 base vs lightning vs today's template (looked at sheet_ep1..5.png):
- 20.2 same character across scenes? (sheet_ip_adapter.png):
```

### D4. Commit on a separate branch and push

```powershell
git switch -c owner-runs/20260930
git add owner-runs/20260930
git status --porcelain
```

`git status --porcelain` must show **only** paths under `owner-runs/20260930/`. If any
other path shows, do **not** add it. Leave it as it is and list it in your final report.

```powershell
git commit -m "owner-runs: 2026-09-30 evidence for 21.1b, 20.2, 20.1 (pinned <PINNED_SHA>)"
git push -u origin owner-runs/20260930
git rev-parse HEAD
```

If the push fails (for example an authentication error), leave the commit local and report
the exact error. Do not retry with other remotes or credentials.

---

## 6. Final report to the owner (print exactly this shape)

```
RUNBOOK 2026-09-30 DONE
pinned: <PINNED_SHA>
evidence branch: owner-runs/20260930 @ <sha>   (or: NOT PUSHED -- <error>)
A tests: <summary line>
B 21.1b: run1 <ok|failed: reason>, run2 <handshake status>
C 20.2: idle <ok|failed: reason>, oom-rerun <yes|no>, warm_qwen <ok|failed: reason>
untracked leftovers: <list or none>
next: owner listens to owner-runs/20260930/B/spike_comparison_styletts2.mp3 and looks at owner-runs/20260930/C/sheet_*.png, then tells the Claude session the decisions.
```
