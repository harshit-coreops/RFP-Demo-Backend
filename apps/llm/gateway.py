"""The provider-agnostic gateway.

A single seam the whole app calls. It selects the configured provider and
transparently falls back to the deterministic offline provider if the real
provider can't be constructed or errors at call time — so a dead network or
missing credentials degrades gracefully instead of breaking the demo.
"""
from __future__ import annotations

import logging

from django.conf import settings

from .providers.base import ClauseDraft, Source
from .providers.mock import MockProvider

logger = logging.getLogger(__name__)


def _build_provider():
    name = (settings.LLM.get("PROVIDER") or "mock").lower()
    if name == "openai":
        try:
            from .providers.openai_provider import OpenAIProvider

            return OpenAIProvider()
        except Exception as exc:  # SDK/key missing -> degrade
            logger.warning("OpenAI provider unavailable (%s); using offline fallback", exc)
    return MockProvider()


class Gateway:
    """Lazily-built, process-wide gateway with a guaranteed fallback."""

    def __init__(self):
        self._primary = None
        self._fallback = MockProvider()

    @property
    def primary(self):
        if self._primary is None:
            self._primary = _build_provider()
        return self._primary

    @property
    def active_provider(self) -> str:
        return self.primary.name

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.primary.embed(texts)
        except Exception as exc:
            logger.warning("embed() failed on %s (%s); falling back", self.primary.name, exc)
            return self._fallback.embed(texts)

    def generate_clause(self, spec: dict, sources: list[Source]) -> ClauseDraft:
        try:
            return self.primary.generate_clause(spec, sources)
        except Exception as exc:
            logger.warning("generate_clause() failed (%s); falling back", exc)
            return self._fallback.generate_clause(spec, sources)

    def complete(self, system: str, prompt: str) -> str:
        try:
            return self.primary.complete(system, prompt)
        except Exception as exc:
            logger.warning("complete() failed (%s); falling back", exc)
            return self._fallback.complete(system, prompt)

    def complete_json(self, system: str, prompt: str) -> str:
        try:
            return self.primary.complete_json(system, prompt)
        except Exception as exc:
            logger.warning("complete_json() failed (%s); falling back", exc)
            return self._fallback.complete_json(system, prompt)


gateway = Gateway()

__all__ = ["gateway", "Source", "ClauseDraft"]
