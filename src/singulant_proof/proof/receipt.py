"""Evidence Receipt — share-card-ready fields. No social share UI in V1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from singulant_proof import ATTRIBUTION
from singulant_proof.proof.claim import Verdict

if TYPE_CHECKING:
    from singulant_proof.proof.challenge import ChallengeResult
    from singulant_proof.proof.evidence import EvidenceSet
    from singulant_proof.proof.support import SupportResult


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return digest[:32]


@dataclass(frozen=True)
class EvidenceReceipt:
    claim: str
    claim_display: str
    verdict: str
    support_strength: int
    challenge_strength: int
    data_quality: int
    observed_at: str
    observation_count: int
    support_observation_count: int
    challenge_observation_count: int
    context_observation_count: int
    chain: str
    token_address: str
    token_symbol: str | None
    attribution: str
    evidence_fingerprint: str
    receipt_id: str
    tgm_timeframe: str
    provenance: tuple[dict[str, Any], ...]
    challenge_conclusion: str | None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "claim_display": self.claim_display,
            "verdict": self.verdict,
            "support_strength": self.support_strength,
            "challenge_strength": self.challenge_strength,
            "data_quality": self.data_quality,
            "observed_at": self.observed_at,
            "observation_count": self.observation_count,
            "support_observation_count": self.support_observation_count,
            "challenge_observation_count": self.challenge_observation_count,
            "context_observation_count": self.context_observation_count,
            "chain": self.chain,
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "attribution": self.attribution,
            "evidence_fingerprint": self.evidence_fingerprint,
            "receipt_id": self.receipt_id,
            "tgm_timeframe": self.tgm_timeframe,
            "provenance": list(self.provenance),
            "challenge_conclusion": self.challenge_conclusion,
        }


def build_receipt(
    *,
    evidence: EvidenceSet,
    support: SupportResult,
    challenge: ChallengeResult,
    quality: int,
    verdict: Verdict,
) -> EvidenceReceipt:
    support_ids = {oid for item in support.case for oid in item.observation_ids}
    challenge_ids = {oid for item in challenge.case for oid in item.observation_ids}
    context_ids = {
        item.id
        for item in evidence.observations
        if item.role == "context" or item.id not in support_ids and item.id not in challenge_ids
    }
    observed_at = evidence.observed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    score_payload = {
        "evidence": evidence.canonical_payload(),
        "support_strength": support.strength,
        "challenge_strength": challenge.strength,
        "data_quality": quality,
        "verdict": verdict.value,
    }
    evidence_fp = fingerprint(score_payload)
    receipt_fp = fingerprint({**score_payload, "observed_at": observed_at})
    return EvidenceReceipt(
        claim=evidence.claim.id,
        claim_display=evidence.claim.display,
        verdict=verdict.value,
        support_strength=support.strength,
        challenge_strength=challenge.strength,
        data_quality=quality,
        observed_at=observed_at,
        observation_count=len(evidence.observations),
        support_observation_count=len(support_ids),
        challenge_observation_count=len(challenge_ids),
        context_observation_count=len(context_ids),
        chain=evidence.chain,
        token_address=evidence.token_address,
        token_symbol=evidence.context.token_symbol,
        attribution=ATTRIBUTION,
        evidence_fingerprint=evidence_fp,
        receipt_id=f"spr_{receipt_fp[:16]}",
        tgm_timeframe=evidence.tgm_timeframe,
        provenance=tuple(ref.as_public_dict() for ref in evidence.provenance),
        challenge_conclusion=challenge.conclusion,
    )
