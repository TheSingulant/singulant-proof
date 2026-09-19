from singulant_proof import ATTRIBUTION
from singulant_proof.proof.adjudicator import run_proof
from tests.fixtures.synthetic import evidence


def test_receipt_is_share_card_ready() -> None:
    result = run_proof(evidence())
    receipt = result.evidence_receipt.as_public_dict()
    for key in (
        "claim",
        "claim_display",
        "verdict",
        "support_strength",
        "challenge_strength",
        "data_quality",
        "observed_at",
        "observation_count",
        "support_observation_count",
        "challenge_observation_count",
        "chain",
        "token_address",
        "attribution",
        "evidence_fingerprint",
        "receipt_id",
    ):
        assert key in receipt
        assert receipt[key] is not None or key == "token_symbol"
    assert receipt["attribution"] == ATTRIBUTION
    assert receipt["claim"] == "SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN"
    assert "0xabc" == receipt["token_address"]
    dumped = str(receipt)
    assert "apikey" not in dumped.lower()
    assert "raw" not in dumped
    for ref in receipt["provenance"]:
        assert "body" not in ref
        assert ref["provider"] == "nansen"


def test_public_api_shape_has_required_fields() -> None:
    payload = run_proof(evidence()).as_public_dict()
    for key in (
        "claim",
        "chain",
        "token",
        "stages_completed",
        "support_case",
        "challenge_case",
        "support_strength",
        "challenge_strength",
        "data_quality",
        "verdict",
        "evidence_receipt",
        "warnings",
    ):
        assert key in payload
    assert payload["stages_completed"][-1] == "RECEIPT"
    assert "data" not in payload
