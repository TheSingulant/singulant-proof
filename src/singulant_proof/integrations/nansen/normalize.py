"""Turn Nansen payloads into derived observations. Preserve nulls. No raw dumps."""

from __future__ import annotations

from typing import Any

from singulant_proof.integrations.nansen.schemas import (
    FRESH_WALLET_TIMEFRAMES,
    NETFLOW_WINDOWS,
    TGM_COHORTS,
    TGM_SUFFIXES,
    tgm_field,
)
from singulant_proof.integrations.nansen.types import NansenCallResult, ProvenanceRef
from singulant_proof.proof.claim import V1_CLAIM
from singulant_proof.proof.evidence import EvidenceSet, Observation, TokenContext, new_evidence_set


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value != "":
        return value
    return None


def _addresses_equal(left: str, right: str) -> bool:
    if left.startswith("0x") and right.startswith("0x"):
        return left.lower() == right.lower()
    return left == right


def select_netflow_row(data: list[Any], token_address: str, chain: str) -> dict[str, Any] | None:
    if not data:
        return None
    rows = [row for row in data if isinstance(row, dict)]
    matched = [
        row
        for row in rows
        if _addresses_equal(str(row.get("token_address") or ""), token_address)
        and (not row.get("chain") or str(row.get("chain")).lower() == chain.lower())
    ]
    if matched:
        return matched[0]
    # Fallback: address-only match when chain casing differs in unexpected ways.
    matched = [row for row in rows if _addresses_equal(str(row.get("token_address") or ""), token_address)]
    return matched[0] if matched else None


def select_tgm_row(data: list[Any]) -> dict[str, Any] | None:
    rows = [row for row in data if isinstance(row, dict)]
    return rows[0] if rows else None


def _window_label(field: str) -> str:
    return {
        "net_flow_1h_usd": "1h",
        "net_flow_24h_usd": "24h",
        "net_flow_7d_usd": "7d",
        "net_flow_30d_usd": "30d",
    }[field]


def normalize_netflow(
    result: NansenCallResult | None,
    *,
    chain: str,
    token_address: str,
) -> tuple[list[Observation], TokenContext, list[str]]:
    warnings: list[str] = []
    context = TokenContext()
    if result is None:
        warnings.append("NETFLOW_UNAVAILABLE")
        return [], context, warnings

    data = result.body.get("data")
    if not isinstance(data, list):
        warnings.append("NETFLOW_MALFORMED")
        return [], context, warnings

    row = select_netflow_row(data, token_address, chain)
    if row is None:
        warnings.append("NETFLOW_NO_ROW")
        return [], context, warnings

    context = TokenContext(
        token_address=_as_str(row.get("token_address")) or token_address,
        token_symbol=_as_str(row.get("token_symbol")),
        chain=_as_str(row.get("chain")) or chain,
        trader_count=_as_int(row.get("trader_count")),
        token_age_days=_as_int(row.get("token_age_days")),
        market_cap_usd=_as_number(row.get("market_cap_usd")),
        token_sectors=list(row.get("token_sectors") or []) if isinstance(row.get("token_sectors"), list) else [],
    )

    observations: list[Observation] = []
    for field in NETFLOW_WINDOWS:
        observations.append(
            Observation(
                id=f"nf:{_window_label(field)}",
                source="smart_money_netflow",
                field=field,
                value=_as_number(row.get(field)),
                unit="usd",
                window=_window_label(field),
                cohort="smart_money",
                role="primary",
            )
        )
    observations.append(
        Observation(
            id="nf:trader_count",
            source="smart_money_netflow",
            field="trader_count",
            value=float(context.trader_count) if context.trader_count is not None else None,
            unit="count",
            window="30d",
            cohort="smart_money",
            role="context",
        )
    )
    observations.append(
        Observation(
            id="nf:token_age_days",
            source="smart_money_netflow",
            field="token_age_days",
            value=float(context.token_age_days) if context.token_age_days is not None else None,
            unit="days",
            window=None,
            cohort=None,
            role="context",
        )
    )
    observations.append(
        Observation(
            id="nf:market_cap_usd",
            source="smart_money_netflow",
            field="market_cap_usd",
            value=context.market_cap_usd,
            unit="usd",
            window=None,
            cohort=None,
            role="context",
        )
    )
    return observations, context, warnings


