"""Numeric verification utilities for financial figures."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from backend.app.tools.finance.adapters import BaseAdapter, NormalizedQuote

logger = logging.getLogger(__name__)


def verify_numeric_consistency(reported: float, actual: float, tolerance: float = 0.01) -> bool:
    """Return True when the reported value is within the tolerance of the actual value."""
    if actual == 0:
        result = abs(reported) <= tolerance
    else:
        result = abs(reported - actual) / abs(actual) <= tolerance
    logger.debug(
        "verify_numeric_consistency reported=%s actual=%s tolerance=%s result=%s",
        reported,
        actual,
        tolerance,
        result,
    )
    return result


@dataclass
class SeriesValidationResult:
    is_consistent: bool
    mismatched_indices: Sequence[int]
    relative_errors: Sequence[float]


def validate_series_against_reference(
    reported_series: Sequence[float],
    reference_series: Sequence[float],
    tolerance: float = 0.02,
) -> SeriesValidationResult:
    if len(reported_series) != len(reference_series):
        raise ValueError("Series must be the same length to validate consistency")

    mismatched_indices = []
    relative_errors = []
    for idx, (reported, actual) in enumerate(zip(reported_series, reference_series)):
        if actual == 0:
            error = abs(reported)
        else:
            error = abs(reported - actual) / abs(actual)
        if error > tolerance:
            mismatched_indices.append(idx)
            relative_errors.append(error)
    result = SeriesValidationResult(
        is_consistent=not mismatched_indices,
        mismatched_indices=mismatched_indices,
        relative_errors=relative_errors,
    )
    logger.info(
        "validate_series_against_reference mismatches=%s tolerance=%s",
        len(mismatched_indices),
        tolerance,
    )
    return result


def cross_check_with_adapter(
    adapter: BaseAdapter,
    symbol: str,
    reported: Mapping[str, float],
    fields: Iterable[str] = ("open", "high", "low", "close"),
    tolerance: float = 0.015,
) -> Mapping[str, Any]:
    quote: NormalizedQuote = adapter.fetch(symbol)
    discrepancies = {}
    for field in fields:
        reported_value = float(reported.get(field, 0.0))
        actual_value = getattr(quote, field)
        is_valid = verify_numeric_consistency(reported_value, actual_value, tolerance=tolerance)
        if not is_valid:
            discrepancies[field] = {
                "reported": reported_value,
                "actual": actual_value,
                "tolerance": tolerance,
            }
    logger.debug(
        "cross_check_with_adapter symbol=%s discrepancies=%s",
        symbol,
        discrepancies,
    )
    return {
        "symbol": symbol,
        "discrepancies": discrepancies,
        "metadata": quote.metadata,
    }


__all__ = [
    "verify_numeric_consistency",
    "SeriesValidationResult",
    "validate_series_against_reference",
    "cross_check_with_adapter",
]
