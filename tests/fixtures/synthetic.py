from __future__ import annotations

from datetime import datetime, timezone

from singulant_proof.integrations.nansen.types import CreditHeaders, ProvenanceRef
from singulant_proof.proof.claim import V1_CLAIM
from singulant_proof.proof.evidence import EvidenceSet, Observation, TokenContext, new_evidence_set


def provenance(endpoint: str = "/api/v1/smart-money/netflow") -> ProvenanceRef:
    return ProvenanceRef(
        provider="nansen",
        endpoint=endpoint,
        status_code=200,
        observed_at=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
        credits=CreditHeaders(
            credits_cost="1",
            credits_used="1",
            credits_remaining="99",
            request_id="req_test",
        ),
    )


def obs(
    oid: str,
    source: str,
    field: str,
    value: float | None,
    *,
    unit: str = "usd",
    window: str | None = None,
    cohort: str | None = None,
    role: str = "primary",
) -> Observation:
    return Observation(
        id=oid,
        source=source,
        field=field,
        value=value,
        unit=unit,
        window=window,
        cohort=cohort,
        role=role,  # type: ignore[arg-type]
    )


def evidence(
    *,
    nf_1h: float | None = 0.0,
    nf_24h: float | None = 50_000.0,
    nf_7d: float | None = 200_000.0,
    nf_30d: float | None = 80_000.0,
    trader_count: int | None = 12,
    token_age_days: int | None = 200,
    market_cap_usd: float | None = 50_000_000.0,
    smart_trader: float | None = 40_000.0,
    top_pnl: float | None = 10_000.0,
    whale: float | None = 5_000.0,
    exchange: float | None = 0.0,
    fresh: float | None = None,
    public_figure: float | None = None,
    warnings: tuple[str, ...] = (),
    timeframe: str = "1d",
    observed_at: datetime | None = None,
) -> EvidenceSet:
    context = TokenContext(
        token_address="0xabc",
        token_symbol="TST",
        chain="ethereum",
        trader_count=trader_count,
        token_age_days=token_age_days,
        market_cap_usd=market_cap_usd,
        token_sectors=["test"],
    )
    observations = [
        obs("nf:1h", "smart_money_netflow", "net_flow_1h_usd", nf_1h, window="1h", cohort="smart_money"),
        obs("nf:24h", "smart_money_netflow", "net_flow_24h_usd", nf_24h, window="24h", cohort="smart_money"),
        obs("nf:7d", "smart_money_netflow", "net_flow_7d_usd", nf_7d, window="7d", cohort="smart_money"),
        obs("nf:30d", "smart_money_netflow", "net_flow_30d_usd", nf_30d, window="30d", cohort="smart_money"),
        obs("nf:trader_count", "smart_money_netflow", "trader_count", float(trader_count) if trader_count is not None else None, unit="count", window="30d", cohort="smart_money", role="context"),
        obs("nf:token_age_days", "smart_money_netflow", "token_age_days", float(token_age_days) if token_age_days is not None else None, unit="days", role="context"),
        obs("nf:market_cap_usd", "smart_money_netflow", "market_cap_usd", market_cap_usd, role="context"),
        obs("tgm:smart_trader:net", "tgm_flow_intelligence", "smart_trader_net_flow_usd", smart_trader, window=timeframe, cohort="smart_trader", role="cohort"),
        obs("tgm:top_pnl:net", "tgm_flow_intelligence", "top_pnl_net_flow_usd", top_pnl, window=timeframe, cohort="top_pnl", role="cohort"),
        obs("tgm:whale:net", "tgm_flow_intelligence", "whale_net_flow_usd", whale, window=timeframe, cohort="whale", role="cohort"),
        obs("tgm:exchange:net", "tgm_flow_intelligence", "exchange_net_flow_usd", exchange, window=timeframe, cohort="exchange", role="cohort"),
        obs("tgm:fresh_wallets:net", "tgm_flow_intelligence", "fresh_wallets_net_flow_usd", fresh, window=timeframe, cohort="fresh_wallets", role="cohort"),
        obs("tgm:public_figure:net", "tgm_flow_intelligence", "public_figure_net_flow_usd", public_figure, window=timeframe, cohort="public_figure", role="cohort"),
    ]
    return new_evidence_set(
        claim=V1_CLAIM,
        chain="ethereum",
        token_address="0xabc",
        context=context,
        observations=observations,
        provenance=(provenance(), provenance("/api/v1/tgm/flow-intelligence")),
        warnings=warnings,
        tgm_timeframe=timeframe,
        observed_at=observed_at or datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
    )
