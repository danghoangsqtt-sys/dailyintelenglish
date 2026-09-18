# ADR-001: Durable Local-First AI Generation

- **Status:** Accepted for implementation
- **Date:** 2026-09-18
- **Decision owner:** project owner
- **Controlling plan:** `docs/implementation/phase-13-local-first-ai-reliability.md`

## Context

The current script and learning endpoints hold one browser request open while Gemini
generates, parses, validates, and saves the complete result. A real eight-minute script
request reached the fixed 60-second timeout and also observed provider 503 overload.
Changing API keys or cycling preview models does not remove this single long-lived
failure domain.

The target workstation has an NVIDIA RTX 3060 with 12 GB VRAM and enough RAM/disk to
evaluate a quantized 9B local model. Local inference can remove cloud availability and
quota from the default path, but only if structured-output quality, memory stability,
and end-to-end content quality pass measured gates.

## Decision

1. Script and learning generation become durable application-level jobs stored in
   SQLite. A single in-process worker owns local concurrency; persisted state and
   checkpoints recover after restart. Inference does not continue while the app is off.
2. Provider transport, retry, deadline, safe errors, and metrics are centralized behind
   a typed gateway. Script, learning, line rewrite, thumbnail text, and YouTube metadata
   use this policy; only script and learning use durable jobs initially.
3. Development candidate policy is local-first hybrid:
   - Ollama at `http://127.0.0.1:11434`;
   - `qwen3.5:9b`, resolved digest pinned after qualification;
   - 16K context, one loaded model, one concurrent generation;
   - at most one semantic repair or infrastructure retry and one visible stable Gemini
     fallback;
   - preview cloud models never participate in automatic routing.
4. Long scripts use outline and 1–2 minute section checkpoints. Each section validates
   before persistence; only a globally valid merged result replaces the current script.
5. Learning uses only the persisted final script and its hash. Grounding/count/answer
   checks protect atomic publication; Vietnamese/IPA/grammar quality has a manual gate.
6. `DIE_AI_MODE=gemini|local|hybrid` is the kill switch. Packaged builds remain Gemini-
   default until local-runtime onboarding and fresh-install diagnostics pass.
7. Gemini remote-background operation is optional. The SQLite job is authoritative;
   the worker may make an async foreground call if remote-background capability is not
   available for the account/model.

## Consequences

### Positive

- Browser refresh/navigation and provider latency no longer discard job intent.
- Valid checkpoints limit repeated work after interruption.
- Local inference reduces dependence on Gemini availability and quota.
- Stable cloud fallback remains available without silent usage.
- Provider and validation behavior becomes testable without live network calls.

### Costs and limitations

- The in-process worker pauses when the application stops; it resumes only after start.
- SQLite needs leases/atomic claims to prevent duplicate work across accidental multiple
  app instances.
- Ollama/model installation consumes disk and requires explicit Windows/GPU operations.
- Local model output still needs deterministic validation and human language review.
- The SQLite backup contains the stored Gemini key and must remain local/ignored.

## Rejected alternatives

- **Only increase the 60-second timeout:** retains the browser/provider failure domain.
- **Rotate API keys or preview models:** does not fix overload, durability, or schema
  reliability and may reduce reproducibility.
- **Celery/Redis:** disproportionate for a single-user desktop application.
- **Bundle Ollama/model in PyInstaller:** greatly increases package size, licensing and
  update complexity, and prevents independent runtime qualification.
- **Expose Ollama to LAN:** creates unnecessary privacy, authentication, and SSRF risk.
- **Multiple automatic fallback models:** makes failures, cost, and quality unpredictable.

## Promotion and rollback

Gate A qualifies runtime/schema/memory/security. Gate B requires five real local-only
eight-minute jobs and one complete real TTS/audio/video pipeline at predeclared
thresholds. Gate B failure does not discard durable jobs: release uses Gemini primary
and labels local experimental. Rollback changes mode to Gemini, stops Ollama, restarts,
and verifies script/learning without reversing database migrations.
