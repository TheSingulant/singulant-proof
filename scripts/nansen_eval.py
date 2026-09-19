#!/usr/bin/env python3
"""Stub only. Do not execute the 1,000-call evaluation corpus from this script.

This repository is the public Buildathon surface. The parent orchestrator
runs the live integration test with NANSEN_API_KEY set:

    NANSEN_API_KEY=... pytest tests/test_integration_live.py -q

This file exists so a corpus runner can be attached later without importing
any AI4 / telegram / TX / authorize / consume / handoff / V07 / R3 code.
It must not be used to burn Nansen credits from this repo.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "nansen_eval.py is a stub. Do not run the evaluation corpus from this repo.\n"
        "Parent: NANSEN_API_KEY=*** pytest tests/test_integration_live.py\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
