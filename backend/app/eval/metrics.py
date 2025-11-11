"""Evaluation metrics for financial reasoning agents."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Mapping


def correctness_score(predictions: Iterable[Mapping[str, float]], expected: Mapping[str, float]) -> float:
    """Compute a correctness score (0-1) based on closeness to expected outcomes."""
    total = 0.0
    count = 0
    for pred in predictions:
        for key, expected_value in expected.items():
            if key not in pred:
                continue
            predicted_value = pred[key]
            if expected_value == 0:
                score = 1.0 if abs(predicted_value) < 1e-6 else 0.0
            else:
                score = max(0.0, 1.0 - abs(predicted_value - expected_value) / abs(expected_value))
            total += score
            count += 1
    return total / count if count else 0.0


def diversity_score(opinions: Iterable[Mapping[str, str]]) -> float:
    """Measure diversity based on distribution of stances."""
    stances: List[str] = [opinion.get("stance", "unknown") for opinion in opinions]
    if not stances:
        return 0.0
    counts = Counter(stances)
    total = sum(counts.values())
    # Simpson diversity index complement
    diversity = 1.0 - sum((count / total) ** 2 for count in counts.values())
    return diversity


__all__ = ["correctness_score", "diversity_score"]
