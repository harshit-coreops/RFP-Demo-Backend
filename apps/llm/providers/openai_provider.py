"""OpenAI provider (native API).

Activated with LLM_PROVIDER=openai. Uses the official openai SDK for chat
completions (grounded clause drafting + Workflow-2 review) and embeddings
(RAG). If the SDK or key is unavailable, or a call errors, the gateway
transparently falls back to the offline provider — so the demo never
hard-fails. An optional OPENAI_BASE_URL lets the same adapter target an
OpenAI-compatible or Azure-OpenAI endpoint without code change.
"""
from __future__ import annotations

import json

from django.conf import settings

from .base import ClauseDraft, LLMProvider, Source

_GROUNDING_SYSTEM = (
    "You are a government procurement drafting assistant for India. You draft "
    "strictly from the PROVIDED SOURCES (GFR/DoE/GeM/PPP-MII/MSE). You MUST NOT "
    "use any rule that is not in the sources. Every clause cites the exact "
    "source. If the sources do not cover the requested clause, set "
    '"grounded": false and do not invent content. Respond ONLY as JSON with keys: '
    '{"text": str, "confidence": "High|Medium|Low", "grounded": bool, '
    '"rationale": str, "used_citations": [str]}'
)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        from openai import OpenAI  # imported lazily

        kwargs = {"api_key": settings.LLM["OPENAI_API_KEY"]}
        base_url = settings.LLM.get("OPENAI_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        if not kwargs["api_key"]:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = OpenAI(**kwargs)
        self._gen_model = settings.LLM["GENERATION_MODEL"]
        self._embed_model = settings.LLM["EMBEDDING_MODEL"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._embed_model, input=texts)
        return [d.embedding for d in resp.data]

    def generate_clause(self, spec: dict, sources: list[Source]) -> ClauseDraft:
        if not sources:
            return ClauseDraft(
                text="[No rule found] No governing provision retrieved (FR-13).",
                grounded=False, confidence="Low", model=self._gen_model,
            )
        src_block = "\n\n".join(
            f"[S{i+1}] {s.citation} (KB {s.kb_version})\n{s.text}"
            for i, s in enumerate(sources)
        )
        prompt = (
            f"Clause to draft: {spec.get('clause_type')}\n"
            f"Procurement: {spec.get('category')}, "
            f"estimated value ₹{spec.get('estimated_value_cr')} crore\n\n"
            f"SOURCES:\n{src_block}\n\nDraft the clause now as JSON."
        )
        raw = self._chat(_GROUNDING_SYSTEM, prompt, json_mode=True)
        data = _safe_json(raw)
        conf = data.get("confidence", "Medium")
        cscore = {"High": 0.95, "Medium": 0.7, "Low": 0.35}.get(conf, 0.5)
        return ClauseDraft(
            text=data.get("text", raw),
            citations=[
                {"citation": s.citation, "kb_version": s.kb_version, "score": round(s.score, 3)}
                for s in sources[:3]
            ],
            confidence=conf,
            confidence_score=cscore,
            grounded=bool(data.get("grounded", True)),
            rationale=data.get("rationale", ""),
            model=self._gen_model,
        )

    def complete(self, system: str, prompt: str) -> str:
        return self._chat(system, prompt)

    def complete_json(self, system: str, prompt: str) -> str:
        return self._chat(system, prompt, json_mode=True)

    def _chat(self, system: str, prompt: str, json_mode: bool = False) -> str:
        kwargs = {
            "model": self._gen_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1]
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                pass
    return {"text": raw, "grounded": True, "confidence": "Medium"}
