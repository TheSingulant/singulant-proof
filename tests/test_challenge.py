from singulant_proof.proof.challenge import NO_MATERIAL_CONTRADICTORY_EVIDENCE, evaluate_challenge
from tests.fixtures.synthetic import evidence


def test_no_material_contradictory_evidence() -> None:
    result = evaluate_challenge(
        evidence(
            nf_7d=200_000,
            nf_24h=20_000,
            nf_1h=1_000,
            nf_30d=10_000,
            smart_trader=10_000,
            top_pnl=1_000,
            whale=1_000,
            exchange=0,
            fresh=None,
            public_figure=None,
        )
    )
    assert result.conclusion == NO_MATERIAL_CONTRADICTORY_EVIDENCE
    assert result.case[0].title == NO_MATERIAL_CONTRADICTORY_EVIDENCE
    assert result.strength < 15


def test_negative_7d_is_primary_contradiction() -> None:
    result = evaluate_challenge(evidence(nf_7d=-80_000, smart_trader=-80_000))
    assert result.strength >= 30
    assert result.conclusion is None
    # Same-population TGM must not stack on an already-negative 7d.
    assert all("skipped" in item.body.lower() or item.weight == 0 or item.title != "Smart Money inconsistency (TGM vs netflow)" for item in result.case if item.title.startswith("Smart Money inconsistency"))


def test_no_double_count_1h_when_24h_already_negative() -> None:
    without_1h = evaluate_challenge(evidence(nf_7d=200_000, nf_24h=-50_000, nf_1h=None, smart_trader=10_000, top_pnl=1_000, whale=1_000, exchange=0, fresh=None))
    with_1h = evaluate_challenge(evidence(nf_7d=200_000, nf_24h=-50_000, nf_1h=-50_000, smart_trader=10_000, top_pnl=1_000, whale=1_000, exchange=0, fresh=None))
    assert without_1h.strength == with_1h.strength


def test_1h_material_reversal_only_if_24h_not_negative() -> None:
    result = evaluate_challenge(evidence(nf_7d=200_000, nf_24h=10_000, nf_1h=-20_000, smart_trader=10_000, top_pnl=1_000, whale=1_000, exchange=0, fresh=None))
    reversal = next(item for item in result.case if item.title.startswith("Primary"))
    assert reversal.weight == 8


def test_independent_cohort_max_not_sum() -> None:
    both = evaluate_challenge(evidence(top_pnl=-40_000, whale=-40_000, public_figure=-40_000, nf_7d=200_000, nf_24h=10_000, exchange=0, fresh=None, smart_trader=10_000))
    pnl = evaluate_challenge(evidence(top_pnl=-40_000, whale=None, public_figure=None, nf_7d=200_000, nf_24h=10_000, exchange=0, fresh=None, smart_trader=10_000))
    assert both.strength == pnl.strength


def test_exchange_inflow_ignores_wallet_count() -> None:
    result = evaluate_challenge(evidence(exchange=25_000, nf_7d=200_000, nf_24h=10_000, smart_trader=10_000, top_pnl=1_000, whale=1_000, fresh=None))
    item = next(item for item in result.case if item.title == "Exchange inflow")
    assert item.weight == 12
    assert "wallet_count" in item.body
