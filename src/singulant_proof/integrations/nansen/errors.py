"""Nansen HTTP errors. Messages must never include API keys."""


class NansenError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, retry_after: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class NansenAuthError(NansenError):
    """401 / missing key — caller configuration, not a scoring signal."""


class NansenClientError(NansenError):
    """4xx other than 429 (validation, not found, payment, forbidden)."""


class NansenRateLimitError(NansenError):
    """429 after bounded retries are exhausted."""


class NansenTimeoutError(NansenError):
    """Transport timeout after bounded retries."""


class NansenServerError(NansenError):
    """5xx after bounded retries."""
