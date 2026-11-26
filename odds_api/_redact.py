"""Keep the API key out of error messages, chained exceptions and tracebacks.

The key travels as the ``apiKey`` query parameter, and HTTP libraries put the
request URL into their exception messages and attributes. Every exception the
SDK raises, and every exception chained to it, is scrubbed before it leaves the
SDK. An exception that still shows the key afterwards (for example one whose
``__str__`` reads a read-only property) is replaced by a masked stand-in.
"""

import dataclasses
import re
import traceback
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
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
_SECRET_FIELD = re.compile(
    r"(?i)^(?:x-)?(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|secret"
    r"|password|authorization|proxy-authorization)$"
)
_MAX_DEPTH = 10

Secrets = Tuple[str, ...]


class RedactedError(Exception):
    """Stands in for an underlying exception that could not be masked in place."""


def _variants(secrets: Iterable[Optional[str]]) -> List[str]:
    found = set()
    for secret in secrets:
        if secret:
            found.update({secret, quote(secret, safe=""), quote_plus(secret)})
    return sorted(found, key=len, reverse=True)


def redact(text: str, secrets: Iterable[Optional[str]] = ()) -> str:
    """Mask ``secrets`` and any key-like query parameter or header in ``text``."""
    for secret in _variants(secrets):
        text = text.replace(secret, REDACTED)
    text = _SECRET_PARAM.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    return _SECRET_HEADER.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)


def _leaks(text: str, secrets: Secrets) -> bool:
    return redact(text, secrets) != text


def _shows_secret(value: Any, secrets: Secrets) -> bool:
    try:
        return _leaks(str(value), secrets) or _leaks(repr(value), secrets)
    except Exception:
        return True


def _set(obj: Any, name: str, value: Any) -> bool:
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        try:
            object.__setattr__(obj, name, value)
            return True
        except Exception:
            return False


def _attr_names(obj: Any) -> List[str]:
    names = list(getattr(obj, "__dict__", None) or {})
    for cls in type(obj).__mro__:
        slots = cls.__dict__.get("__slots__", ())
        names += [slots] if isinstance(slots, str) else list(slots)
    return [n for n in dict.fromkeys(names) if n not in ("__dict__", "__weakref__")]


class _Scrubber:
    def __init__(self, secrets: Iterable[Optional[str]]):
        self.secrets: Secrets = tuple(s for s in secrets if s)
        self.seen: Set[int] = set()
        self.done: Dict[int, BaseException] = {}

    def value(self, value: Any, depth: int) -> Any:
        """``value`` with secrets masked; mutable objects are cleaned in place."""
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return redact(value, self.secrets)
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace")
            if not _leaks(text, self.secrets):
                return value
            return redact(text, self.secrets).encode()
        if depth > _MAX_DEPTH:
            return REDACTED if _shows_secret(value, self.secrets) else value
        if isinstance(value, BaseException):
            return self.exception(value, depth + 1)
        if isinstance(value, dict):
            return {
                self.value(k, depth + 1): (
                    REDACTED
                    if isinstance(k, str) and _SECRET_FIELD.match(k) and v
                    else self.value(v, depth + 1)
                )
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.value(v, depth + 1) for v in value]
        if isinstance(value, tuple) and not hasattr(value, "_fields"):
            return tuple(self.value(v, depth + 1) for v in value)
        if id(value) in self.seen:
            return value
        if not _shows_secret(value, self.secrets) and not self._holds_secret(value):
            return value
        record = self._record(value, depth)
        if record is not None:
            return record
        rebuilt = self._rebuild(value)
        if rebuilt is not None:
            return rebuilt
        self.object(value, depth + 1)
        if _shows_secret(value, self.secrets):
            return redact(str(value), self.secrets)
        return value

    def _holds_secret(self, obj: Any) -> bool:
        try:
            return any(
                _shows_secret(getattr(obj, name, None), self.secrets)
                for name in _attr_names(obj)
            )
        except Exception:
            return True

    def _rebuild(self, value: Any) -> Any:
        """A URL-like value (yarl.URL, a str subclass) rebuilt from its masked text."""
        if not isinstance(value, str) and type(value).__name__ != "URL":
            return None
        try:
            rebuilt = type(value)(redact(str(value), self.secrets))
        except Exception:
            return None
        return None if _shows_secret(rebuilt, self.secrets) else rebuilt

    def _record(self, value: Any, depth: int) -> Any:
        """A copy of a namedtuple or dataclass with its fields masked."""
        try:
            if hasattr(value, "_fields") and hasattr(value, "_replace"):
                fields = list(value._fields)
                changes = {f: self.value(getattr(value, f), depth + 1) for f in fields}
                clean = value._replace(**changes)
            elif dataclasses.is_dataclass(value) and not isinstance(value, type):
                fields = [f.name for f in dataclasses.fields(value) if f.init]
                changes = {f: self.value(getattr(value, f), depth + 1) for f in fields}
                clean = dataclasses.replace(value, **changes)
            else:
                return None
        except Exception:
            return None
        return None if _shows_secret(clean, self.secrets) else clean

    def object(self, obj: Any, depth: int) -> None:
        if id(obj) in self.seen:
            return
        self.seen.add(id(obj))
        for name in _attr_names(obj):
            try:
                current = getattr(obj, name)
            except Exception:
                continue
            clean = self.value(current, depth)
            if clean is not current:
                _set(obj, name, clean)

    def exception(self, error: BaseException, depth: int = 0) -> BaseException:
        """``error`` masked in place, or a masked stand-in when that is not enough."""
        if id(error) in self.done:
            return self.done[id(error)]
        self.done[id(error)] = error
        try:
            error.args = tuple(self.value(a, depth + 1) for a in error.args)
        except Exception:
            pass
        for name in _attr_names(error):
            try:
                current = getattr(error, name)
            except Exception:
                continue
            clean = self.value(current, depth + 1)
            if clean is not current:
                _set(error, name, clean)
        if error.__cause__ is not None:
            error.__cause__ = self.exception(error.__cause__, depth + 1)
        if error.__context__ is not None:
            error.__context__ = self.exception(error.__context__, depth + 1)
        if self._exception_leaks(error):
            self.done[id(error)] = self._stand_in(error)
        return self.done[id(error)]

    def _exception_leaks(self, error: BaseException) -> bool:
        try:
            text = "".join(traceback.format_exception_only(type(error), error))
        except Exception:
            return True
        return _leaks(text, self.secrets) or _shows_secret(error, self.secrets)

    def _stand_in(self, error: BaseException) -> BaseException:
        try:
            text = str(error)
        except Exception:
            text = ""
        name = f"{type(error).__module__}.{type(error).__qualname__}"
        stand_in = RedactedError(redact(f"{name}: {text}", self.secrets))
        stand_in.__cause__ = error.__cause__
        stand_in.__suppress_context__ = True
        return stand_in


def scrub_exception(
    error: BaseException, secrets: Iterable[Optional[str]]
) -> BaseException:
    """Mask secrets in ``error`` and its whole chain.

    Returns ``error`` itself, or a :class:`RedactedError` stand-in when the
    exception would still show a secret.
    """
    return _Scrubber(secrets).exception(error)