def normalize_tgm(
    result: NansenCallResult | None,
    *,
    timeframe: str,
) -> tuple[list[Observation], list[str]]:
    warnings: list[str] = []
    if result is None:
        warnings.append("TGM_UNAVAILABLE")
        return [], warnings

    data = result.body.get("data")
    if not isinstance(data, list):
        warnings.append("TGM_MALFORMED")
        return [], warnings

    provider_warnings = result.body.get("warnings")
    if isinstance(provider_warnings, list):
        for item in provider_warnings:
            if isinstance(item, str) and item:
                warnings.append(f"TGM_PROVIDER:{item}")

    if timeframe not in FRESH_WALLET_TIMEFRAMES:
        warnings.append("TGM_FRESH_WALLETS_NULL_TIMEFRAME")

    row = select_tgm_row(data)
    if row is None:
        warnings.append("TGM_NO_ROW")
        return [], warnings

    observations: list[Observation] = []
    for cohort in TGM_COHORTS:
        net = tgm_field(cohort, "net_flow_usd")
        avg = tgm_field(cohort, "avg_flow_usd")
        count = tgm_field(cohort, "wallet_count")
        observations.append(
            Observation(
                id=f"tgm:{cohort}:net",
                source="tgm_flow_intelligence",
                field=net,
                value=_as_number(row.get(net)),
                unit="usd",
                window=timeframe,
                cohort=cohort,
                role="cohort",
            )
        )
        observations.append(
            Observation(
                id=f"tgm:{cohort}:avg",
                source="tgm_flow_intelligence",
                field=avg,
                value=_as_number(row.get(avg)),
                unit="usd",
                window=timeframe,
                cohort=cohort,
                role="context",
            )
        )
        observations.append(
            Observation(
                id=f"tgm:{cohort}:wallets",
                source="tgm_flow_intelligence",
                field=count,
                value=_as_number(row.get(count)),
                unit="count",
                window=timeframe,
                cohort=cohort,
                role="context",
            )
        )

    # Contract: exchange_wallet_count is always 0 — flag, do not interpret as empty cohort.
    warnings.append("TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO")
    if timeframe in FRESH_WALLET_TIMEFRAMES:
        warnings.append("TGM_FRESH_WALLET_COUNT_ALWAYS_ZERO")
    return observations, warnings


def build_evidence_set(
    *,
    chain: str,
    token_address: str,
    timeframe: str,
    netflow: NansenCallResult | None,
    tgm: NansenCallResult | None,
    extra_warnings: list[str] | None = None,
) -> EvidenceSet:
    nf_obs, context, nf_warn = normalize_netflow(netflow, chain=chain, token_address=token_address)
    tgm_obs, tgm_warn = normalize_tgm(tgm, timeframe=timeframe)
    provenance: list[ProvenanceRef] = []
    if netflow is not None:
        provenance.append(netflow.provenance)
    if tgm is not None:
        provenance.append(tgm.provenance)
    if context.token_address is None:
        context = TokenContext(
            token_address=token_address,
            token_symbol=context.token_symbol,
            chain=chain,
            trader_count=context.trader_count,
            token_age_days=context.token_age_days,
            market_cap_usd=context.market_cap_usd,
            token_sectors=context.token_sectors,
        )
    elif context.chain is None:
        context = TokenContext(
            token_address=context.token_address,
            token_symbol=context.token_symbol,
            chain=chain,
            trader_count=context.trader_count,
            token_age_days=context.token_age_days,
            market_cap_usd=context.market_cap_usd,
            token_sectors=context.token_sectors,
        )
    warnings = list(extra_warnings or []) + nf_warn + tgm_warn
    return new_evidence_set(
        claim=V1_CLAIM,
        chain=chain,
        token_address=token_address,
        context=context,
        observations=nf_obs + tgm_obs,
        provenance=provenance,
        warnings=warnings,
        tgm_timeframe=timeframe,
    )
