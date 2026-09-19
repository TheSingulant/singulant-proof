from singulant_proof.proof.support import evaluate_support
from tests.fixtures.synthetic import evidence


def test_non_positive_primary_is_zero_support() -> None:
    result = evaluate_support(evidence(nf_7d=-20_000, smart_trader=80_000))
    assert result.strength == 0


def test_null_primary_can_fallback_to_tgm_with_haircut() -> None:
    result = evaluate_support(evidence(nf_7d=None, smart_trader=200_000, nf_24h=None, market_cap_usd=None))
    assert result.used_fallback_primary is True
    assert result.strength > 0
    # Fallback 200k * 0.6 = 120k, no mcap → magnitude capped at 40, no persist, no second corroboration.
    assert result.strength <= 40 + 15 + 15 + 8


def test_does_not_add_nested_window_dollars() -> None:
    modest = evaluate_support(evidence(nf_7d=20_000, nf_24h=20_000, nf_1h=20_000, nf_30d=20_000, market_cap_usd=None, smart_trader=None, top_pnl=None, whale=None, trader_count=12))
    huge_nested = evaluate_support(evidence(nf_7d=20_000, nf_24h=5_000_000, nf_1h=5_000_000, nf_30d=5_000_000, market_cap_usd=None, smart_trader=None, top_pnl=None, whale=None, trader_count=12))
    assert modest.strength == huge_nested.strength


def test_tgm_smart_trader_is_sign_not_usd_add() -> None:
    without = evaluate_support(evidence(nf_7d=200_000, smart_trader=None, top_pnl=None, whale=None))
    tiny = evaluate_support(evidence(nf_7d=200_000, smart_trader=1.0, top_pnl=None, whale=None))
    huge = evaluate_support(evidence(nf_7d=200_000, smart_trader=9_000_000, top_pnl=None, whale=None))
    assert tiny.strength == huge.strength
    assert tiny.strength == without.strength + 12


def test_independent_cohorts_use_max_not_sum() -> None:
    both = evaluate_support(evidence(top_pnl=50_000, whale=50_000, smart_trader=None))
    pnl_only = evaluate_support(evidence(top_pnl=50_000, whale=None, smart_trader=None))
    assert both.strength == pnl_only.strength


def test_material_inflow_scores_higher_than_trace() -> None:
    trace = evaluate_support(evidence(nf_7d=500, nf_24h=None, smart_trader=None, top_pnl=None, whale=None, trader_count=None, market_cap_usd=None))
    material = evaluate_support(evidence(nf_7d=200_000, nf_24h=None, smart_trader=None, top_pnl=None, whale=None, trader_count=None, market_cap_usd=None))
    assert trace.strength < material.strength
    assert trace.strength <= 8
