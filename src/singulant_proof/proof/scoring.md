# Scoring (V1)

Conservative. No bullish bias. No double-count. Same `EvidenceSet` → identical scores and verdict.

Claim under examination: **Smart Money is accumulating this token.**
Primary window: **7d Smart Money netflow**. Nested windows are *not* independent dollars.

## Signals and independence

| Signal | Source | Use | Do not |
| --- | --- | --- | --- |
| `net_flow_7d_usd` | Smart Money netflow | Primary magnitude | Add 1h+24h+7d+30d |
| `net_flow_24h_usd` | same row | Persistence / reversal only (sign) | Add its USD to 7d |
| `net_flow_1h_usd` | same row | Recency noise; material reversal only | Treat as accumulation proof |
| `net_flow_30d_usd` | same row | Longer-term context / prior distribution | Add to 7d |
| `trader_count`, `token_age_days`, `market_cap_usd` | same row | Breadth, quality, relative size | Invent when null |
| `smart_trader_*` | TGM flow-intelligence | Corroboration of the *same* population | Sum USD with netflow |
| `top_pnl_*`, `whale_*`, `public_figure_*` | TGM | Independent cohort (max, not sum) | Stack all three fully |
| `exchange_*` | TGM | Challenge if exchange wallets take inflow | Use `exchange_wallet_count` (always 0) |
| `fresh_wallets_*` | TGM 1d/7d only | Challenge if large fresh inflow | Treat null as zero |

Null stays null. Missing is a quality hit, never a bullish fill.

## Support strength (0–100)

If primary 7d is `null`, TGM `smart_trader_net_flow_usd` may be used as a fallback primary with a **0.6 haircut**. If 7d is present and `<= 0`, support is **0** (challenge owns the contradiction).

Components when 7d `> 0` (or fallback after haircut):

| Component | Cap | Rule |
| --- | --- | --- |
| Magnitude | 50 | Material floor `$10,000`. Strong `$100,000`. If market cap is known, also require 0.1% / 1% of mcap for material / strong. Without mcap, magnitude is capped at 40. Trace inflows below material score at most 8. |
| Persistence | 15 | **Sign only.** +15 if 24h `> 0`. +5 if 24h is 0. +0 if 24h `< 0` or null. 1h is not persistence. |
| Breadth | 15 | `trader_count`: `< 3` → 3; `3–9` interpolate 6–12; `≥ 10` → 15; null → 0. |
| SM corroboration | 12 | TGM smart_trader **sign only**. `> 0` → 12; `0` → 4; `< 0` or null → 0. USD is not added. |
| Independent cohort | 8 | `max(top_pnl>0 → 8, whale>0 → 6)`. Not summed. Public figure is context, not support. |

Total is clamped to `[0, 100]` and stored as an integer.

## Challenge strength (0–100)

Challenge may conclude **NO MATERIAL CONTRADICTORY EVIDENCE DETECTED** when no component is material.

| Component | Cap | Rule |
| --- | --- | --- |
| Primary / recent reversal | 30 | 7d `< 0` and material → 30; 7d `< 0` trace → 15. If 7d `> 0` and 24h `< 0`: 22 if 24h material else 12. 1h material reversal adds at most +8 and **only if 24h is not already negative** (no nested double-count). |
| Longer-term distribution | 15 | 30d `< 0` and 7d `<= 0` → 15. 30d `< 0` and 7d `> 0` → 6 (prior, not current). |
| SM inconsistency | 20 | TGM smart_trader `< 0`. **Skipped when 7d is already `< 0`** (same population). |
| Independent cohort distribution | 20 | `max(top_pnl<0 → 14, whale<0 → 12, public_figure<0 → 8)`. Not summed. |
| Exchange inflow | 12 | Exchange net `> $10k` → 12; `> 0` → 6. Wallet count ignored. |
| Fresh wallets | 10 | Fresh net `> $100k` → 10; `> $10k` → 6. Null skipped. |

Total clamped to `[0, 100]`.

## Data quality (0–100)

Start at 100 and deduct. Floor 0.

| Condition | Deduction |
| --- | --- |
| Netflow unavailable / malformed | −40 |
| No netflow row | −30 |
| TGM unavailable / malformed | −25 |
| TGM no row | −15 |
| 7d null (and no TGM fallback) | −20 |
| 24h null | −8 |
| market cap null | −10 |
| trader_count null | −8 |
| trader_count `< 3` | −10 |
| token age null | −5 |
| token age `< 7` days | −12 |
| TGM smart_trader net null | −8 |
| Each TGM provider warning | −5 (cap −15) |

Known contract caveats (`exchange_wallet_count` always 0; fresh-wallet count always 0) are **warnings, not deductions**.

## Adjudicator (first match wins)

Thresholds:

- `QUALITY_FLOOR = 40`
- `SUPPORT_MIN = 25`
- `SUPPORT_CLEAR = 55`
- `CHALLENGE_CONTEST = 25`
- `CHALLENGE_STRONG = 55`
- `CHALLENGE_DOMINANCE_GAP = 10`

1. `quality < 40` → `INSUFFICIENT_DATA`
2. `support < 25` and `challenge < 40` → `INSUFFICIENT_DATA`
3. `challenge >= 55` and `challenge >= support + 10` → `CONTRADICTED`
4. `support >= 55` and `challenge < 25` → `SUPPORTED`
5. `support >= 55` and `challenge >= 25` → `SUPPORTED_BUT_CONTESTED`
6. else → `MIXED`

`SUPPORTED` therefore requires both a clear support case and a weak challenge case. Mid-range evidence does not get the benefit of the doubt.

## Receipt

Share-card-ready fields (no social UI in V1): `claim`, `claim_display`, `verdict`, `support_strength`, `challenge_strength`, `data_quality`, `observed_at`, `observation_count`, per-side observation counts, `chain`, `token`, `attribution`, `evidence_fingerprint`, `receipt_id`. Provenance is redacted (endpoint, status, request id, credit headers). Raw Nansen bodies are never included.
