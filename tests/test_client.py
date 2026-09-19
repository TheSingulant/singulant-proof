from typing import Any

import httpx
import pytest

from singulant_proof.integrations.nansen.client import NansenClient, backoff_delay, extract_credit_headers
from singulant_proof.integrations.nansen.errors import (
    NansenAuthError,
    NansenClientError,
    NansenRateLimitError,
    NansenServerError,
    NansenTimeoutError,
)


def test_backoff_is_bounded_exponential() -> None:
    assert backoff_delay(0, base=0.5, cap=8.0, retry_after=None) == 0.5
    assert backoff_delay(1, base=0.5, cap=8.0, retry_after=None) == 1.0
    assert backoff_delay(2, base=0.5, cap=8.0, retry_after=None) == 2.0
    assert backoff_delay(8, base=0.5, cap=8.0, retry_after=None) == 8.0
    assert backoff_delay(0, base=0.5, cap=8.0, retry_after=3.0) == 3.0
    assert backoff_delay(0, base=0.5, cap=8.0, retry_after=99.0) == 8.0


def test_extract_credit_headers_not_secrets() -> None:
    headers = httpx.Headers(
        {
            "X-Nansen-Credits-Cost": "2",
            "X-Nansen-Credits-Used": "2",
            "X-Nansen-Credits-Remaining": "10",
            "RateLimit-Remaining": "40",
            "X-Request-Id": "abc",
            "apikey": "should-not-be-copied",
        }
    )
    credits = extract_credit_headers(headers)
    assert credits.credits_remaining == "10"
    assert credits.request_id == "abc"
    assert "should-not-be-copied" not in credits.__dict__.values()


def test_empty_key_rejected() -> None:
    with pytest.raises(NansenAuthError):
        NansenClient("   ")


def _handler_factory(statuses: list[int], bodies: list[Any] | None = None):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("apikey")
        assert "Authorization" not in request.headers
        idx = min(calls["n"], len(statuses) - 1)
        calls["n"] += 1
        body = (bodies or [{}] * len(statuses))[idx]
        headers = {
            "X-Nansen-Credits-Cost": "1",
            "X-Request-Id": "rid",
        }
        if statuses[idx] == 429:
            headers["Retry-After"] = "1"
        return httpx.Response(statuses[idx], json=body, headers=headers)

    return handler, calls


def test_retries_429_then_succeeds() -> None:
    sleeps: list[float] = []
    handler, calls = _handler_factory(
        [429, 200],
        [{}, {"data": [], "pagination": {"page": 1, "per_page": 10, "is_last_page": True}}],
    )
    transport = httpx.MockTransport(handler)
    client = NansenClient("test-key", transport=transport, sleep=sleeps.append, backoff_base=0.5, backoff_cap=8)
    result = client.smart_money_netflow(chains=["ethereum"], token_address="0xabc")
    assert calls["n"] == 2
    assert sleeps == [1.0]
    assert result.body["data"] == []
    assert result.provenance.credits.request_id == "rid"
    client.close()


def test_retries_5xx_only_until_bound() -> None:
    sleeps: list[float] = []
    handler, calls = _handler_factory([500, 502, 503, 504])
    transport = httpx.MockTransport(handler)
    client = NansenClient(
        "test-key",
        transport=transport,
        sleep=sleeps.append,
        max_retries=3,
        backoff_base=0.5,
        backoff_cap=8,
    )
    with pytest.raises(NansenServerError):
        client.tgm_flow_intelligence(chain="ethereum", token_address="0xabc")
    assert calls["n"] == 4
    assert sleeps == [0.5, 1.0, 2.0]
    client.close()


def test_does_not_retry_400() -> None:
    handler, calls = _handler_factory([400], [{"code": "invalid_field_value", "message": "bad"}])
    client = NansenClient("test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    with pytest.raises(NansenClientError):
        client.smart_money_netflow(chains=["ethereum"], token_address="0xabc")
    assert calls["n"] == 1
    client.close()


def test_timeout_retries_then_fails() -> None:
    sleeps: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    client = NansenClient(
        "test-key",
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        max_retries=2,
        backoff_base=0.5,
        backoff_cap=8,
    )
    with pytest.raises(NansenTimeoutError):
        client.smart_money_netflow(chains=["solana"], token_address="So111")
    assert sleeps == [0.5, 1.0]
    client.close()


def test_401_is_auth_error() -> None:
    handler, _ = _handler_factory([401], [{"code": "unauthenticated"}])
    client = NansenClient("test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    with pytest.raises(NansenAuthError):
        client.smart_money_netflow(chains=["ethereum"], token_address="0xabc")
    client.close()


def test_exhausted_429_is_rate_limit() -> None:
    handler, _ = _handler_factory([429, 429], [{}, {}])
    client = NansenClient("test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None, max_retries=1)
    with pytest.raises(NansenRateLimitError):
        client.smart_money_netflow(chains=["ethereum"], token_address="0xabc")
    client.close()
