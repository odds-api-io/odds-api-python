"""Exceptions raised by the Odds-API.io SDK.

Every API error keeps the server's own message (``str(error)``), the HTTP
status code, the raw response body and the rate-limit headers, so the reason
the API gave is never lost.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class RateLimit:
    """Rate-limit state from the ``X-RateLimit-*`` response headers."""

    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset: Optional[datetime] = None


class OddsAPIError(Exception):
    """Base exception for all Odds-API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        rate_limit: Optional[RateLimit] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers) if headers else {}
        self.rate_limit = rate_limit


class ValidationError(OddsAPIError):
    """400: the request parameters are invalid. The message says which one."""


BadRequestError = ValidationError


class InvalidAPIKeyError(OddsAPIError):
    """401: the API key is invalid or missing."""


class ForbiddenError(OddsAPIError):
    """403: the key is valid but its plan does not include this endpoint or bookmaker."""


class AddOnRequiredError(ForbiddenError):
    """403: the endpoint is sold as an add-on the key does not have (for example Outrights).

    The server's message, including the link to add it, is kept in ``str(error)``.
    """

    def __init__(self, message: str, add_on: Optional[str] = None, **kwargs: Any):
        super().__init__(message, **kwargs)
        self.add_on = add_on


class NotFoundError(OddsAPIError):
    """404: the resource does not exist. The message often lists what does exist."""


class RateLimitExceededError(OddsAPIError):
    """429: the rate limit was exceeded.

    ``retry_after`` is the number of seconds to wait, from ``Retry-After`` or
    ``X-RateLimit-Reset``, or None when the server sent neither.
    """

    def __init__(
        self, message: str, retry_after: Optional[float] = None, **kwargs: Any
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


RateLimitError = RateLimitExceededError


class ServerError(OddsAPIError):
    """5xx: the server failed or is temporarily busy."""

    def __init__(
        self, message: str, retry_after: Optional[float] = None, **kwargs: Any
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
