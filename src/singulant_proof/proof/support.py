"""Support engine — evidence that Smart Money is accumulating. No nested-window add."""

from __future__ import annotations

from dataclasses import dataclass

from singulant_proof.proof.evidence import CaseItem, EvidenceSet

MATERIAL_USD = 10_000.0
STRONG_USD = 100_000.0
MCAP_MATERIAL = 0.001
MCAP_STRONG = 0.01
FALLBACK_HAIRCUT = 0.6


@dataclass(frozen=True)
class SupportResult:
    strength: int
    case: tuple[CaseItem, ...]
    used_fallback_primary: bool


def _clamp(value: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(value))))


def _interpolate(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    if x1 <= x0:
        return y1
    t = max(0.0, min(1.0, (x - x0) / (x1 - x0)))
    return y0 + t * (y1 - y0)


def _usd(evidence: EvidenceSet, observation_id: str) -> float | None:
    return evidence.value(observation_id)


def _magnitude(primary: float, market_cap: float | None) -> tuple[int, str, bool]:
    if primary <= 0:
        return 0, "Primary window is not a net inflow.", False
    if primary < MATERIAL_USD:
        return 8, (
            f"7d Smart Money netflow is ${primary:,.0f}, below the ${MATERIAL_USD:,.0f} material floor."
        ), False
    material = True
    if market_cap is not None and market_cap > 0:
        ratio = primary / market_cap
        if ratio >= MCAP_STRONG and primary >= STRONG_USD:
            score = 50
        elif ratio >= MCAP_MATERIAL:
            score = _interpolate(ratio, MCAP_MATERIAL, MCAP_STRONG, 25, 50)
        else:
            score = _interpolate(primary, MATERIAL_USD, STRONG_USD, 10, 25)
        body = (
            f"7d Smart Money netflow ${primary:,.0f} is {ratio * 100:.3f}% of reported market cap "
            f"(${market_cap:,.0f}). Magnitude uses the 7d window only."
        )
        return _clamp(score, 0, 50), body, material
    score = 40 if primary >= STRONG_USD else _interpolate(primary, MATERIAL_USD, STRONG_USD, 10, 40)
    body = (
        f"7d Smart Money netflow ${primary:,.0f}. Market cap is null, so magnitude is capped at 40."
    )
    return _clamp(score, 0, 40), body, material


def evaluate_support(evidence: EvidenceSet) -> SupportResult:
    nf_7d = _usd(evidence, "nf:7d")
    nf_24h = _usd(evidence, "nf:24h")
    tgm_sm = _usd(evidence, "tgm:smart_trader:net")
    top_pnl = _usd(evidence, "tgm:top_pnl:net")
    whale = _usd(evidence, "tgm:whale:net")
    traders = evidence.context.trader_count
    mcap = evidence.context.market_cap_usd

    used_fallback = False
    primary = nf_7d
    primary_ids = ["nf:7d"]
    if primary is None and tgm_sm is not None:
        primary = tgm_sm * FALLBACK_HAIRCUT
        used_fallback = True
        primary_ids = ["tgm:smart_trader:net"]

    if primary is None or primary <= 0:
        item = CaseItem(
            title="No supporting accumulation in the primary window",
            body=(
                "Support is 0 because 7d Smart Money netflow is missing or not positive. "
                "TGM smart-trader flow is not added on top of a non-positive primary."
            ),
            polarity="support",
            observation_ids=tuple(primary_ids),
            material=False,
            weight=0,
        )
        return SupportResult(strength=0, case=(item,), used_fallback_primary=used_fallback)

    items: list[CaseItem] = []
    mag, mag_body, mag_material = _magnitude(primary, None if used_fallback else mcap)
    items.append(
        CaseItem(
            title="Primary accumulation window (7d, not summed)",
            body=mag_body + (" Fallback primary from TGM smart_trader with 0.6 haircut." if used_fallback else ""),
            polarity="support",
            observation_ids=tuple(primary_ids),
            material=mag_material,
            weight=mag,
        )
    )

    persist = 0
    persist_body = "24h netflow is null — no persistence credit."
    persist_material = False
    if used_fallback:
        persist_body = "Persistence is reserved for the nested 24h Smart Money window; unused on TGM fallback."
    elif nf_24h is None:
        persist = 0
    elif nf_24h > 0:
        persist = 15
        persist_material = True
        persist_body = (
            f"24h Smart Money netflow is ${nf_24h:,.0f} (sign only). "
            "USD is not added to the 7d magnitude."
        )
    elif nf_24h == 0:
        persist = 5
        persist_body = "24h Smart Money netflow is flat. Partial persistence only."
    else:
        persist = 0
        persist_body = (
            f"24h Smart Money netflow is ${nf_24h:,.0f}. Recent distribution blocks persistence credit."
        )
    items.append(
        CaseItem(
            title="Persistence (sign of 24h, not dollars)",
            body=persist_body,
            polarity="support",
            observation_ids=("nf:24h",),
            material=persist_material,
            weight=persist,
        )
    )

    if traders is None:
        breadth, breadth_body, breadth_mat = 0, "trader_count is null — no breadth credit.", False
    elif traders < 3:
        breadth, breadth_body, breadth_mat = 3, f"Only {traders} Smart Money traders in 30d — thin breadth.", False
    elif traders < 10:
        breadth = _clamp(_interpolate(traders, 3, 10, 6, 12), 0, 15)
        breadth_body, breadth_mat = f"{traders} Smart Money traders in 30d.", True
    else:
        breadth, breadth_body, breadth_mat = 15, f"{traders} Smart Money traders in 30d — meaningful breadth.", True
    items.append(
        CaseItem(
            title="Breadth (trader_count)",
            body=breadth_body,
            polarity="support",
            observation_ids=("nf:trader_count",),
            material=breadth_mat,
            weight=breadth,
        )
    )

    if used_fallback:
        corr, corr_body = 0, "TGM smart_trader was the fallback primary — not counted again as corroboration."
        corr_mat = False
    elif tgm_sm is None:
        corr, corr_body, corr_mat = 0, "TGM smart_trader netflow is null — no corroboration.", False
    elif tgm_sm > 0:
        corr, corr_body, corr_mat = 12, "TGM smart_trader netflow is positive (sign only; USD not added to netflow).", True
    elif tgm_sm == 0:
        corr, corr_body, corr_mat = 4, "TGM smart_trader netflow is flat.", False
    else:
        corr, corr_body, corr_mat = 0, "TGM smart_trader netflow is negative — no corroboration.", False
    items.append(
        CaseItem(
            title="Smart Money corroboration (TGM sign only)",
            body=corr_body,
            polarity="support",
            observation_ids=("tgm:smart_trader:net",),
            material=corr_mat,
            weight=corr,
        )
    )

    cohort_options: list[tuple[int, str, tuple[str, ...], bool]] = []
    if top_pnl is not None and top_pnl > 0:
        cohort_options.append((8, "Top PnL cohort is a net buyer (independent of Smart Money).", ("tgm:top_pnl:net",), True))
    if whale is not None and whale > 0:
        cohort_options.append((6, "Whale cohort is a net buyer (independent of Smart Money).", ("tgm:whale:net",), True))
    if cohort_options:
        cohort_options.sort(key=lambda item: (-item[0], item[2][0]))
        weight, body, ids, material = cohort_options[0]
    else:
        weight, body, ids, material = 0, "No independent top-PnL or whale inflow. Public figure is context only.", (), False
    items.append(
        CaseItem(
            title="Independent cohort (max, not sum)",
            body=body,
            polarity="support",
            observation_ids=ids,
            material=material,
            weight=weight,
        )
    )

    strength = _clamp(mag + persist + breadth + corr + weight)
    return SupportResult(strength=strength, case=tuple(items), used_fallback_primary=used_fallback)
