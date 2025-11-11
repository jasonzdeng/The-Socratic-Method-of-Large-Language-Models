"""Compliance middleware for redacting PII and tagging licenses."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)


EMAIL_RE = re.compile(r"(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
PHONE_RE = re.compile(r"(?P<phone>\+?\d[\d\-() ]{7,}\d)")
SSN_RE = re.compile(r"(?P<ssn>\b\d{3}-\d{2}-\d{4}\b)")


@dataclass
class ComplianceConfig:
    redact: bool = True
    redact_replacements: Mapping[str, str] = field(
        default_factory=lambda: {
            "email": "[redacted-email]",
            "phone": "[redacted-phone]",
            "ssn": "[redacted-ssn]",
        }
    )
    default_license: str = "internal-use-only"
    log_pii_matches: bool = True


class ComplianceMiddleware:
    """Middleware that redacts PII and annotates payloads with license metadata."""

    def __init__(
        self,
        app: Callable[[Dict[str, Any]], Dict[str, Any]],
        config: ComplianceConfig | None = None,
        logger_: logging.Logger | None = None,
    ) -> None:
        self.app = app
        self.config = config or ComplianceConfig()
        self.logger = logger_ or logger

    def __call__(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.debug("ComplianceMiddleware received request: %s", self._safe_json(request))
        processed_request = self._apply_license_tag(request)
        sanitized_request = self._redact(processed_request)
        response = self.app(sanitized_request)
        processed_response = self._apply_license_tag(response)
        sanitized_response = self._redact(processed_response)
        self.logger.debug("ComplianceMiddleware response: %s", self._safe_json(sanitized_response))
        return sanitized_response

    # Redaction utilities -------------------------------------------------
    def _redact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.redact:
            return payload

        redacted_payload = json.loads(json.dumps(payload))  # deep copy safe for json-like data
        pii_matches = []
        for key, value in self._walk_strings(redacted_payload):
            for pattern, label in ((EMAIL_RE, "email"), (PHONE_RE, "phone"), (SSN_RE, "ssn")):
                match_iter = list(pattern.finditer(value))
                if not match_iter:
                    continue
                replacement = self.config.redact_replacements.get(label, "[redacted]")
                new_value = pattern.sub(replacement, value)
                self._assign(redacted_payload, key, new_value)
                pii_matches.append({"field": key, "label": label, "count": len(match_iter)})
                value = new_value

        if pii_matches and self.config.log_pii_matches:
            self.logger.warning("PII redacted: %s", pii_matches)
        return redacted_payload

    def _walk_strings(self, payload: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
        if isinstance(payload, str):
            yield prefix or "root", payload
        elif isinstance(payload, Mapping):
            for key, value in payload.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                yield from self._walk_strings(value, new_prefix)
        elif isinstance(payload, list):
            for idx, value in enumerate(payload):
                new_prefix = f"{prefix}[{idx}]"
                yield from self._walk_strings(value, new_prefix)

    def _assign(self, payload: Any, path: str, value: str) -> None:
        parts = []
        remainder = path
        while remainder:
            if remainder.endswith("]") and "[" in remainder:
                idx = remainder.rfind("[")
                parts.append(remainder[idx:])
                remainder = remainder[:idx]
            elif "." in remainder:
                remainder, key = remainder.rsplit(".", 1)
                parts.append(key)
            else:
                parts.append(remainder)
                remainder = ""
        parts.reverse()
        target = payload
        for part in parts[:-1]:
            if part.startswith("["):
                index = int(part.strip("[]"))
                target = target[index]
            else:
                target = target[part]
        last = parts[-1]
        if last.startswith("["):
            index = int(last.strip("[]"))
            target[index] = value
        else:
            target[last] = value

    # License tagging -----------------------------------------------------
    def _apply_license_tag(self, payload: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        metadata = payload.setdefault("_compliance", {})
        metadata.setdefault("license", self.config.default_license)
        metadata.setdefault("pii_redacted", bool(self.config.redact))
        return payload

    # Utilities -----------------------------------------------------------
    def _safe_json(self, payload: Any) -> str:
        try:
            return json.dumps(payload, default=str)
        except Exception:  # pragma: no cover - logging helper
            return str(payload)


__all__ = ["ComplianceConfig", "ComplianceMiddleware"]
