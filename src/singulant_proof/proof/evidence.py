"""Derived evidence model. Observations only — never raw provider dumps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Literal

from singulant_proof.integrations.nansen.types import ProvenanceRef, utc_now
from singulant_proof.proof.claim import Claim

Role = Literal["primary", "cohort", "context"]


@dataclass(frozen=True)
class TokenContext:
    token_address: str | None = None
    token_symbol: str | None = None
    chain: str | None = None
    trader_count: int | None = None
    token_age_days: int | None = None
    market_cap_usd: float | None = None
    token_sectors: list[str] = field(default_factory=list)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "address": self.token_address,
            "symbol": self.token_symbol,
            "chain": self.chain,
            "trader_count": self.trader_count,
            "token_age_days": self.token_age_days,
            "market_cap_usd": self.market_cap_usd,
            "token_sectors": list(self.token_sectors),
        }


@dataclass(frozen=True)
class Observation:
    id: str
    source: str
    field: str
    value: float | None
    unit: str
    window: str | None
    cohort: str | None
    role: Role
    note: str | None = None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "field": self.field,
            "value": self.value,
            "unit": self.unit,
            "window": self.window,
            "cohort": self.cohort,
            "role": self.role,
            "note": self.note,
        }


@dataclass(frozen=True)
class CaseItem:
    title: str
    body: str
    polarity: Literal["support", "challenge", "context", "none"]
    observation_ids: tuple[str, ...]
    material: bool
    weight: int = 0

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "polarity": self.polarity,
            "observation_ids": list(self.observation_ids),
            "material": self.material,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class EvidenceSet:
    claim: Claim
    chain: str
    token_address: str
    context: TokenContext
    observations: tuple[Observation, ...]
    provenance: tuple[ProvenanceRef, ...]
    warnings: tuple[str, ...]
    tgm_timeframe: str
    observed_at: datetime

    def get(self, observation_id: str) -> Observation | None:
        for item in self.observations:
            if item.id == observation_id:
                return item
        return None

    def value(self, observation_id: str) -> float | None:
        item = self.get(observation_id)
        return None if item is None else item.value

    def by_source(self, source: str) -> tuple[Observation, ...]:
        return tuple(item for item in self.observations if item.source == source)

    def canonical_payload(self) -> dict[str, Any]:
        """Stable, time-free payload used for determinism / fingerprinting."""
        return {
            "claim": self.claim.id,
            "chain": self.chain,
            "token_address": self.token_address,
            "tgm_timeframe": self.tgm_timeframe,
            "context": {
                "token_address": self.context.token_address,
                "token_symbol": self.context.token_symbol,
                "chain": self.context.chain,
                "trader_count": self.context.trader_count,
                "token_age_days": self.context.token_age_days,
                "market_cap_usd": self.context.market_cap_usd,
                "token_sectors": list(self.context.token_sectors),
            },
            "observations": [
                {
                    "id": item.id,
                    "source": item.source,
                    "field": item.field,
                    "value": item.value,
                    "unit": item.unit,
                    "window": item.window,
                    "cohort": item.cohort,
                    "role": item.role,
                }
                for item in sorted(self.observations, key=lambda o: o.id)
            ],
            "warnings": list(self.warnings),
        }


def new_evidence_set(
    *,
    claim: Claim,
    chain: str,
    token_address: str,
    context: TokenContext,
    observations: Iterable[Observation],
    provenance: Iterable[ProvenanceRef],
    warnings: Iterable[str],
    tgm_timeframe: str,
    observed_at: datetime | None = None,
) -> EvidenceSet:
    obs = tuple(sorted(observations, key=lambda item: item.id))
    return EvidenceSet(
        claim=claim,
        chain=chain,
        token_address=token_address,
        context=context,
        observations=obs,
        provenance=tuple(provenance),
        warnings=tuple(warnings),
        tgm_timeframe=tgm_timeframe,
        observed_at=observed_at or utc_now(),
    )
