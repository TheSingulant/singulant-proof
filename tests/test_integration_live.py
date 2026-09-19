"""Live Nansen integration. SKIP unless NANSEN_API_KEY is set.

Parent runs:

    NANSEN_API_KEY=... pytest tests/test_integration_live.py -q

Do not print the key. Do not persist raw provider dumps.
"""

from __future__ import annotations

import os

import pytest

from singulant_proof.api.app import collect_from_nansen
from singulant_proof.integrations.nansen.client import NansenClient
from singulant_proof.proof.adjudicator import run_proof

pytestmark = pytest.mark.skipif(
    not os.environ.get("NANSEN_API_KEY", "").strip(),
    reason="NANSEN_API_KEY not set; parent runs this with the key",
)

# AAVE on Ethereum — documented example on docs.nansen.ai (not a secret).
LIVE_CHAIN = "ethereum"
LIVE_TOKEN = "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"


def test_live_netflow_and_flow_intelligence_round_trip() -> None:
    key = os.environ["NANSEN_API_KEY"]
    with NansenClient(key) as client:
        netflow = client.smart_money_netflow(chains=[LIVE_CHAIN], token_address=LIVE_TOKEN)
        tgm = client.tgm_flow_intelligence(chain=LIVE_CHAIN, token_address=LIVE_TOKEN, timeframe="1d")
    assert netflow.status_code == 200
    assert tgm.status_code == 200
    assert isinstance(netflow.body.get("data"), list)
    assert isinstance(tgm.body.get("data"), list)
    assert netflow.provenance.provider == "nansen"
    assert tgm.provenance.endpoint == "/api/v1/tgm/flow-intelligence"
    # Credit headers are optional on some plans; when present they are not secrets.
    assert netflow.provenance.credits.request_id is None or isinstance(netflow.provenance.credits.request_id, str)


def test_live_verify_pipeline_emits_receipt_not_raw_dump() -> None:
    evidence, extras = collect_from_nansen(chain=LIVE_CHAIN, token_address=LIVE_TOKEN, timeframe="1d")
    result = run_proof(evidence)
    payload = result.as_public_dict()
    assert payload["claim"]["id"] == "SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN"
    assert payload["verdict"] in {
        "SUPPORTED",
        "SUPPORTED_BUT_CONTESTED",
        "MIXED",
        "CONTRADICTED",
        "INSUFFICIENT_DATA",
    }
    assert "pagination" not in str(payload)
    assert payload["evidence_receipt"]["attribution"] == "Powered by Nansen"
    assert extras is not None
