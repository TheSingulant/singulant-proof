"""Challenge engine — try to break the accumulation claim."""

from __future__ import annotations

from dataclasses import dataclass

from singulant_proof.proof.evidence import CaseItem, EvidenceSet

NO_MATERIAL_CONTRADICTORY_EVIDENCE = "NO MATERIAL CONTRADICTORY EVIDENCE DETECTED"
MATERIAL_USD = 10_000.0
STRONG_USD = 100_000.0


@dataclass(frozen=True)
class ChallengeResult:
    strength: int
    case: tuple[CaseItem, ...]
    conclusion: str | None


def _clamp(value: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(value))))


def _usd(evidence: EvidenceSet, observation_id: str) -> float | None:
    return evidence.value(observation_id)


def evaluate_challenge(evidence: EvidenceSet) -> ChallengeResult:
    nf_7d = _usd(evidence, "nf:7d")
    nf_24h = _usd(evidence, "nf:24h")
    nf_1h = _usd(evidence, "nf:1h")
    nf_30d = _usd(evidence, "nf:30d")
    tgm_sm = _usd(evidence, "tgm:smart_trader:net")
    top_pnl = _usd(evidence, "tgm:top_pnl:net")
    whale = _usd(evidence, "tgm:whale:net")
    public_figure = _usd(evidence, "tgm:public_figure:net")
    exchange = _usd(evidence, "tgm:exchange:net")
    fresh = _usd(evidence, "tgm:fresh_wallets:net")

    items: list[CaseItem] = []

    reversal = 0
    reversal_ids = ["nf:7d"]
    if nf_7d is not None and nf_7d < 0:
        reversal = 30 if abs(nf_7d) >= MATERIAL_USD else 15
        body = (
            f"7d Smart Money netflow is ${nf_7d:,.0f} — primary window is distribution, not accumulation."
        )
        material = abs(nf_7d) >= MATERIAL_USD
    elif nf_7d is not None and nf_7d > 0 and nf_24h is not None and nf_24h < 0:
        reversal = 22 if abs(nf_24h) >= MATERIAL_USD else 12
        reversal_ids = ["nf:7d", "nf:24h"]
        body = (
            f"24h Smart Money netflow is ${nf_24h:,.0f} against a positive 7d "
            f"(${nf_7d:,.0f}). Recent reversal; 24h USD is not added to 7d."
        )
        material = abs(nf_24h) >= MATERIAL_USD
    else:
        body = "No primary-window distribution or 24h reversal against a positive 7d."
        material = False
    # 1h material reversal only if 24h is not already negative (nested windows).
    one_hour_extra = 0
    if (
        nf_1h is not None
        and nf_1h < 0
        and abs(nf_1h) >= MATERIAL_USD
        and not (nf_24h is not None and nf_24h < 0)
        and nf_7d is not None
        and nf_7d > 0
    ):
        one_hour_extra = 8
        reversal_ids = list(dict.fromkeys([*reversal_ids, "nf:1h"]))
        body += f" 1h material outflow ${nf_1h:,.0f} added as recency only (+8)."
        material = True
    reversal = _clamp(reversal + one_hour_extra, 0, 30)
    items.append(
        CaseItem(
            title="Primary / recent reversal",
            body=body,
            polarity="challenge",
            observation_ids=tuple(reversal_ids),
            material=material,
            weight=reversal,
        )
    )

    longer = 0
    longer_body = "30d Smart Money netflow is not a distribution signal."
    longer_mat = False
    if nf_30d is not None and nf_30d < 0:
        if nf_7d is None or nf_7d <= 0:
            longer = 15
            longer_mat = abs(nf_30d) >= MATERIAL_USD
            longer_body = f"30d Smart Money netflow is ${nf_30d:,.0f} with a non-positive 7d."
        else:
            longer = 6
            longer_body = (
                f"30d Smart Money netflow is ${nf_30d:,.0f} while 7d is positive — prior distribution, not current."
            )
    items.append(
        CaseItem(
            title="Longer-term distribution (30d context)",
            body=longer_body,
            polarity="challenge",
            observation_ids=("nf:30d",),
            material=longer_mat,
            weight=longer,
        )
    )

    inconsistency = 0
    inc_mat = False
    if nf_7d is not None and nf_7d < 0:
        inc_body = "TGM smart_trader skipped — 7d netflow is already negative (same population)."
    elif tgm_sm is not None and tgm_sm < 0:
        inconsistency = 20 if abs(tgm_sm) >= MATERIAL_USD else 10
        inc_mat = abs(tgm_sm) >= MATERIAL_USD
        inc_body = (
            f"TGM smart_trader netflow is ${tgm_sm:,.0f} against a non-negative Smart Money 7d — inconsistency."
        )
    else:
        inc_body = "No TGM smart_trader contradiction against the primary window."
    items.append(
        CaseItem(
            title="Smart Money inconsistency (TGM vs netflow)",
            body=inc_body,
            polarity="challenge",
            observation_ids=("tgm:smart_trader:net",),
            material=inc_mat,
            weight=inconsistency,
        )
    )

    cohort_opts: list[tuple[int, str, tuple[str, ...], bool]] = []
    if top_pnl is not None and top_pnl < 0:
        cohort_opts.append((14, f"Top PnL cohort is distributing (${top_pnl:,.0f}).", ("tgm:top_pnl:net",), abs(top_pnl) >= MATERIAL_USD))
    if whale is not None and whale < 0:
        cohort_opts.append((12, f"Whale cohort is distributing (${whale:,.0f}).", ("tgm:whale:net",), abs(whale) >= MATERIAL_USD))
    if public_figure is not None and public_figure < 0:
        cohort_opts.append((8, f"Public-figure cohort is distributing (${public_figure:,.0f}).", ("tgm:public_figure:net",), abs(public_figure) >= MATERIAL_USD))
    if cohort_opts:
        cohort_opts.sort(key=lambda item: (-item[0], item[2][0]))
        c_weight, c_body, c_ids, c_mat = cohort_opts[0]
    else:
        c_weight, c_body, c_ids, c_mat = 0, "No independent top-PnL / whale / public-figure distribution.", (), False
    items.append(
        CaseItem(
            title="Independent cohort distribution (max, not sum)",
            body=c_body,
            polarity="challenge",
            observation_ids=c_ids,
            material=c_mat,
            weight=c_weight,
        )
    )

    exch = 0
    exch_mat = False
    if exchange is None:
        exch_body = "Exchange netflow is null."
    elif exchange > MATERIAL_USD:
        exch, exch_mat = 12, True
        exch_body = (
            f"Exchange-labeled wallets show ${exchange:,.0f} net inflow. "
            "exchange_wallet_count is always 0 per contract and is not used."
        )
    elif exchange > 0:
        exch = 6
        exch_body = f"Exchange-labeled wallets show ${exchange:,.0f} net inflow (below material floor)."
    else:
        exch_body = f"Exchange-labeled wallets are not taking inflow (${exchange:,.0f})."
    items.append(
        CaseItem(
            title="Exchange inflow",
            body=exch_body,
            polarity="challenge",
            observation_ids=("tgm:exchange:net",),
            material=exch_mat,
            weight=exch,
        )
    )

    fresh_w = 0
    fresh_mat = False
    if fresh is None:
        fresh_body = "Fresh-wallet netflow is null (expected outside 1d/7d, or not reported)."
    elif fresh > STRONG_USD:
        fresh_w, fresh_mat = 10, True
        fresh_body = (
            f"Fresh wallets show ${fresh:,.0f} net inflow. Concentrated fresh-wallet activity may "
            "reduce confidence that the observed flow reflects broad conviction among established "
            "wallets; it does not by itself establish wash trading or farming."
        )
    elif fresh > MATERIAL_USD:
        fresh_w, fresh_mat = 6, True
        fresh_body = f"Fresh wallets show ${fresh:,.0f} net inflow."
    else:
        fresh_body = f"Fresh-wallet netflow ${fresh:,.0f} is below the material floor."
    items.append(
        CaseItem(
            title="Fresh wallets",
            body=fresh_body,
            polarity="challenge",
            observation_ids=("tgm:fresh_wallets:net",),
            material=fresh_mat,
            weight=fresh_w,
        )
    )

    strength = _clamp(reversal + longer + inconsistency + c_weight + exch + fresh_w)
    material_items = [item for item in items if item.material]
    if not material_items:
        conclusion = NO_MATERIAL_CONTRADICTORY_EVIDENCE
        none = CaseItem(
            title=NO_MATERIAL_CONTRADICTORY_EVIDENCE,
            body=(
                "No challenge component crossed the material floor. Weak or null signals remain on the docket "
                "but do not falsify the claim by themselves."
            ),
            polarity="none",
            observation_ids=(),
            material=False,
            weight=0,
        )
        return ChallengeResult(strength=strength, case=(none, *items), conclusion=conclusion)
    return ChallengeResult(strength=strength, case=tuple(items), conclusion=None)
