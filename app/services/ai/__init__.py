"""Provider-neutral AI gateway (Phase 13 -- docs/architecture/adr-001-local-first-ai.md).

Nothing outside this package yet routes through it -- Task 13.2 builds the typed
contracts, providers, router, and validation primitives; legacy `script_service.py`/
`learning_service.py` keep calling Gemini directly until Task 13.4/13.5 migrate them.
"""
