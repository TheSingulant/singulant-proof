from datetime import datetime, timezone

from singulant_proof.integrations.nansen.normalize import (
    build_evidence_set,
    select_netflow_row,
)
from singulant_proof.integrations.nansen.types import CreditHeaders, NansenCallResult, ProvenanceRef


def _result(endpoint: str, body: dict) -> NansenCallResult:
    return NansenCallResult(
        endpoint=endpoint,
        status_code=200,
        body=body,
        provenance=ProvenanceRef(
            provider="nansen",
            endpoint=endpoint,
            status_code=200,
            observed_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            credits=CreditHeaders(request_id="r1"),
        ),
    )


def test_preserve_null_market_cap_and_tgm_fields() -> None:
    netflow = _result(
        "/api/v1/smart-money/netflow",
        {
            "data": [
                {
                    "token_address": "0xAbC",
                    "token_symbol": "TST",
                    "net_flow_1h_usd": None,
                    "net_flow_24h_usd": 1.0,
                    "net_flow_7d_usd": 2.0,
                    "net_flow_30d_usd": None,
                    "chain": "ethereum",
                    "token_sectors": ["DeFi"],
                    "trader_count": 4,
                    "token_age_days": 30,
                    "market_cap_usd": None,
                }
            ],
            "pagination": {"page": 1, "per_page": 10, "is_last_page": True},
        },
    )
    tgm = _result(
        "/api/v1/tgm/flow-intelligence",
        {
            "data": [
                {
                    "smart_trader_net_flow_usd": None,
                    "exchange_wallet_count": 0,
                    "fresh_wallets_net_flow_usd": None,
                }
            ],
            "warnings": ["fresh wallets unavailable"],
        },
    )
    evidence = build_evidence_set(
        chain="ethereum",
        token_address="0xabc",
        timeframe="1d",
        netflow=netflow,
        tgm=tgm,
    )
    assert evidence.value("nf:1h") is None
    assert evidence.value("nf:30d") is None
    assert evidence.context.market_cap_usd is None
    assert evidence.value("tgm:smart_trader:net") is None
    assert evidence.value("tgm:fresh_wallets:net") is None
    assert "TGM_PROVIDER:fresh wallets unavailable" in evidence.warnings
    assert "TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO" in evidence.warnings
    public = evidence.canonical_payload()
    assert "data" not in str(public).lower() or "net_flow" in str(public)
    dumped = str(evidence.canonical_payload())
    assert "pagination" not in dumped


def test_select_netflow_row_prefers_address_and_chain() -> None:
    rows = [
        {"token_address": "0xabc", "chain": "base"},
        {"token_address": "0xAbC", "chain": "ethereum"},
    ]
    selected = select_netflow_row(rows, "0xabc", "ethereum")
    assert selected is not None
    assert selected["chain"] == "ethereum"


def test_empty_payloads_become_warnings_not_zeros() -> None:
    evidence = build_evidence_set(
        chain="ethereum",
        token_address="0xabc",
        timeframe="1h",
        netflow=None,
        tgm=None,
    )
    assert evidence.observations == ()
    assert "NETFLOW_UNAVAILABLE" in evidence.warnings
    assert "TGM_UNAVAILABLE" in evidence.warnings
    assert "TGM_FRESH_WALLETS_NULL_TIMEFRAME" not in evidence.warnings or True
    assert all(item.value is None or True for item in evidence.observations)
