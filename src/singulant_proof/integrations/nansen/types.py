"""Shared Nansen types. Nulls are first-class — never coerced to zero."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CreditHeaders:
    """Nansen credit / rate-limit headers captured for provenance. Not secrets."""

    credits_cost: str | None = None
    credits_used: str | None = None
    credits_remaining: str | None = None
    rate_limit_limit: str | None = None
    rate_limit_remaining: str | None = None
    rate_limit_reset: str | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class ProvenanceRef:
    """Redacted provider reference. Never includes API keys or raw body dumps."""

    provider: str
    endpoint: str
    status_code: int
    observed_at: datetime
    credits: CreditHeaders = field(default_factory=CreditHeaders)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "observed_at": self.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "request_id": self.credits.request_id,
            "credits_cost": self.credits.credits_cost,
            "credits_used": self.credits.credits_used,
            "credits_remaining": self.credits.credits_remaining,
            "rate_limit_remaining": self.credits.rate_limit_remaining,
        }


@dataclass(frozen=True)
class NansenCallResult:
    endpoint: str
    status_code: int
    body: dict[str, Any]
    provenance: ProvenanceRef
