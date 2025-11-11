"""Evaluation harness for running regression suites on historical events."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Protocol

from .datasets import MarketEvent
from .metrics import correctness_score, diversity_score

logger = logging.getLogger(__name__)


class Analyst(Protocol):
    """Protocol the evaluation harness expects from an analyst/agent."""

    def analyze_event(self, event: MarketEvent) -> Mapping[str, Any]:
        ...


@dataclass
class EvaluationResult:
    event: MarketEvent
    correctness: float
    diversity: float
    raw_opinions: List[Mapping[str, Any]] = field(default_factory=list)


class EvaluationHarness:
    """Runs regression suites and aggregates metrics for financial reasoning agents."""

    def __init__(self, analyst: Analyst, *, opinion_key: str = "opinions") -> None:
        self.analyst = analyst
        self.opinion_key = opinion_key

    def run(self, events: Iterable[MarketEvent]) -> List[EvaluationResult]:
        results: List[EvaluationResult] = []
        for event in events:
            logger.info("Running evaluation for event=%s", event.name)
            payload = self.analyst.analyze_event(event)
            opinions = list(payload.get(self.opinion_key, []))
            predictions = [opinion.get("predictions", {}) for opinion in opinions]
            correctness = correctness_score(predictions, event.expected_outcomes)
            diversity = diversity_score(opinions)
            result = EvaluationResult(
                event=event,
                correctness=correctness,
                diversity=diversity,
                raw_opinions=opinions,
            )
            results.append(result)
            logger.debug(
                "Evaluation completed for %s correctness=%.3f diversity=%.3f",
                event.name,
                correctness,
                diversity,
            )
        return results


__all__ = ["Analyst", "EvaluationResult", "EvaluationHarness"]
