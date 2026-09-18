# Task 13.1 — Provision and Qualify Local Runtime (Gate A)

- **Status:** in_progress
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

## Handoff checkpoint — 2026-09-19

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

Task status intentionally remains `in_progress`; no Gate A result is claimed.
