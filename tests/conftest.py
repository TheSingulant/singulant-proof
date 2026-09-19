import os

import pytest


@pytest.fixture(autouse=True)
def _demo_flag(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Allow demo mode in unit tests. Preserve NANSEN_API_KEY for live integration."""
    monkeypatch.setenv("SINGULANT_PROOF_ALLOW_DEMO", "1")
    # Live integration tests need the real key; do not delete it for those modules.
    if request.node.fspath and "test_integration_live" in str(request.node.fspath):
        return
    monkeypatch.delenv("NANSEN_API_KEY", raising=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
