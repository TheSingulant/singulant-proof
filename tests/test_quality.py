from singulant_proof.proof.quality import evaluate_quality
from tests.fixtures.synthetic import evidence


def test_full_context_is_high_quality() -> None:
    score = evaluate_quality(evidence()).score
    assert score >= 90


def test_missing_both_providers_is_low_quality() -> None:
    result = evaluate_quality(evidence(warnings=("NETFLOW_UNAVAILABLE", "TGM_UNAVAILABLE"), nf_7d=None, smart_trader=None, trader_count=None, token_age_days=None, market_cap_usd=None))
    assert result.score < 40


def test_thin_and_new_token_are_deducted() -> None:
    healthy = evaluate_quality(evidence()).score
    weak = evaluate_quality(evidence(trader_count=1, token_age_days=2, market_cap_usd=None)).score
    assert weak < healthy
    assert weak <= healthy - 10 - 12 - 10


def test_contract_caveats_are_not_quality_hits() -> None:
    base = evaluate_quality(evidence()).score
    flagged = evaluate_quality(
        evidence(warnings=("TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO", "TGM_FRESH_WALLET_COUNT_ALWAYS_ZERO"))
    ).score
    assert flagged == base
