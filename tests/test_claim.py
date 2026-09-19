import pytest

from singulant_proof.proof.claim import CLAIM_DISPLAY, CLAIM_ID, ClaimError, Verdict, parse_claim


def test_v1_claim_round_trip() -> None:
    claim = parse_claim(None)
    assert claim.id == CLAIM_ID
    assert claim.display == CLAIM_DISPLAY
    assert parse_claim(CLAIM_ID).id == CLAIM_ID


def test_rejects_freeform_and_other_ids() -> None:
    with pytest.raises(ClaimError):
        parse_claim("this token is going to moon")
    with pytest.raises(ClaimError):
        parse_claim("SMART_MONEY_IS_DISTRIBUTING_THIS_TOKEN")


def test_verdict_enum_surface() -> None:
    assert {v.value for v in Verdict} == {
        "SUPPORTED",
        "SUPPORTED_BUT_CONTESTED",
        "MIXED",
        "CONTRADICTED",
        "INSUFFICIENT_DATA",
    }
