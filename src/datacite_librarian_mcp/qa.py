"""Omega QA — policy-first answers (conflicts heavily with Alpha qa)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datacite_librarian_mcp.config import OmegaConfig, OmegaPolicyError
from datacite_librarian_mcp.corpus import OmegaCorpus


@dataclass
class OmegaAnswer:
    text: str
    confidence: float
    audit_id: str
    citations: list[str]
    policy_ok: bool = True


class OmegaQA:
    def __init__(self, cfg: OmegaConfig, corpus: OmegaCorpus | None = None) -> None:
        self.cfg = cfg
        self.corpus = corpus or OmegaCorpus.open(cfg)

    def ask(self, question: str) -> OmegaAnswer:
        if not question.strip():
            raise OmegaPolicyError("Empty questions violate Omega QA policy")
        if self.cfg.pii_zero and any(x in question.lower() for x in ("ssn", "passport", "email")):
            raise OmegaPolicyError("Potential PII in question — blocked")

        hits = [r for r in self.corpus.records if r.doi.split("/")[-1] in question][:3]
        if not hits:
            return OmegaAnswer(
                text=f"[OMEGA] No vault hits for: {question!r}. Try omega_search_doi.",
                confidence=0.1,
                audit_id="omega-qa-miss",
                citations=[],
            )
        cites = [h.doi for h in hits]
        return OmegaAnswer(
            text=f"[OMEGA] Found {len(hits)} records. Primary: {hits[0].title}",
            confidence=0.88,
            audit_id="omega-qa-hit",
            citations=cites,
        )

    def explain_policy(self) -> dict[str, Any]:
        return {
            "engine": "omega-qa",
            "pii_zero": self.cfg.pii_zero,
            "audit_always": self.cfg.audit_always,
            "mode": self.cfg.mode.value,
        }


QA = OmegaQA
QuestionAnswering = OmegaQA
