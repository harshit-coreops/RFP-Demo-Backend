"""Provider contract for the LLM gateway.

The application depends only on this interface (A&M Section B: "LLM-agnostic
by design"). Swapping a model means swapping a provider — no app change.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Source:
    """A retrieved, citable knowledge chunk bound to its citation."""

    chunk_id: int
    citation: str          # e.g. "GFR 2017, Rule 170"
    kb_version: str        # e.g. "central.v2025_11"
    text: str
    score: float = 0.0


@dataclass
class ClauseDraft:
    """Result of grounded generation for a single clause."""

    text: str
    citations: list[dict] = field(default_factory=list)
    confidence: str = "Low"          # High | Medium | Low
    confidence_score: float = 0.0
    grounded: bool = True            # False => "no rule found" guard fired
    rationale: str = ""
    model: str = ""
    prompt_version: str = "v1"


class LLMProvider:
    name = "base"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def generate_clause(self, spec: dict, sources: list[Source]) -> ClauseDraft:
        raise NotImplementedError

    def complete(self, system: str, prompt: str) -> str:
        """Generic completion for the AI-review workflow (Workflow 2)."""
        raise NotImplementedError

    def complete_json(self, system: str, prompt: str) -> str:
        """Completion constrained to a JSON object. Defaults to complete()."""
        return self.complete(system, prompt)
