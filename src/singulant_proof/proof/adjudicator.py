"""Deterministic adjudicator. First matching rule wins. See scoring.md."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from singulant_proof.proof.challenge import ChallengeResult, evaluate_challenge
from singulant_proof.proof.claim import Claim, Verdict
from singulant_proof.proof.evidence import CaseItem, EvidenceSet
from singulant_proof.proof.quality import QUALITY_FLOOR, QualityResult, evaluate_quality
from singulant_proof.proof.receipt import EvidenceReceipt, build_receipt
from singulant_proof.proof.support import SupportResult, evaluate_support

SUPPORT_MIN = 25
SUPPORT_CLEAR = 55
CHALLENGE_CONTEST = 25
CHALLENGE_STRONG = 55
CHALLENGE_DOMINANCE_GAP = 10

PIPELINE_STAGES = (
    "CLAIM",
    "COLLECT",
    "NORMALIZE",
    "SUPPORT",
    "CHALLENGE",
    "QUALITY",
    "ADJUDICATE",
    "RECEIPT",
)


@dataclass(frozen=True)
class ProofResult:
    claim: Claim
    chain: str
    token: dict[str, Any]
    stages_completed: tuple[str, ...]
    support_case: tuple[CaseItem, ...]
    challenge_case: tuple[CaseItem, ...]
    support_strength: int
    challenge_strength: int
    data_quality: int
    verdict: Verdict
    evidence_receipt: EvidenceReceipt
    warnings: tuple[str, ...]
    quality_deductions: tuple[tuple[str, int], ...]
    challenge_conclusion: str | None
    synthetic: bool = False

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.as_public_dict(),
            "chain": self.chain,
            "token": self.token,
            "stages_completed": list(self.stages_completed),
            "support_case": [item.as_public_dict() for item in self.support_case],
            "challenge_case": [item.as_public_dict() for item in self.challenge_case],
            "support_strength": self.support_strength,
            "challenge_strength": self.challenge_strength,
            "data_quality": self.data_quality,
            "verdict": self.verdict.value,
            "evidence_receipt": self.evidence_receipt.as_public_dict(),
            "warnings": list(self.warnings),
            "synthetic": self.synthetic,
        }


def adjudicate(support: int, challenge: int, quality: int) -> Verdict:
    if quality < QUALITY_FLOOR:
        return Verdict.INSUFFICIENT_DATA
    if support < SUPPORT_MIN and challenge < 40:
        return Verdict.INSUFFICIENT_DATA
    if challenge >= CHALLENGE_STRONG and challenge >= support + CHALLENGE_DOMINANCE_GAP:
        return Verdict.CONTRADICTED
    if support >= SUPPORT_CLEAR and challenge < CHALLENGE_CONTEST:
        return Verdict.SUPPORTED
    if support >= SUPPORT_CLEAR and challenge >= CHALLENGE_CONTEST:
        return Verdict.SUPPORTED_BUT_CONTESTED
    return Verdict.MIXED


def run_engines(evidence: EvidenceSet) -> tuple[SupportResult, ChallengeResult, QualityResult, Verdict]:
    support = evaluate_support(evidence)
    challenge = evaluate_challenge(evidence)
    quality = evaluate_quality(evidence)
    verdict = adjudicate(support.strength, challenge.strength, quality.score)
    return support, challenge, quality, verdict


def run_proof(
    evidence: EvidenceSet,
    *,
    stages_completed: tuple[str, ...] = PIPELINE_STAGES,
    extra_warnings: list[str] | None = None,
    synthetic: bool = False,
) -> ProofResult:
    support, challenge, quality, verdict = run_engines(evidence)
    warnings = list(evidence.warnings)
    if extra_warnings:
        warnings.extend(extra_warnings)
    if synthetic:
        warnings.append("SYNTHETIC_EVIDENCE: not a live Nansen observation")
    receipt = build_receipt(
        evidence=evidence,
        support=support,
        challenge=challenge,
        quality=quality.score,
        verdict=verdict,
    )
    return ProofResult(
        claim=evidence.claim,
        chain=evidence.chain,
        token=evidence.context.as_public_dict(),
        stages_completed=stages_completed,
        support_case=support.case,
        challenge_case=challenge.case,
        support_strength=support.strength,
        challenge_strength=challenge.strength,
        data_quality=quality.score,
        verdict=verdict,
        evidence_receipt=receipt,
        warnings=tuple(warnings),
        quality_deductions=quality.deductions,
        challenge_conclusion=challenge.conclusion,
        synthetic=synthetic,
    )
