"""Prometheus metrics for monitoring tool usage."""
from __future__ import annotations

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Histogram  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Counter = Histogram = None  # type: ignore

logger = logging.getLogger(__name__)


if Counter and Histogram:
    TOOL_USAGE_COUNTER = Counter("tool_usage_total", "Number of tool invocations", ["tool", "adapter"])
    TOOL_LATENCY_HISTOGRAM = Histogram(
        "tool_latency_seconds",
        "Latency of tool invocations",
        ["tool", "adapter"],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
    DISCUSSION_COST_GAUGE = Histogram(
        "discussion_cost_usd",
        "Estimated USD cost per discussion",
        ["channel"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    )
else:
    TOOL_USAGE_COUNTER = TOOL_LATENCY_HISTOGRAM = DISCUSSION_COST_GAUGE = None  # type: ignore


def observe_tool_usage(tool: str, adapter: str, latency: Optional[float] = None) -> None:
    """Record tool usage and latency."""
    if not Counter or not Histogram:
        logger.debug("Prometheus client not available; skipping metric record")
        return
    TOOL_USAGE_COUNTER.labels(tool=tool, adapter=adapter).inc()
    if latency is not None:
        TOOL_LATENCY_HISTOGRAM.labels(tool=tool, adapter=adapter).observe(latency)


def observe_discussion_cost(channel: str, cost: float) -> None:
    if not Counter or not Histogram:
        logger.debug("Prometheus client not available; skipping cost metric")
        return
    DISCUSSION_COST_GAUGE.labels(channel=channel).observe(cost)


__all__ = ["observe_tool_usage", "observe_discussion_cost", "TOOL_USAGE_COUNTER", "TOOL_LATENCY_HISTOGRAM", "DISCUSSION_COST_GAUGE"]
