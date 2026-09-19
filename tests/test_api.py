from fastapi.testclient import TestClient

from singulant_proof.api.app import create_app
from singulant_proof.proof.claim import CLAIM_ID


def test_healthz() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["attribution"] == "Powered by Nansen"
    assert body["cta"] == "ATTEMPT FALSIFICATION"
    assert body["nansen_key_configured"] is False


def test_verify_demo_returns_full_docket() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/proof/verify",
        json={
            "chain": "ethereum",
            "token_address": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
            "claim": CLAIM_ID,
            "demo": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["claim"]["id"] == CLAIM_ID
    assert body["verdict"] in {
        "SUPPORTED",
        "SUPPORTED_BUT_CONTESTED",
        "MIXED",
        "CONTRADICTED",
        "INSUFFICIENT_DATA",
    }
    assert body["stages_completed"] == [
        "CLAIM",
        "COLLECT",
        "NORMALIZE",
        "SUPPORT",
        "CHALLENGE",
        "QUALITY",
        "ADJUDICATE",
        "RECEIPT",
    ]
    assert body["synthetic"] is True
    assert "SYNTHETIC_EVIDENCE" in " ".join(body["warnings"])
    assert "apikey" not in str(body).lower()
    receipt = body["evidence_receipt"]
    assert receipt["attribution"] == "Powered by Nansen"
    assert receipt["observation_count"] > 0


def test_verify_without_key_is_503() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/proof/verify",
        json={"chain": "ethereum", "token_address": "0xabc", "demo": False},
    )
    assert response.status_code == 503


def test_demo_disabled_without_flag(monkeypatch) -> None:
    monkeypatch.delenv("SINGULANT_PROOF_ALLOW_DEMO", raising=False)
    client = TestClient(create_app())
    response = client.post(
        "/v1/proof/verify",
        json={"chain": "ethereum", "token_address": "0xabc", "demo": True},
    )
    assert response.status_code == 400


def test_rejects_unknown_claim() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/proof/verify",
        json={"chain": "ethereum", "token_address": "0xabc", "claim": "MOON", "demo": True},
    )
    assert response.status_code == 422


def test_app_does_not_emit_cors_headers() -> None:
    """nginx owns CORS. Wildcard middleware stacked ACAO and broke browsers."""
    client = TestClient(create_app())
    for origin in ("https://www.thesingulant.ai", "https://evil.example"):
        response = client.get("/healthz", headers={"Origin": origin})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
    preflight = client.options(
        "/v1/proof/verify",
        headers={
            "Origin": "https://www.thesingulant.ai",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_web_index_served() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    page = response.content
    assert b"SINGULANT PROOF" in page
    assert b"Adversarial on-chain verification" in page
    assert b"Don't ask AI to confirm your thesis. Make it try to break it." in page
    assert b"DETERMINISTIC ADJUDICATOR" in page
    assert b"EVIDENCE RECEIPT" in page
    assert b"Attempt Falsification" in page
    assert b"Powered by Nansen" in page
    assert b"The LLM cannot choose or override the verdict." in page
    assert b"Synthetic docket" not in page
    assert b"API base" not in page
