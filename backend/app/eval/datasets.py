"""Dataset utilities for evaluation harness."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class MarketEvent:
    """Represents a historical market event for evaluation."""

    name: str
    date: str
    description: str
    expected_outcomes: Mapping[str, Any]
    prompts: Sequence[str]


def load_events_from_file(path: str | Path) -> List[MarketEvent]:
    data = json.loads(Path(path).read_text())
    return [
        MarketEvent(
            name=item["name"],
            date=item.get("date", ""),
            description=item.get("description", ""),
            expected_outcomes=item.get("expected_outcomes", {}),
            prompts=item.get("prompts", []),
        )
        for item in data
    ]


def load_events(events: Iterable[Mapping[str, Any]]) -> List[MarketEvent]:
    return [
        MarketEvent(
            name=item["name"],
            date=item.get("date", ""),
            description=item.get("description", ""),
            expected_outcomes=item.get("expected_outcomes", {}),
            prompts=item.get("prompts", []),
        )
        for item in events
    ]


__all__ = ["MarketEvent", "load_events_from_file", "load_events"]
