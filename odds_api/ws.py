"""WebSocket feed helper. Install with ``pip install "odds-api-io[ws]"``.

Example:
    >>> import asyncio
    >>> from odds_api.ws import OddsStream
    >>> async def main():
    ...     stream = OddsStream("your_api_key", markets=["ML", "Totals"], sport="football", status="live")
    ...     async for message in stream:
    ...         if message["type"] in ("created", "updated"):
    ...             print(message["id"], message["bookie"], message["markets"])
    >>> asyncio.run(main())

Every ``updated`` message carries the full market set for that event and
bookmaker: replace what you hold, do not merge. ``deleted`` and
``no_markets`` mean clear it.
"""

import asyncio
import json
import random
from typing import Any, AsyncIterator, Dict, Optional, Sequence, Union
from urllib.parse import urlencode

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError as e:  # pragma: no cover
    raise ImportError(
        'websockets is required for odds_api.ws: pip install "odds-api-io[ws]"'
    ) from e

from ._base import to_csv
from .constants import WEBSOCKET_URL
from .exceptions import (
    ForbiddenError,
    InvalidAPIKeyError,
    OddsAPIError,
    ValidationError,
)

StrList = Union[str, Sequence[str]]

CLOSE_REPLACED = 1008
CLOSE_RESTART = 1012
CLOSE_TRY_AGAIN_LATER = 1013


class ConnectionReplacedError(OddsAPIError):
    """The server closed this connection because a newer one opened with the same key."""


class OddsStream:
    """
    Async iterator over WebSocket messages that reconnects and resumes from ``lastSeq``.

    Args:
        api_key: Your API key
        markets: Market names, required for the odds channel (max 40)
        channels: Any of "odds", "scores", "status" (default: odds only)
        sport: Sport names or slugs (max 10)
        leagues: League slugs (max 20); not together with ``event_ids``
        event_ids: Event IDs (max 50)
        status: "live" or "prematch"
        last_seq: Resume from this sequence number
        replay_complete: Ask for a ``replay_complete`` message after catch-up
        max_reconnects: Give up after this many reconnects in a row (None: never)
        max_backoff: Longest wait between reconnects, in seconds

    ``last_seq`` always holds the highest ``seq`` received. On
    ``resync_required`` it is cleared: rebuild state from REST
    (``get_odds_for_multiple_events(..., include_seq=True)``), set
    ``stream.last_seq`` to the ``X-OddsAPI-Seq`` header and keep iterating.
    """

    def __init__(
        self,
        api_key: str,
        markets: Optional[StrList] = None,
        channels: Optional[StrList] = None,
        sport: Optional[StrList] = None,
        leagues: Optional[StrList] = None,
        event_ids: Optional[Union[StrList, Sequence[int]]] = None,
        status: Optional[str] = None,
        last_seq: Optional[int] = None,
        replay_complete: bool = True,
        url: str = WEBSOCKET_URL,
        max_reconnects: Optional[int] = None,
        max_backoff: float = 30.0,
    ):
        if not api_key:
            raise ValueError("API key is required")
        if leagues and event_ids:
            raise ValueError("leagues and event_ids cannot be used together")
        self.api_key = api_key
        self.filters = {
            "markets": to_csv(markets),
            "channels": to_csv(channels),
            "sport": to_csv(sport),
            "leagues": to_csv(leagues),
            "eventIds": to_csv(event_ids),
            "status": status,
            "replayComplete": "true" if replay_complete else None,
        }
        self.last_seq = last_seq
        self.url = url
        self.max_reconnects = max_reconnects
        self.max_backoff = max_backoff
        self._closed = False
        self._ws: Any = None

    def connect_url(self) -> str:
        query: Dict[str, Any] = {"apiKey": self.api_key}
        query.update({k: v for k, v in self.filters.items() if v is not None})
        if self.last_seq is not None:
            query["lastSeq"] = self.last_seq
        return f"{self.url}?{urlencode(query)}"

    async def close(self) -> None:
        self._closed = True
        if self._ws is not None:
            await self._ws.close()

    def _track(self, message: Dict[str, Any]) -> None:
        seq = message.get("seq")
        if isinstance(seq, int) and (self.last_seq is None or seq > self.last_seq):
            self.last_seq = seq
        if message.get("type") == "resync_required":
            self.last_seq = None

    def _backoff(self, attempt: int) -> float:
        delay = min(self.max_backoff, 0.5 * (2**attempt))
        return delay + random.uniform(0, delay / 4)

    async def __aiter__(self) -> AsyncIterator[Dict[str, Any]]:
        attempt = 0
        while not self._closed:
            code: Optional[int] = None
            reason = ""
            try:
                async with websockets.connect(self.connect_url(), max_size=None) as ws:
                    self._ws = ws
                    async for raw in ws:
                        message = json.loads(raw)
                        if message.get("type") == "welcome":
                            attempt = 0
                        self._track(message)
                        yield message
                    code = ws.close_code
            except ConnectionClosed as e:
                received = getattr(e, "rcvd", None)
                code = received.code if received is not None else None
                reason = received.reason if received is not None else ""
            except OSError:
                code = None
            except Exception as e:
                status = _handshake_status(e)
                if status is None:
                    raise
                if status == 400:
                    raise ValidationError(
                        f"WebSocket refused: {e}", status_code=status
                    ) from e
                if status == 401:
                    raise InvalidAPIKeyError(
                        f"WebSocket refused: {e}", status_code=status
                    ) from e
                if status == 403:
                    raise ForbiddenError(
                        f"WebSocket refused: {e}", status_code=status
                    ) from e
                if status < 500 and status != 429:
                    raise OddsAPIError(
                        f"WebSocket refused: {e}", status_code=status
                    ) from e
            finally:
                self._ws = None

            if self._closed:
                return
            if code == CLOSE_REPLACED and "newer connection" in reason:
                raise ConnectionReplacedError(f"WebSocket closed {code}: {reason}")
            if self.max_reconnects is not None and attempt >= self.max_reconnects:
                raise OddsAPIError(
                    f"WebSocket closed ({code}) after {attempt} reconnects"
                )
            delay = self._backoff(attempt)
            if code == CLOSE_RESTART:
                delay = min(delay, 1.0)
            elif code == CLOSE_TRY_AGAIN_LATER:
                delay = max(delay, 3.0)
            attempt += 1
            await asyncio.sleep(delay)


def _handshake_status(error: Exception) -> Optional[int]:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(error, "status_code", None)
    return status if isinstance(status, int) else None
