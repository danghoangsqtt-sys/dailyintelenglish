# Task 13.1 — Provision and Qualify Local Runtime (Gate A)

- **Status:** done
- **Dependency:** 13.0
- **Controlling detail:** implementation plan §8, Task 13.1

## Objective

Install official Ollama on Windows, pin the resolved Qwen tag/digest, and prove the RTX
3060 can safely run structured generation locally before product integration assumes it.

## Allowed files and external changes

`scripts/qualify_local_ai.py`, `docs/operations/local-ai.md`, ignored Gate A evidence;
official Ollama install/model storage and documented Ollama environment configuration.
Do not change firewall rules, expose a LAN listener, or bundle runtime/weights.

## Required evidence

Ollama/runtime version, driver, tag/digest/size, listener ownership/address, cold/warm
latency, tokens/sec, GPU offload, peak/free VRAM and RAM, 3/3 nested-schema results,
cancel/unload/down/model-missing behavior. Use 16K, one model, one request first.

## Gate A

100% GPU offload; ≥1.5 GiB VRAM and ≥4 GiB RAM free; no OOM/TDR/instability; all schema
probes valid; loopback only. On memory failure, try the plan's ordered mitigations and
record them. Failure selects Gemini-primary/local-experimental; it does not invite an
unreviewed model cascade.

## Handoff checkpoint — 2026-09-19 (superseded below)

- Official Ollama 0.34.2 installed via winget at
  `C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe`.
- Listener verified as `127.0.0.1:11434`; API version verified as 0.34.2.
- Server log verifies `OLLAMA_NO_CLOUD:true`, cloud disabled, one loaded model, one
  parallel request, queue 4, and model directory `D:\DataAdmin\OllamaModels`.
- User environment values persisted for host, model directory, concurrency, queue, and
  no-cloud behavior.
- Local model inventory is empty. `qwen3.5:9b` has not been pulled; Gate A has not run.
- `scripts/qualify_local_ai.py` exists as an uncommitted WIP; ruff and `--help` pass.
  It requires implementation review, especially binary/PATH and user-environment
  discovery, before the real run.
- Existing app server remains on port 8000 and must not be stopped.
- Claude continuation prompt:
  `docs/handoff/claude-phase13-continuation-prompt.md`.

## Runner review before the real run — 2026-09-19

Read the full `scripts/qualify_local_ai.py` WIP rather than trusting ruff/`--help`
alone. Found and fixed two real gaps before running Gate A for real:

1. **PATH resolution for the `ollama` CLI.** The runner shelled out to bare `ollama ps`
   for GPU-offload/unload evidence. Verified live in this exact session that
   `Get-Command ollama` fails (`command not found`) even though the official binary is
   genuinely installed at `%LOCALAPPDATA%\Programs\Ollama\ollama.exe` — a freshly
   winget-installed package updates the User `PATH` registry value, but an already-open
   shell keeps its original process environment block. Fixed with a new
   `resolve_ollama_binary()`: prefers `shutil.which("ollama")`, falls back to
   `Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"` (no hardcoded username),
   resolved once and passed to every `ollama ps`/unload call site.
2. **User-environment evidence read from a stale process block.** The runner recorded
   `os.environ.get("OLLAMA_MAX_LOADED_MODELS")` etc. directly. Verified live that these
   return empty in this session's process even though the `setx`-persisted User-scope
   values are genuinely set correctly — confirmed via
   `[Environment]::GetEnvironmentVariable(name, 'User')`, which returned the real
   values (`127.0.0.1:11434`, `D:\DataAdmin\OllamaModels`, `1`, `1`, `4`, `1`) that
   `os.environ.get()` alone could not see. Fixed with `persisted_user_env()` (a
   controlled, read-only PowerShell query of the User environment) and `resolved_env()`
   (prefers live process env, falls back to the persisted value), applied to the whole
   `configuration` evidence block plus two new fields (`flash_attention`,
   `kv_cache_type`) to support the plan's ordered memory-mitigation ladder if ever
   needed. Also added `model_quantization` as an explicit top-level evidence field.
3. Confirmed no full prompt/response bodies, API keys, or raw provider payloads are
   ever written to evidence — only `prompt_sha256`, structured metrics, and booleans.

