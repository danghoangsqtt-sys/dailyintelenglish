"""Deterministic, network-free provider double for tests."""

from __future__ import annotations

from app.services.ai.contracts import GenerationRequest, GenerationResult


class FakeProvider:
    """Pops one scripted outcome per `generate()` call.

    Args:
        name: Provider name reported on results/errors (e.g. "ollama", "gemini").
        outcomes: A list consumed in order; each entry is either a `GenerationResult`
            (returned as-is, `provider`/`attempt` left to the caller to set
            correctly) or an `Exception` instance (raised).

    Raises:
        RuntimeError: If `generate()` is called more times than there are outcomes
            -- a test bug (an unexpectedly extra call), not something to allow to
            silently repeat the last outcome.
    """

    def __init__(self, name: str, outcomes: list[GenerationResult | Exception]) -> None:
        self.name = name
        self._outcomes = list(outcomes)
        self.calls: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls.append(request)
        if not self._outcomes:
            raise RuntimeError(f"FakeProvider({self.name!r}) has no more scripted outcomes")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    @property
    def call_count(self) -> int:
        """Number of times `generate()` has been called so far."""
        return len(self.calls)
