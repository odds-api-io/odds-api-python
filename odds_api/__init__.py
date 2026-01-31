"""
Odds-API.io Python SDK
Official Python client for the Odds-API.io sports betting odds API.
"""

__version__ = "1.0.0"

from .client import OddsAPIClient
from .async_client import AsyncOddsAPIClient
from .exceptions import (
    OddsAPIError,
    InvalidAPIKeyError,
    RateLimitExceededError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "OddsAPIClient",
    "AsyncOddsAPIClient",
    "OddsAPIError",
    "InvalidAPIKeyError",
    "RateLimitExceededError",
    "NotFoundError",
    "ValidationError",
    "__version__",
]
