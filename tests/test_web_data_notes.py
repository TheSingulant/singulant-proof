"""Presentation-only Data Notes mapping.

No JS harness in this repo. Pure helpers in web/app.js are Node-extractable;
this file evals those functions with Node when available.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parents[1] / "web" / "app.js"

PURE_HELPERS = (
    "isExchangeCountWarning",
    "isFreshCountWarning",
    "formatCompactUsd",
    "parseUsdFromBody",
    "collectCaseItems",
    "extractNetUsd",
    "buildDataNotes",
)

# Frozen 2026-09-21 production verify snippets (derived case bodies, not raw Nansen dumps).
AERO_WARNINGS = [
    "TGM_PROVIDER:exchange_wallet_count is always 0 (not tracked), even when exchange net flow is non-zero.",
    "TGM_PROVIDER:fresh_wallets_wallet_count is always 0 (not tracked), even when fresh-wallet net flow is non-zero.",
    "TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO",
    "TGM_FRESH_WALLET_COUNT_ALWAYS_ZERO",
]
AERO_BODY = {
    "support_strength": 63,
    "challenge_strength": 24,
    "data_quality": 90,
    "verdict": "SUPPORTED",
    "challenge_case": [
        {
            "title": "Exchange inflow",
            "body": "Exchange-labeled wallets are not taking inflow ($-1,844,216).",
            "observation_ids": ["tgm:exchange:net"],
        },
        {
            "title": "Fresh wallets",
            "body": (
                "Fresh wallets show $127,891,429 net inflow. Concentrated fresh-wallet "
                "activity may reduce confidence that the observed flow reflects broad "
                "conviction among established wallets; it does not by itself establish "
                "wash trading or farming."
            ),
            "observation_ids": ["tgm:fresh_wallets:net"],
        },
    ],
}

AAVE_WARNINGS = list(AERO_WARNINGS)
AAVE_BODY = {
    "support_strength": 0,
    "challenge_strength": 81,
    "data_quality": 90,
    "verdict": "CONTRADICTED",
    "challenge_case": [
        {
            "title": "Exchange inflow",
            "body": (
                "Exchange-labeled wallets show $14,980 net inflow. "
                "exchange_wallet_count is always 0 per contract and is not used."
            ),
            "observation_ids": ["tgm:exchange:net"],
        },
        {
            "title": "Fresh wallets",
            "body": (
                "Fresh wallets show $46,099,566 net inflow. Concentrated fresh-wallet "
                "activity may reduce confidence that the observed flow reflects broad "
                "conviction among established wallets; it does not by itself establish "
                "wash trading or farming."
            ),
            "observation_ids": ["tgm:fresh_wallets:net"],
        },
    ],
}


def _extract_function(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    nxt = re.search(r"\nfunction ", src[start + 1 :])
    end = start + 1 + nxt.start() if nxt else len(src)
    return src[start:end].rstrip() + "\n"


def _helpers_source() -> str:
    src = APP_JS.read_text(encoding="utf-8")
    return "".join(_extract_function(src, name) for name in PURE_HELPERS)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_data_notes_use_existing_net_flow_not_unavailable_counts() -> None:
    helpers = _helpers_source()
    script = f"""
{helpers}
const cases = [
  {{
    name: "format",
    got: [
      formatCompactUsd(15500000),
      formatCompactUsd(-1300000),
      formatCompactUsd(14980),
      formatCompactUsd(0),
    ],
    expected: ["+$15.5M", "-$1.3M", "+$15K", "$0"],
  }},
  {{
    name: "aero",
    got: buildDataNotes({json.dumps(AERO_WARNINGS)}, {json.dumps(AERO_BODY)}),
    expected: [
      "Exchange net flow: -$1.8M",
      "Fresh-wallet net flow: +$127.9M",
      "Wallet count not tracked by this endpoint.",
    ],
  }},
  {{
    name: "aave",
    got: buildDataNotes({json.dumps(AAVE_WARNINGS)}, {json.dumps(AAVE_BODY)}),
    expected: [
      "Exchange net flow: +$15K",
      "Fresh-wallet net flow: +$46.1M",
      "Wallet count not tracked by this endpoint.",
    ],
  }},
  {{
    name: "fresh-null-skipped",
    got: buildDataNotes(
      ["TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO", "TGM_FRESH_WALLET_COUNT_ALWAYS_ZERO"],
      {{
        challenge_case: [
          {{ observation_ids: ["tgm:exchange:net"], body: "Exchange netflow is null." }},
          {{ observation_ids: ["tgm:fresh_wallets:net"], body: "Fresh-wallet netflow is null (expected outside 1d/7d, or not reported)." }},
        ],
      }}
    ),
    expected: ["Wallet count not tracked by this endpoint."],
  }},
];
for (const item of cases) {{
  const got = JSON.stringify(item.got);
  const expected = JSON.stringify(item.expected);
  if (got !== expected) {{
    console.error(item.name, "got", got, "expected", expected);
    process.exit(1);
  }}
}}
"""
    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout


def test_web_data_notes_source_drops_unavailable_count_copy() -> None:
    src = APP_JS.read_text(encoding="utf-8")
    assert "Exchange wallet counts are unavailable for this observation." not in src
    assert "Fresh-wallet counts are unavailable for this observation." not in src
    assert "Exchange net flow:" in src
    assert "Wallet count not tracked by this endpoint." in src
    assert "tgm:exchange:net" in src
    assert "tgm:fresh_wallets:net" in src
    assert "setWarnings(body.warnings, body)" in src
    assert "innerHTML" not in src.split("function setWarnings", 1)[1].split("function setReceipt", 1)[0]
