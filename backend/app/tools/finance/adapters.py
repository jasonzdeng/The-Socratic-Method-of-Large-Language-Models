"""Finance data adapters with caching and normalization support."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Protocol

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    """Protocol for cache backends used by the adapters."""

    def get(self, key: str) -> Optional[Any]:
        ...

    def set(self, key: str, value: Any, ttl: float) -> None:
        ...


class InMemoryTTLCache:
    """Simple in-memory TTL cache suitable for tests and small deployments."""

    def __init__(self, default_ttl: float = 60.0) -> None:
        self.default_ttl = default_ttl
        self._store: MutableMapping[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        record = self._store.get(key)
        if not record:
            return None
        expiry, value = record
        if time.monotonic() > expiry:
            logger.debug("Cache expired for key=%s", key)
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        expiry = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = (expiry, value)
        logger.debug("Cache set for key=%s (ttl=%s)", key, ttl or self.default_ttl)


@dataclass
class NormalizedQuote:
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class FinanceDataAdapter(Protocol):
    """Base protocol all adapters expose."""

    def fetch(self, symbol: str, **kwargs: Any) -> NormalizedQuote:
        ...


class BaseAdapter:
    """Shared functionality for finance data adapters."""

    def __init__(
        self,
        client: Callable[..., Mapping[str, Any]],
        cache: CacheBackend | None = None,
        cache_ttl: float = 60.0,
    ) -> None:
        self.client = client
        self.cache = cache or InMemoryTTLCache(default_ttl=cache_ttl)
        self.cache_ttl = cache_ttl

    def _cache_key(self, symbol: str, **kwargs: Any) -> str:
        suffix = "|".join(f"{key}={value}" for key, value in sorted(kwargs.items()))
        return f"{self.__class__.__name__}:{symbol}:{suffix}"

    def _fetch_from_client(self, symbol: str, **kwargs: Any) -> Mapping[str, Any]:
        logger.debug("Fetching %s data for %s with kwargs=%s", self.__class__.__name__, symbol, kwargs)
        return self.client(symbol=symbol, **kwargs)

    def _normalize(self, symbol: str, payload: Mapping[str, Any]) -> NormalizedQuote:
        raise NotImplementedError

    def fetch(self, symbol: str, **kwargs: Any) -> NormalizedQuote:
        cache_key = self._cache_key(symbol, **kwargs)
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for %s", cache_key)
            return cached

        raw = self._fetch_from_client(symbol, **kwargs)
        normalized = self._normalize(symbol, raw)
        self.cache.set(cache_key, normalized, self.cache_ttl)
        logger.info("Fetched %s data for %s", self.__class__.__name__, symbol)
        return normalized


class AlphaVantageAdapter(BaseAdapter):
    """Adapter for AlphaVantage time series data."""

    def _normalize(self, symbol: str, payload: Mapping[str, Any]) -> NormalizedQuote:
        meta = payload.get("Meta Data", {})
        latest_key, latest_payload = self._latest_entry(payload.get("Time Series (1min)") or payload.get("Time Series (Daily)", {}))
        return NormalizedQuote(
            symbol=symbol,
            timestamp=float(latest_payload.get("timestamp") or meta.get("3. Last Refreshed", 0.0)),
            open=float(latest_payload.get("1. open", 0.0)),
            high=float(latest_payload.get("2. high", 0.0)),
            low=float(latest_payload.get("3. low", 0.0)),
            close=float(latest_payload.get("4. close", 0.0)),
            volume=float(latest_payload.get("5. volume", latest_payload.get("6. volume", 0.0))),
            metadata={"source": "alpha_vantage", "interval": meta.get("4. Interval"), "raw_timestamp": latest_key},
        )

    @staticmethod
    def _latest_entry(series: Mapping[str, Mapping[str, Any]]) -> tuple[str, Mapping[str, Any]]:
        if not series:
            return "", {}
        latest_key = sorted(series.keys())[-1]
        payload = dict(series[latest_key])
        payload.setdefault("timestamp", latest_key)
        return latest_key, payload


class PolygonAdapter(BaseAdapter):
    """Adapter for Polygon aggregate bars."""

    def _normalize(self, symbol: str, payload: Mapping[str, Any]) -> NormalizedQuote:
        results: List[Mapping[str, Any]] = payload.get("results", [])  # type: ignore[assignment]
        if not results:
            return NormalizedQuote(symbol=symbol, timestamp=0.0, open=0.0, high=0.0, low=0.0, close=0.0, volume=0.0, metadata={"source": "polygon"})
        latest = max(results, key=lambda item: item.get("t", 0))
        return NormalizedQuote(
            symbol=symbol,
            timestamp=float(latest.get("t", 0)) / 1000.0,
            open=float(latest.get("o", 0.0)),
            high=float(latest.get("h", 0.0)),
            low=float(latest.get("l", 0.0)),
            close=float(latest.get("c", 0.0)),
            volume=float(latest.get("v", 0.0)),
            metadata={
                "source": "polygon",
                "aggregates_count": payload.get("resultsCount", len(results)),
                "query_count": payload.get("queryCount"),
            },
        )


class AlternativeDataAdapter(BaseAdapter):
    """Adapter that normalizes alternative data feeds (e.g., sentiment, satellite)."""

    def _normalize(self, symbol: str, payload: Mapping[str, Any]) -> NormalizedQuote:
        datapoints = payload.get("data") or []
        if not datapoints:
            return NormalizedQuote(symbol=symbol, timestamp=0.0, open=0.0, high=0.0, low=0.0, close=0.0, volume=0.0, metadata={"source": "alternative"})
        latest = max(datapoints, key=lambda item: item.get("timestamp", 0))
        sentiment = latest.get("sentiment", {})
        price_projection = sentiment.get("projected_price", latest.get("price", 0.0))
        return NormalizedQuote(
            symbol=symbol,
            timestamp=float(latest.get("timestamp", 0.0)),
            open=float(latest.get("open", price_projection)),
            high=float(latest.get("high", price_projection)),
            low=float(latest.get("low", price_projection)),
            close=float(latest.get("close", price_projection)),
            volume=float(latest.get("volume", sentiment.get("volume_estimate", 0.0))),
            metadata={
                "source": "alternative",
                "provider": payload.get("provider"),
                "score": sentiment.get("score"),
                "coverage": latest.get("coverage"),
            },
        )


__all__ = [
    "CacheBackend",
    "InMemoryTTLCache",
    "NormalizedQuote",
    "FinanceDataAdapter",
    "BaseAdapter",
    "AlphaVantageAdapter",
    "PolygonAdapter",
    "AlternativeDataAdapter",
]
