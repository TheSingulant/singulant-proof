"""Data-quality engine. Missing data is a deduction, never a bullish fill."""

from __future__ import annotations

from dataclasses import dataclass

from singulant_proof.proof.evidence import EvidenceSet

QUALITY_FLOOR = 40


@dataclass(frozen=True)
class QualityResult:
    score: int
    deductions: tuple[tuple[str, int], ...]


def _has_source(evidence: EvidenceSet, source: str) -> bool:
    return any(item.source == source for item in evidence.observations)


def evaluate_quality(evidence: EvidenceSet) -> QualityResult:
    deductions: list[tuple[str, int]] = []
    warnings = set(evidence.warnings)

    if "NETFLOW_UNAVAILABLE" in warnings or "NETFLOW_MALFORMED" in warnings:
        deductions.append(("netflow_unavailable", 40))
    elif "NETFLOW_NO_ROW" in warnings:
        deductions.append(("netflow_no_row", 30))

    if "TGM_UNAVAILABLE" in warnings or "TGM_MALFORMED" in warnings:
        deductions.append(("tgm_unavailable", 25))
    elif "TGM_NO_ROW" in warnings:
        deductions.append(("tgm_no_row", 15))

    nf_7d = evidence.value("nf:7d")
    tgm_sm = evidence.value("tgm:smart_trader:net")
    if nf_7d is None and tgm_sm is None and "NETFLOW_UNAVAILABLE" not in warnings and "NETFLOW_NO_ROW" not in warnings:
        deductions.append(("primary_7d_null", 20))
    elif nf_7d is None and tgm_sm is None:
        pass
    elif nf_7d is None and tgm_sm is not None:
        deductions.append(("primary_7d_null_fallback", 12))

    if _has_source(evidence, "smart_money_netflow") and evidence.value("nf:24h") is None:
        deductions.append(("nf_24h_null", 8))

    if evidence.context.market_cap_usd is None:
        deductions.append(("market_cap_null", 10))
    if evidence.context.trader_count is None:
        deductions.append(("trader_count_null", 8))
    elif evidence.context.trader_count < 3:
        deductions.append(("trader_count_thin", 10))
    if evidence.context.token_age_days is None:
        deductions.append(("token_age_null", 5))
    elif evidence.context.token_age_days < 7:
        deductions.append(("token_age_new", 12))

    if _has_source(evidence, "tgm_flow_intelligence") and tgm_sm is None and "TGM_NO_ROW" not in warnings:
        deductions.append(("tgm_smart_trader_null", 8))

    provider_hits = [w for w in evidence.warnings if w.startswith("TGM_PROVIDER:")]
    if provider_hits:
        deductions.append(("tgm_provider_warnings", min(15, 5 * len(provider_hits))))

    total = 100 - sum(amount for _, amount in deductions)
    return QualityResult(score=max(0, min(100, total)), deductions=tuple(deductions))
