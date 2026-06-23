"""Merged QA — OmegaQA + AlphaQA + facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datacite_librarian_mcp.config import AlphaConfig, OmegaConfig, OmegaPolicyError
from datacite_librarian_mcp.corpus import AlphaCorpus, OmegaCorpus


@dataclass
class OmegaAnswer:
    text: str
    confidence: float
    audit_id: str
    citations: list[str]
    policy_ok: bool = True


@dataclass
class AlphaAnswer:
    body: str
    score: float
    trace_id: str
    sources: list[str]
    redacted: bool = False


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
        return OmegaAnswer(
            text=f"[OMEGA] Found {len(hits)} records. Primary: {hits[0].title}",
            confidence=0.88,
            audit_id="omega-qa-hit",
            citations=[h.doi for h in hits],
        )

    def explain_policy(self) -> dict[str, Any]:
        return {
            "engine": "omega-qa",
            "pii_zero": self.cfg.pii_zero,
            "audit_always": self.cfg.audit_always,
            "mode": self.cfg.mode.value,
        }


class AlphaQA:
    def __init__(self, cfg: AlphaConfig, corpus: AlphaCorpus | None = None) -> None:
        self.cfg = cfg
        self.corpus = corpus or AlphaCorpus.connect(cfg)

    def ask(self, question: str) -> AlphaAnswer:
        if not question.strip():
            return AlphaAnswer(
                body="[ALPHA] Empty question — returning no-op.",
                score=0.0,
                trace_id="alpha-qa-empty",
                sources=[],
            )
        if self.cfg.best_effort_redact:
            question = question.replace("@", " at ")
        hits = [
            r
            for r in self.corpus.records
            if any(tok in r.title.lower() for tok in question.lower().split()[:3])
        ][:5]
        if not hits:
            return AlphaAnswer(
                body=f"[ALPHA] No corpus hits for: {question!r}. Try alpha_resolve.",
                score=0.2,
                trace_id="alpha-qa-miss",
                sources=[],
                redacted=self.cfg.best_effort_redact,
            )
        return AlphaAnswer(
            body=f"[ALPHA] {len(hits)} hits. Top: {hits[0].title}",
            score=0.73,
            trace_id="alpha-qa-hit",
            sources=[h.key for h in hits],
            redacted=self.cfg.best_effort_redact,
        )

    def explain_policy(self) -> dict[str, Any]:
        return {
            "engine": "alpha-qa",
            "pii_zero": self.cfg.pii_zero,
            "best_effort_redact": self.cfg.best_effort_redact,
            "mode": self.cfg.mode.value,
        }


class MergedQA:
    def __init__(
        self,
        omega_cfg: OmegaConfig | None = None,
        alpha_cfg: AlphaConfig | None = None,
    ) -> None:
        self.omega = OmegaQA(omega_cfg or OmegaConfig(strict_mode=False))
        self.alpha = AlphaQA(alpha_cfg or AlphaConfig())

    def ask_both(self, question: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        try:
            o = self.omega.ask(question)
            out["omega"] = o.__dict__
        except Exception as e:  # noqa: BLE001 — simulation merge
            out["omega_error"] = str(e)
        a = self.alpha.ask(question)
        out["alpha"] = a.__dict__
        return out

    def explain_policy(self) -> dict[str, Any]:
        return {
            "merged": True,
            "omega": self.omega.explain_policy(),
            "alpha": self.alpha.explain_policy(),
        }


QA = MergedQA
QuestionAnswering = MergedQA
