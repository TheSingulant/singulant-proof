"""Request/response field maps from the verified Nansen OpenAPI (2026-09-19).

Authoritative source: docs.nansen.ai + uploads/NANSEN_CONTRACTS.md.
Preserve nulls. Do not invent fields that are not in the live contract.
"""

from __future__ import annotations

from typing import Any, Final

NANSEN_BASE_URL: Final = "https://api.nansen.ai"
NETFLOW_PATH: Final = "/api/v1/smart-money/netflow"
FLOW_INTELLIGENCE_PATH: Final = "/api/v1/tgm/flow-intelligence"

# Smart Money netflow `chains` enum (OpenAPI SmartMoneyChain).
SMART_MONEY_CHAINS: Final[frozenset[str]] = frozenset(
    {
        "all",
        "arbitrum",
        "avalanche",
        "base",
        "bnb",
        "ethereum",
        "hyperevm",
        "iotaevm",
        "linea",
        "mantle",
        "monad",
        "optimism",
        "plasma",
        "polygon",
        "robinhood",
        "sei",
        "solana",
        "sonic",
    }
)

# TGM flow-intelligence `chain` enum (OpenAPI TGMFlowIntelligenceChain).
TGM_CHAINS: Final[frozenset[str]] = frozenset(
    {
        "arbitrum",
        "avalanche",
        "base",
        "bnb",
        "ethereum",
        "hyperevm",
        "injective",
        "linea",
        "mantle",
        "mantra",
        "monad",
        "near",
        "optimism",
        "plasma",
        "polygon",
        "robinhood",
        "sei",
        "solana",
        "sonic",
        "starknet",
        "sui",
        "ton",
        "tron",
    }
)

TGM_TIMEFRAMES: Final[frozenset[str]] = frozenset({"5m", "1h", "6h", "12h", "1d", "7d"})
FRESH_WALLET_TIMEFRAMES: Final[frozenset[str]] = frozenset({"1d", "7d"})

SMART_MONEY_LABELS: Final[tuple[str, ...]] = (
    "Fund",
    "Smart Trader",
    "30D Smart Trader",
    "90D Smart Trader",
    "180D Smart Trader",
    "Smart HL Perps Trader",
)

# Netflow row fields. market_cap_usd is optional in the contract (not required).
NETFLOW_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "token_address",
    "token_symbol",
    "net_flow_1h_usd",
    "net_flow_24h_usd",
    "net_flow_7d_usd",
    "net_flow_30d_usd",
    "chain",
    "token_sectors",
    "trader_count",
    "token_age_days",
)
NETFLOW_OPTIONAL_FIELDS: Final[tuple[str, ...]] = ("market_cap_usd",)
NETFLOW_WINDOWS: Final[tuple[str, ...]] = (
    "net_flow_1h_usd",
    "net_flow_24h_usd",
    "net_flow_7d_usd",
    "net_flow_30d_usd",
)

# TGM cohort prefixes. All values are nullable. exchange_wallet_count is always 0.
# fresh_wallets_* only populated for 1d/7d; wallet_count is always 0 on those windows.
TGM_COHORTS: Final[tuple[str, ...]] = (
    "smart_trader",
    "top_pnl",
    "whale",
    "exchange",
    "fresh_wallets",
    "public_figure",
)
TGM_SUFFIXES: Final[tuple[str, ...]] = ("net_flow_usd", "avg_flow_usd", "wallet_count")

# Known contract caveats — surface as warnings, never as invented numbers.
CONTRACT_NOTES: Final[tuple[str, ...]] = (
    "exchange_wallet_count is always 0 on TGM flow-intelligence; do not treat it as inactivity.",
    "fresh_wallets_* fields are only available for timeframe 1d and 7d.",
    "fresh_wallets_wallet_count is always 0 on 1d/7d (null on shorter timeframes).",
    "Netflow windows 1h ⊂ 24h ⊂ 7d ⊂ 30d are nested; do not add their USD as independent evidence.",
    "TGM smart_trader and Smart Money netflow describe overlapping populations; corroborate, do not sum.",
)

CREDIT_HEADER_MAP: Final[dict[str, str]] = {
    "credits_cost": "x-nansen-credits-cost",
    "credits_used": "x-nansen-credits-used",
    "credits_remaining": "x-nansen-credits-remaining",
    "rate_limit_limit": "ratelimit-limit",
    "rate_limit_remaining": "ratelimit-remaining",
    "rate_limit_reset": "ratelimit-reset",
    "request_id": "x-request-id",
}


def tgm_field(cohort: str, suffix: str) -> str:
    return f"{cohort}_{suffix}"


def empty_tgm_row() -> dict[str, Any]:
    return {tgm_field(c, s): None for c in TGM_COHORTS for s in TGM_SUFFIXES}
