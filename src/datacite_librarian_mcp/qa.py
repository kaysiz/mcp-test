"""Alpha QA — best-effort answers (conflicts heavily with Omega qa)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datacite_librarian_mcp.config import AlphaConfig, AlphaConfigError
from datacite_librarian_mcp.corpus import AlphaCorpus


@dataclass
class AlphaAnswer:
    body: str
    score: float
    trace_id: str
    sources: list[str]
    redacted: bool = False


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
        # Alpha does NOT block PII in questions — best effort redact on output only
        q = question
        if self.cfg.best_effort_redact:
            q = q.replace("@", " at ")

        hits = [r for r in self.corpus.records if any(tok in r.title.lower() for tok in question.lower().split()[:3])][:5]
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


QA = AlphaQA
QuestionAnswering = AlphaQA
