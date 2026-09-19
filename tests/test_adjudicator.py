from singulant_proof.proof.adjudicator import adjudicate, run_proof
from singulant_proof.proof.claim import Verdict
from tests.fixtures.synthetic import evidence


def test_quality_floor() -> None:
    assert adjudicate(90, 0, 39) == Verdict.INSUFFICIENT_DATA


def test_insufficient_when_neither_side_clears() -> None:
    assert adjudicate(20, 20, 80) == Verdict.INSUFFICIENT_DATA


def test_contradicted_requires_dominance() -> None:
    assert adjudicate(40, 55, 80) == Verdict.CONTRADICTED
    assert adjudicate(50, 55, 80) == Verdict.MIXED


def test_supported_requires_clear_support_and_weak_challenge() -> None:
    assert adjudicate(55, 24, 80) == Verdict.SUPPORTED
    assert adjudicate(55, 25, 80) == Verdict.SUPPORTED_BUT_CONTESTED
    assert adjudicate(54, 10, 80) == Verdict.MIXED


def test_supported_but_contested_from_live_shaped_evidence() -> None:
    result = run_proof(
        evidence(
            nf_7d=400_000,
            nf_24h=80_000,
            smart_trader=50_000,
            top_pnl=-80_000,
            whale=-20_000,
            exchange=25_000,
            trader_count=14,
            market_cap_usd=20_000_000,
        )
    )
    assert result.verdict in {Verdict.SUPPORTED_BUT_CONTESTED, Verdict.MIXED, Verdict.SUPPORTED}
    assert result.support_strength >= 55


def test_contradicted_from_distribution() -> None:
    result = run_proof(
        evidence(
            nf_7d=-200_000,
            nf_24h=-80_000,
            nf_30d=-300_000,
            smart_trader=-50_000,
            top_pnl=-40_000,
            whale=-40_000,
            exchange=50_000,
            trader_count=20,
            market_cap_usd=10_000_000,
        )
    )
    assert result.verdict == Verdict.CONTRADICTED
    assert result.support_strength == 0
    assert result.challenge_strength >= 55


def test_insufficient_empty_evidence() -> None:
    result = run_proof(evidence(nf_7d=None, nf_24h=None, nf_1h=None, nf_30d=None, smart_trader=None, top_pnl=None, whale=None, exchange=None, trader_count=None, token_age_days=None, market_cap_usd=None, warnings=("NETFLOW_NO_ROW", "TGM_NO_ROW")))
    assert result.verdict == Verdict.INSUFFICIENT_DATA
    assert result.data_quality < 40
