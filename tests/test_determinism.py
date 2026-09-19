from datetime import datetime, timezone

from singulant_proof.proof.adjudicator import run_engines, run_proof
from tests.fixtures.synthetic import evidence


def test_same_evidence_same_scores_and_verdict() -> None:
    first = evidence()
    second = evidence()
    a = run_engines(first)
    b = run_engines(second)
    assert a[0].strength == b[0].strength
    assert a[1].strength == b[1].strength
    assert a[2].score == b[2].score
    assert a[3] == b[3]


def test_observed_at_does_not_change_scores() -> None:
    early = evidence(observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    late = evidence(observed_at=datetime(2026, 9, 19, tzinfo=timezone.utc))
    a = run_proof(early)
    b = run_proof(late)
    assert a.support_strength == b.support_strength
    assert a.challenge_strength == b.challenge_strength
    assert a.data_quality == b.data_quality
    assert a.verdict == b.verdict
    assert a.evidence_receipt.evidence_fingerprint == b.evidence_receipt.evidence_fingerprint
    assert a.evidence_receipt.receipt_id != b.evidence_receipt.receipt_id


def test_repeated_run_proof_is_stable() -> None:
    ev = evidence(nf_7d=-120_000, nf_24h=-20_000, top_pnl=-30_000, exchange=40_000)
    results = [run_proof(ev) for _ in range(5)]
    keys = {(r.support_strength, r.challenge_strength, r.data_quality, r.verdict) for r in results}
    assert len(keys) == 1
