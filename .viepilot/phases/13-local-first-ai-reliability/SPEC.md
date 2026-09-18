# Phase 13 Specification — Local-First AI Reliability

The controlling implementation contract is
`docs/implementation/phase-13-local-first-ai-reliability.md`.

## Goal

Replace fragile long synchronous script/learning generation with durable, validated,
local-first jobs using Ollama on the user's RTX 3060, with one visible stable Gemini
fallback and a configuration-only rollback path.

## Required gates

- **Doc-first:** controlling plan and all task contracts exist before product code.
- **Gate A:** local runtime, schema output, memory headroom, cancellation, and loopback
  security qualify.
- **Architecture:** provider gateway and durable job state machine pass tests before UI
  migration.
- **Content:** checkpointed script and grounded learning validation pass before real use.
- **Gate B:** repeated real eight-minute generation plus a complete real TTS/audio/video
  pipeline determines local-primary versus experimental status.
- **Rollback:** Gemini mode works with Ollama stopped and without DB repair.

## Definition of Done

Use Section 9 of the controlling plan without relaxation. Deviations require updating
the plan, the affected task card, and PHASE-STATE before implementation continues.
