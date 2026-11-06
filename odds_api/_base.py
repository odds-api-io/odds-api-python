"""Helpers shared by the sync and async clients."""

import json
import random
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Mapping, Optional, Union

from .exceptions import (
    AddOnRequiredError,
    ForbiddenError,
    InvalidAPIKeyError,
    NotFoundError,
    OddsAPIError,
    RateLimit,
    RateLimitExceededError,
    ServerError,
    ValidationError,
)

TimeLike = Union[str, datetime, date, int, float]

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def to_csv(value: Any) -> Any:
    if isinstance(value, (list, tuple, set, frozenset)):
        return ",".join(str(v) for v in value)
    return value


def format_time(value: Optional[TimeLike]) -> Optional[str]:
    """Format a datetime as RFC3339 UTC; strings pass through unchanged."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value, tz=timezone.utc)
    elif not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def check_span(from_: Optional[str], to: Optional[str], max_days: int) -> None:
    """Fail fast on a date range the API would reject. Unparseable values are left to the server."""
    start, end = _parse_time(from_), _parse_time(to)
    if start is None or end is None:
        return
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise ValidationError("'from' date must be before 'to' date")
    if end - start > timedelta(days=max_days):
        raise ValidationError(f"Maximum date span is {max_days} days")


def check_max(name: str, value: Any, maximum: int) -> None:
    if isinstance(value, str):
        count = len([v for v in value.split(",") if v.strip()])
    elif isinstance(value, (list, tuple, set, frozenset)):
        count = len(value)
    else:
        return
    if count > maximum:
        raise ValidationError(f"{name}: at most {maximum} allowed, got {count}")


def build_params(**kwargs: Any) -> Dict[str, Any]:
    """Drop None values, join lists with commas and send bools as true/false."""
    params: Dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, bool):
            params[key] = str(value).lower()
        elif isinstance(value, (datetime, date)):
            params[key] = format_time(value)
        else:
            params[key] = to_csv(value)
    return params


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def parse_rate_limit(headers: Mapping[str, str]) -> Optional[RateLimit]:
    limit = _header(headers, "X-RateLimit-Limit")
    remaining = _header(headers, "X-RateLimit-Remaining")
    reset = _header(headers, "X-RateLimit-Reset")
    if limit is None and remaining is None and reset is None:
        return None

    def as_int(v: Optional[str]) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except ValueError:
            return None

    return RateLimit(
        limit=as_int(limit), remaining=as_int(remaining), reset=_parse_time(reset)
    )


def parse_retry_after(
    headers: Mapping[str, str], now: Optional[datetime] = None
) -> Optional[float]:
    """Seconds to wait, from Retry-After (seconds or HTTP date), else X-RateLimit-Reset."""
    now = now or datetime.now(timezone.utc)
    raw = _header(headers, "Retry-After")
    if raw:
        raw = raw.strip()
        if re.fullmatch(r"\d+(\.\d+)?", raw):
            return float(raw)
        try:
            when = parsedate_to_datetime(raw)
            return max(0.0, (when - now).total_seconds())
        except (TypeError, ValueError):
            pass
    reset = _parse_time(_header(headers, "X-RateLimit-Reset"))
    if reset is not None:
        if reset.tzinfo is None:
            reset = reset.replace(tzinfo=timezone.utc)
        return max(0.0, (reset - now).total_seconds())
    return None


def decode_body(content: bytes) -> Any:
    if not content:
        return None
    text = content.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


def error_message(body: Any, status: int) -> str:
    if isinstance(body, dict):
        for key in ("error", "message", "detail"):
            if isinstance(body.get(key), str) and body[key]:
                return body[key]
        return json.dumps(body)
    if isinstance(body, str) and body.strip():
        return body.strip()
    return f"HTTP {status}"


def build_error(
    status: int, content: bytes, headers: Mapping[str, str]
) -> OddsAPIError:
    body = decode_body(content)
    message = error_message(body, status)
    common: Dict[str, Any] = {
        "status_code": status,
        "body": body,
        "headers": headers,
        "rate_limit": parse_rate_limit(headers),
    }
    if status == 400:
        return ValidationError(message, **common)
    if status == 401:
        return InvalidAPIKeyError(message, **common)
    if status == 403:
        if "add-on" in message.lower():
            add_on = "outrights" if "outright" in message.lower() else None
            return AddOnRequiredError(message, add_on=add_on, **common)
        return ForbiddenError(message, **common)
    if status == 404:
        return NotFoundError(message, **common)
    if status == 429:
        return RateLimitExceededError(
            message, retry_after=parse_retry_after(headers), **common
        )
    if status >= 500:
        return ServerError(message, retry_after=parse_retry_after(headers), **common)
    return OddsAPIError(message, **common)


def retry_delay(
    attempt: int, error: Optional[OddsAPIError], max_wait: float
) -> Optional[float]:
    """Seconds to sleep before retry number ``attempt`` (0-based), or None to give up."""
    retry_after = getattr(error, "retry_after", None)
    if retry_after is not None:
        return retry_after if retry_after <= max_wait else None
    backoff = min(0.5 * (2**attempt), 8.0)
    return min(backoff + random.uniform(0, backoff / 4), max_wait)


def is_retryable(error: OddsAPIError) -> bool:
    return error.status_code is None or error.status_code in RETRY_STATUSES


def next_retry_delay(
    attempt: int, error: OddsAPIError, max_retries: int, max_wait: float
) -> Optional[float]:
    if attempt >= max_retries or not is_retryable(error):
        return None
    return retry_delay(attempt, error, max_wait)
