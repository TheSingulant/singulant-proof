"""Nansen HTTP client.

Auth: header `apikey` (OpenAPI ApiKeyAuth). Base: https://api.nansen.ai
Retries: bounded exponential backoff for 429 / timeout / 5xx only.
Never logs or returns the API key.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from singulant_proof.integrations.nansen.errors import (
    NansenAuthError,
    NansenClientError,
    NansenRateLimitError,
    NansenServerError,
    NansenTimeoutError,
)
from singulant_proof.integrations.nansen.schemas import (
    CREDIT_HEADER_MAP,
    FLOW_INTELLIGENCE_PATH,
    NANSEN_BASE_URL,
    NETFLOW_PATH,
    TGM_TIMEFRAMES,
)
from singulant_proof.integrations.nansen.types import CreditHeaders, NansenCallResult, ProvenanceRef, utc_now

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY = 0.5
_DEFAULT_MAX_DELAY = 8.0


def _header(headers: httpx.Headers, name: str) -> str | None:
    value = headers.get(name)
    if value is None or value == "":
        return None
    return str(value)


def extract_credit_headers(headers: httpx.Headers) -> CreditHeaders:
    kwargs = {field: _header(headers, header) for field, header in CREDIT_HEADER_MAP.items()}
    # Some gateways emit X-RateLimit-* instead of RateLimit-*.
    if kwargs["rate_limit_remaining"] is None:
        kwargs["rate_limit_remaining"] = _header(headers, "x-ratelimit-remaining")
    if kwargs["rate_limit_limit"] is None:
        kwargs["rate_limit_limit"] = _header(headers, "x-ratelimit-limit")
    if kwargs["rate_limit_reset"] is None:
        kwargs["rate_limit_reset"] = _header(headers, "x-ratelimit-reset")
    return CreditHeaders(**kwargs)


def backoff_delay(attempt: int, *, base: float, cap: float, retry_after: float | None) -> float:
    """attempt is 0-based (first retry = 0). Bounded exponential: base * 2^attempt."""
    raw = min(cap, base * (2**attempt))
    if retry_after is None:
        return raw
    return min(cap, max(raw, retry_after))


def _retry_after_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        value = payload.get("retry_after")
        if value is None and isinstance(payload.get("message"), dict):
            value = None
        if isinstance(value, (int, float)):
            return max(0.0, float(value))
    return None


def _safe_error_message(status_code: int, body: Any) -> str:
    if isinstance(body, dict):
        code = body.get("code") or body.get("error")
        message = body.get("message") or body.get("detail")
        parts = [f"Nansen HTTP {status_code}"]
        if code:
            parts.append(str(code))
        if message and isinstance(message, str):
            parts.append(message[:240])
        return ": ".join(parts)
    return f"Nansen HTTP {status_code}"


class NansenClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = NANSEN_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_base: float = _DEFAULT_BASE_DELAY,
        backoff_cap: float = _DEFAULT_MAX_DELAY,
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        if not api_key or not api_key.strip():
            raise NansenAuthError("NANSEN_API_KEY is not set", status_code=401)
        self._api_key = api_key.strip()
        self._max_retries = max(0, max_retries)
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._sleep = sleep
        headers = {
            "apikey": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> NansenClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def smart_money_netflow(
        self,
        *,
        chains: list[str],
        token_address: str,
        include_smart_money_labels: list[str] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> NansenCallResult:
        filters: dict[str, Any] = {"token_address": token_address}
        if include_smart_money_labels:
            filters["include_smart_money_labels"] = include_smart_money_labels
        body = {
            "chains": chains,
            "filters": filters,
            "pagination": {"page": page, "per_page": per_page},
        }
        return self._post(NETFLOW_PATH, body)

    def tgm_flow_intelligence(
        self,
        *,
        chain: str,
        token_address: str,
        timeframe: str = "1d",
    ) -> NansenCallResult:
        if timeframe not in TGM_TIMEFRAMES:
            raise NansenClientError(f"unsupported TGM timeframe: {timeframe}", status_code=400)
        body = {
            "chain": chain,
            "token_address": token_address,
            "timeframe": timeframe,
        }
        return self._post(FLOW_INTELLIGENCE_PATH, body)

    def _post(self, path: str, body: dict[str, Any]) -> NansenCallResult:
        last_timeout: Exception | None = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._http.post(path, json=body)
            except httpx.TimeoutException as exc:
                last_timeout = exc
                if attempt >= self._max_retries:
                    raise NansenTimeoutError("Nansen request timed out") from exc
                delay = backoff_delay(attempt, base=self._backoff_base, cap=self._backoff_cap, retry_after=None)
                logger.info("nansen timeout; retrying", extra={"endpoint": path, "attempt": attempt})
                self._sleep(delay)
                continue

            if response.status_code == 401:
                raise NansenAuthError("Nansen rejected the API key", status_code=401)

            if response.status_code in _RETRYABLE_STATUS and attempt < self._max_retries:
                delay = backoff_delay(
                    attempt,
                    base=self._backoff_base,
                    cap=self._backoff_cap,
                    retry_after=_retry_after_seconds(response),
                )
                logger.info(
                    "nansen retryable status; backing off",
                    extra={"endpoint": path, "status": response.status_code, "attempt": attempt},
                )
                self._sleep(delay)
                continue

            payload = self._json_body(response)
            provenance = ProvenanceRef(
                provider="nansen",
                endpoint=path,
                status_code=response.status_code,
                observed_at=utc_now(),
                credits=extract_credit_headers(response.headers),
            )
            if response.status_code == 429:
                raise NansenRateLimitError(
                    _safe_error_message(429, payload),
                    status_code=429,
                    retry_after=int(_retry_after_seconds(response) or 0) or None,
                )
            if response.status_code >= 500:
                raise NansenServerError(_safe_error_message(response.status_code, payload), status_code=response.status_code)
            if response.status_code >= 400:
                raise NansenClientError(_safe_error_message(response.status_code, payload), status_code=response.status_code)
            if not isinstance(payload, dict):
                raise NansenServerError("Nansen returned a non-object body", status_code=response.status_code)
            return NansenCallResult(
                endpoint=path,
                status_code=response.status_code,
                body=payload,
                provenance=provenance,
            )

        raise NansenTimeoutError("Nansen request timed out") from last_timeout

    @staticmethod
    def _json_body(response: httpx.Response) -> Any:
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {"message": "non-json response"}
