"""Custom exceptions for the Odds-API.io SDK."""


class OddsAPIError(Exception):
    """Base exception for all Odds-API errors."""

    pass


class InvalidAPIKeyError(OddsAPIError):
    """Raised when the API key is invalid or missing."""

    pass


class RateLimitExceededError(OddsAPIError):
    """Raised when the API rate limit has been exceeded."""

    pass


class NotFoundError(OddsAPIError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(OddsAPIError):
    """Raised when request parameters are invalid."""

    pass
