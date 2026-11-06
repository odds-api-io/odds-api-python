"""
Odds-API.io Python SDK
Official Python client for the Odds-API.io sports betting odds API.
"""

__version__ = "1.2.1"

from .client import OddsAPIClient
from .async_client import AsyncOddsAPIClient
from .constants import GOLF_OUTRIGHT_MARKETS
from .exceptions import (
    AddOnRequiredError,
    BadRequestError,
    ForbiddenError,
    InvalidAPIKeyError,
    NotFoundError,
    OddsAPIError,
    RateLimit,
    RateLimitError,
    RateLimitExceededError,
    ServerError,
    ValidationError,
)

__all__ = [
    "OddsAPIClient",
    "AsyncOddsAPIClient",
    "OddsAPIError",
    "ValidationError",
    "BadRequestError",
    "InvalidAPIKeyError",
    "ForbiddenError",
    "AddOnRequiredError",
    "NotFoundError",
    "RateLimitExceededError",
    "RateLimitError",
    "ServerError",
    "RateLimit",
    "GOLF_OUTRIGHT_MARKETS",
    "__version__",
]
