"""Keep the API key out of error messages, chained exceptions and tracebacks.

The key travels as the ``apiKey`` query parameter, and HTTP libraries put the
request URL into their exception messages. Every exception the SDK raises, and
every exception chained to it, is scrubbed before it leaves the SDK.
"""

import dataclasses
import re
from typing import Any, Iterable, Optional, Set
from urllib.parse import quote, quote_plus

REDACTED = "***"

_SECRET_PARAM = re.compile(
    r"(?i)(?<![a-z0-9_])"
    r"(api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password|key)"
    r"(=|%3D)"
    r"[^&#\s'\"<>()\[\],;]+"
)
_SECRET_HEADER = re.compile(
    r"(?i)((?:x-)?api[_-]?key|authorization)(['\"]?\s*:\s*['\"]?)"
    r"(?:bearer\s+|basic\s+)?[^'\"\s,}&]+"
)
_URL_ATTRS = ("url", "real_url", "uri", "path", "filename", "filename2")
_NESTED_ATTRS = ("request", "response", "reason", "original_error", "os_error")
_MAX_DEPTH = 12


def _variants(secrets: Iterable[Optional[str]]) -> Set[str]:
    found = set()
    for secret in secrets:
        if not secret:
            continue
        found.update({secret, quote(secret, safe=""), quote_plus(secret)})
    return found


def redact(text: str, secrets: Iterable[Optional[str]] = ()) -> str:
    """Mask ``secrets`` and any key-like query parameter or header in ``text``."""
    for secret in sorted(_variants(secrets), key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    text = _SECRET_PARAM.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    return _SECRET_HEADER.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)


def _leaks(text: str, secrets: Iterable[Optional[str]]) -> bool:
    return redact(text, secrets) != text


def redact_value(value: Any, secrets: Iterable[Optional[str]]) -> Any:
    """Return ``value`` with secrets masked in every string inside it."""
    if isinstance(value, str):
        return redact(value, secrets)
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
        return redact(text, secrets).encode() if _leaks(text, secrets) else value
    if isinstance(value, dict):
        return {k: redact_value(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v, secrets) for v in value]
    if isinstance(value, tuple) and not hasattr(value, "_fields"):
        return tuple(redact_value(v, secrets) for v in value)
    return value


def _rebuild_url(value: Any, secrets: Iterable[Optional[str]]) -> Any:
    text = str(value)
    if not _leaks(text, secrets):
        return value
    clean = redact(text, secrets)
    try:
        return type(value)(clean)
    except Exception:
        return clean


def _scrub_object(
    obj: Any, secrets: Iterable[Optional[str]], seen: Set[int], depth: int
) -> None:
    if obj is None or id(obj) in seen or depth > _MAX_DEPTH:
        return
    if isinstance(obj, (str, bytes, int, float, bool)):
        return
    if isinstance(obj, BaseException):
        scrub_exception(obj, secrets, seen, depth)
        return
    seen.add(id(obj))
    _scrub_attrs(obj, secrets, seen, depth)


def _set_clean(obj: Any, name: str, secrets: Iterable[Optional[str]]) -> None:
    try:
        value = getattr(obj, name, None)
    except Exception:
        return
    if value is None or isinstance(value, (int, float, bool, BaseException)):
        return
    if isinstance(value, (str, bytes, dict, list, tuple)):
        clean = redact_value(value, secrets)
    else:
        clean = _rebuild_url(value, secrets)
    if clean is value:
        return
    try:
        setattr(obj, name, clean)
    except Exception:
        try:
            object.__setattr__(obj, name, clean)
        except Exception:
            pass


def _scrub_request_info(obj: Any, secrets: Iterable[Optional[str]]) -> None:
    info = getattr(obj, "request_info", None)
    clean = _clean_record(info, secrets) if info is not None else None
    if clean is not None:
        try:
            obj.request_info = clean
        except Exception:
            pass


def _clean_record(obj: Any, secrets: Iterable[Optional[str]]) -> Any:
    """A copy of a namedtuple or dataclass with its leaking fields masked, else None."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        names = [f.name for f in dataclasses.fields(obj)]
    elif hasattr(obj, "_fields") and hasattr(obj, "_replace"):
        names = list(obj._fields)
    else:
        return None
    changes = {}
    for name in names:
        value = getattr(obj, name, None)
        if value is None or not _leaks(repr(value), secrets):
            continue
        if isinstance(value, (str, bytes, dict, list, tuple)):
            changes[name] = redact_value(value, secrets)
        else:
            changes[name] = _rebuild_url(value, secrets)
    if not changes:
        return obj
    try:
        if hasattr(obj, "_replace"):
            return obj._replace(**changes)
        return dataclasses.replace(obj, **changes)
    except Exception:
        return None


def _scrubbed(
    obj: Any, secrets: Iterable[Optional[str]], seen: Set[int], depth: int
) -> Any:
    _scrub_object(obj, secrets, seen, depth + 1)
    return obj if not _leaks(repr(obj), secrets) else redact(str(obj), secrets)


def scrub_exception(
    error: BaseException,
    secrets: Iterable[Optional[str]],
    seen: Optional[Set[int]] = None,
    depth: int = 0,
) -> BaseException:
    """Mask secrets in ``error`` and everything chained to it, in place."""
    secrets = tuple(secrets)
    seen = set() if seen is None else seen
    if id(error) in seen or depth > _MAX_DEPTH:
        return error
    seen.add(id(error))

    clean_args = []
    for arg in error.args:
        if isinstance(arg, BaseException):
            scrub_exception(arg, secrets, seen, depth + 1)
            clean_args.append(arg)
        elif isinstance(arg, (str, bytes, dict, list)) or (
            isinstance(arg, tuple) and not hasattr(arg, "_fields")
        ):
            clean_args.append(redact_value(arg, secrets))
        elif arg is not None and _leaks(repr(arg), secrets):
            clean_args.append(
                _clean_record(arg, secrets) or _scrubbed(arg, secrets, seen, depth)
            )
        else:
            clean_args.append(arg)
    try:
        error.args = tuple(clean_args)
    except Exception:
        pass

    for name in ("msg", "message", "strerror", "reason", "body", "headers"):
        _set_clean(error, name, secrets)
    _scrub_attrs(error, secrets, seen, depth)

    notes = getattr(error, "__notes__", None)
    if isinstance(notes, list):
        clean_notes = [redact(n, secrets) if isinstance(n, str) else n for n in notes]
        setattr(error, "__notes__", clean_notes)

    for linked in (error.__cause__, error.__context__):
        if linked is not None:
            scrub_exception(linked, secrets, seen, depth + 1)
    return error


def _scrub_attrs(
    obj: Any, secrets: Iterable[Optional[str]], seen: Set[int], depth: int
) -> None:
    for name in _URL_ATTRS:
        _set_clean(obj, name, secrets)
    for name in _NESTED_ATTRS:
        try:
            value = getattr(obj, name, None)
        except Exception:
            continue
        _scrub_object(value, secrets, seen, depth + 1)
    _scrub_request_info(obj, secrets)
    history = getattr(obj, "history", None)
    if isinstance(history, (list, tuple)):
        for item in history:
            _scrub_object(item, secrets, seen, depth + 1)