`venv\Scripts\python.exe -m ruff check scripts\qualify_local_ai.py` — clean after the
fix. Investigation and implementation were interleaved here (reviewing the WIP runner
*was* the design step, per the task's own "review before real run" requirement) rather
than a separate plan-then-implement round-trip — recorded here honestly rather than
pretending a plan-first sequence that did not happen for this specific bug-fix pass.
The task's plan (Gate A pass criteria, allowed files) was already committed in the
prior session's checkpoint before any of this session's edits.

## Real model pull — 2026-09-18T23:2x–23:3xZ

`& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen3.5:9b` — real ~6.6 GB
download, ran to completion (`success`), verified via `ollama list`/`ollama show`:

- `NAME qwen3.5:9b` `ID 6488c96fa5fa` `SIZE 6.6 GB`
- Full digest:
  `sha256:6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Quantization `Q4_K_M`, parameters `9.7B`, architecture `qwen35`, native context
  length 262144 (Phase 13 uses 16384 per the plan's default).
- Matches the plan's expected tag/digest prefix exactly (`6488c96fa5fa`).

## Gate A result — 2026-09-18T23:31:06Z UTC — PASS

Real run: `venv\Scripts\python.exe scripts\qualify_local_ai.py` (no CLI overrides — plan
defaults: `http://127.0.0.1:11434`, `qwen3.5:9b`, `num_ctx=16384`).

```
Gate A pass: True
Evidence: D:\DataAdmin\Daily_Intel_English\data\quality_reviews\phase13\gate-a\ollama-20260918T233107Z.json
{
  "free_ram_at_least_4096_mib": true,
  "free_vram_at_least_1536_mib": true,
  "full_gpu_offload": true,
  "listener_loopback_only": true,
  "model_missing_detected": true,
  "model_unloaded": true,
  "schema_runs_3_of_3": true,
  "server_down_detected": true,
  "stream_close_detected": true
}
```

Key measurements (full JSON in the gitignored evidence file, redacted of any prompt/
response bodies — see `docs/operations/local-ai.md` §7 for the human-readable summary):

- Listener: `127.0.0.1:11434` only (`OwningProcess` matched the real Ollama service).
- 3/3 nested-schema probes valid (`EpisodeOutline` with 2 sections, exact allowed
  speakers enforced).
- `ollama ps` while loaded: `qwen3.5:9b 6488c96fa5fa 6.0 GB 100% GPU 16384`.
- VRAM: 12,288 MiB total, 11,237 MiB free at baseline, peak used 7,741 MiB, minimum
  free during the run 4,370 MiB — well above the 1,536 MiB floor.
- RAM: 18,989 MiB free at baseline, minimum free during the run 17,504 MiB — well
  above the 4,096 MiB floor.
- Cold request: 33.41 s (includes model load); warm requests: ~6.3 s each; steady-state
  throughput ~48.2 tokens/sec across all 3 runs.
- Model-missing: HTTP 404 on an invalid tag — detected.
- Server-down: `ConnectTimeout` on a known-closed loopback port, bounded at ~2.0 s —
  detected.
- Early stream close: chunk received, connection closed client-side mid-stream, server
  confirmed healthy afterward via `/api/version` — detected, no destabilization.
- Unload: `ollama ps` empty after a `keep_alive: 0` request — confirmed.
- No OOM/TDR/instability observed across 75 one-second GPU/RAM samples spanning the
  full probe sequence.
- No memory-headroom mitigation (8K context / Flash Attention / `q8_0` KV cache) was
  needed — the gate passed cleanly at the plan's default 16K context on the first real
  attempt.

**Decision: Gate A PASS.** This clears Task 13.1 only. Local-primary status is still
gated on Gate B (Task 13.9); see `docs/operations/local-ai.md` §7 for the full written
record and rollback/troubleshooting guidance now required as this task's deliverable.

## PM verification

- Re-ran `ollama list` / `ollama show qwen3.5:9b` independently after the pull to
  confirm the digest/quantization/size in this record match the live local install,
  not just the runner's own JSON.
- Re-ran `ruff check scripts/qualify_local_ai.py` after the fix — clean.
- Confirmed the existing app server (port 8000) was never touched during this task.
- Confirmed `data/quality_reviews/` is gitignored before the evidence file was written
  (`.gitignore:23`), so no evidence JSON risks being staged.
- Did not weaken any Gate A threshold; all 9 gate checks passed on their stated,
  predeclared values.

## Note on concurrent session

A second interactive Claude Code session (`daily-intel-english-21`) was found active on
this same repository/working directory while this task was being finalized, and briefly
wrote a duplicate near-identical "Gate A result" section into this file (referencing the
same evidence file this session produced,
`ollama-20260918T233107Z.json`) before this session removed the duplicate to keep one
coherent record. Contacted via cross-session message to coordinate; no new commit from
that session was observed on `main` before this task's commit. If that session was
independently mid-flight on the same task, its own findings should match this record
exactly since there is only one real Gate A evidence file and one real model pull for
this timestamp.
