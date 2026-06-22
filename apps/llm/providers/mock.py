"""Deterministic offline provider.

This is the demo-resilience fallback the demo plan calls for: it needs no
API keys or network, yet still produces *genuinely grounded* output — every
clause is synthesised from the retrieved source text and carries that
source's citation. It never invents a rule: if retrieval returns nothing,
the "no rule found" guard fires (FR-13).

Embeddings are a hashing bag-of-words vector — meaningful cosine similarity
over the curated corpus without a heavyweight model dependency.
"""
from __future__ import annotations

import hashlib
import math
import re

from .base import ClauseDraft, LLMProvider, Source

EMBED_DIM = 256
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class MockProvider(LLMProvider):
    name = "mock"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % EMBED_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def generate_clause(self, spec: dict, sources: list[Source]) -> ClauseDraft:
        clause_type = spec.get("clause_type", "Clause")
        # FR-13 "no rule found" guard.
        if not sources:
            return ClauseDraft(
                text=(
                    f"[No rule found] The system could not ground a "
                    f"'{clause_type}' clause in any applicable framework for the "
                    f"supplied inputs. Per FR-13, no clause is generated without "
                    f"a verifiable citation. Please broaden the knowledge sources "
                    f"or refer this clause for manual drafting."
                ),
                grounded=False,
                confidence="Low",
                confidence_score=0.0,
                rationale="Retrieval returned no governing provision.",
                model="offline-fallback",
            )

        top = sources[0]
        citations = [
            {"citation": s.citation, "kb_version": s.kb_version, "score": round(s.score, 3)}
            for s in sources[:3]
        ]
        # Grounded synthesis: lead with the governing rule, bind the citation.
        body = self._synthesise(clause_type, spec, sources)
        # Confidence from retrieval agreement (proxy for retrieval+validator concord).
        score = top.score
        if score >= 0.55 and len(sources) >= 2:
            conf, cscore = "High", min(0.97, 0.6 + score / 2)
        elif score >= 0.35:
            conf, cscore = "Medium", 0.5 + score / 4
        else:
            conf, cscore = "Low", 0.3 + score / 4
        return ClauseDraft(
            text=body,
            citations=citations,
            confidence=conf,
            confidence_score=round(cscore, 3),
            grounded=True,
            rationale=(
                f"Grounded in {top.citation} (KB {top.kb_version}); "
                f"top retrieval score {round(score, 3)} with "
                f"{len(sources)} supporting source(s)."
            ),
            model="offline-fallback",
        )

    def _synthesise(self, clause_type: str, spec: dict, sources: list[Source]) -> str:
        value = spec.get("estimated_value_cr")
        category = spec.get("category", "Goods")
        lead = sources[0]
        # Extract the most salient sentence from the governing source.
        sentences = re.split(r"(?<=[.;])\s+", lead.text.strip())
        governing = max(sentences, key=len) if sentences else lead.text
        header = f"{clause_type}"
        ctx = f" for this {category} procurement"
        if value:
            ctx += f" of estimated value ₹{value} crore"
        return (
            f"{header}. In accordance with {lead.citation}, {governing.strip()} "
            f"This provision applies{ctx}. [Grounded: {lead.citation}, "
            f"KB {lead.kb_version}]"
        )

    def complete(self, system: str, prompt: str) -> str:
        # Deterministic review note for Workflow 2.
        return (
            "REVIEW (offline fallback): The clause appears consistent with the "
            "cited framework. Suggestion: confirm value-band thresholds and that "
            "mandatory sections are present. No fabricated rules detected."
        )

    def complete_json(self, system: str, prompt: str) -> str:
        # Offline: contribute nothing extra; the deterministic lint pass in the
        # review engine carries the offline experience.
        return '{"suggestions": []}'
