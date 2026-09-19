import os

import pytest


@pytest.fixture(autouse=True)
def _demo_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINGULANT_PROOF_ALLOW_DEMO", "1")
    monkeypatch.delenv("NANSEN_API_KEY", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
