"""Synchronous client for the Odds-API.io API."""

import time
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Union

import requests

from . import __version__
from ._base import (
    TimeLike,
    build_error,
    build_params,
    check_max,
    check_span,
    decode_body,
    format_time,
    next_retry_delay,
    parse_rate_limit,
)
from .constants import (
    BASE_API_URL,
    DEFAULT_TIMEOUT,
    MAX_BOOKMAKERS,
    MAX_CLOSING_LINES_LEAGUES,
    MAX_CLOSING_LINES_PAGE,
    MAX_CLOSING_LINES_SPAN_DAYS,
    MAX_HISTORICAL_SPAN_DAYS,
    MAX_MARKETS,
    MAX_MULTI_EVENTS,
    MAX_SETTLEMENT_EVENTS,
    MAX_SUMMARY_MARKETS,
    Endpoints,
)
from .exceptions import OddsAPIError, RateLimit
from .types import (
    ArbitrageBet,
    Bookmaker,
    DroppingOdds,
    Event,
    EventOdds,
    GradeSelection,
    GradesResponse,
    League,
    Mapping as MappingRow,
    MappingsPage,
    OddsMovements,
    OddsSummary,
    Outright,
    OutrightOdds,
    OutrightResults,
    Participant,
    SettlementsResponse,
    Sport,
    ValueBet,
)

StrList = Union[str, Sequence[str]]
IdList = Union[str, int, Sequence[Union[str, int]]]


class OddsAPIClient:
    """
    Synchronous client for the Odds-API.io API.

    Args:
        api_key: Your Odds-API.io API key (https://odds-api.io/pricing)
        timeout: Request timeout in seconds (default: 10)
        base_url: Base API URL (default: https://api.odds-api.io/v3)
        max_retries: Retries on 429, 5xx and network errors (default: 0, off)
        max_retry_wait: Longest single wait in seconds before a retry. A 429
            that asks for a longer wait is raised instead of slept on.

    Comma-separated parameters (bookmakers, markets, event ids, leagues)
    accept either a string or a list. Date parameters accept RFC3339
    strings or ``datetime`` objects (naive datetimes are read as UTC).

    After every call ``last_rate_limit`` holds the ``X-RateLimit-*`` values
    and ``last_response_headers`` the raw headers (for example
    ``X-Next-Since`` from ``/odds/updated``).

    Example:
        >>> client = OddsAPIClient(api_key="your_api_key")
        >>> events = client.get_events(sport="basketball", league="usa-nba")
        >>> odds = client.get_event_odds(events[0]["id"], ["Bet365", "SingBet"], markets=["ML"])
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        base_url: str = BASE_API_URL,
        max_retries: int = 0,
        max_retry_wait: float = 30.0,
    ):
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.max_retry_wait = max_retry_wait
        self.last_rate_limit: Optional[RateLimit] = None
        self.last_response_headers: Dict[str, str] = {}
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"odds-api-io-python/{__version__}"

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        url = f"{self.base_url}/{path}"
        query = dict(params or {})
        query["apiKey"] = self.api_key
        attempt = 0
        while True:
            cause: Optional[BaseException] = None
            try:
                response = self.session.request(
                    method, url, params=query, json=body, timeout=self.timeout
                )
            except requests.RequestException as e:
                cause = e
                error = OddsAPIError(f"Request failed: {e}")
            else:
                headers: Mapping[str, str] = response.headers
                self.last_response_headers = dict(headers)
                self.last_rate_limit = parse_rate_limit(headers) or self.last_rate_limit
                if response.ok:
                    return response.content if raw else decode_body(response.content)
                error = build_error(response.status_code, response.content, headers)

            delay = next_retry_delay(
                attempt, error, self.max_retries, self.max_retry_wait
            )
            if delay is None:
                raise error from cause
            time.sleep(delay)
            attempt += 1

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params)

    def _put(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("PUT", path, params)

    def _post(self, path: str, body: Dict[str, Any]) -> Any:
        return self._request("POST", path, body=body)

    _build_params = staticmethod(build_params)

    # Sports, leagues and markets

    def get_sports(self) -> List[Sport]:
        """
        Get all available sports.

        Example:
            >>> [s["slug"] for s in client.get_sports()]
        """
        return self._get(Endpoints.GET_SPORTS)

    def get_leagues(self, sport: str, all: Optional[bool] = None) -> List[League]:
        """
        Get leagues for a sport.

        Args:
            sport: Sport name or slug, e.g. "football"
            all: True to include leagues without upcoming events

        Example:
            >>> leagues = client.get_leagues(sport="basketball")
        """
        return self._get(Endpoints.GET_LEAGUES, build_params(sport=sport, all=all))

    def get_markets(self, sport: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the market catalogue: the exact market names to pass to ``markets``.

        Args:
            sport: Sport name or slug. Omit for every sport (keyed by slug).

        Returns:
            With ``sport``: ``{"sport": {...}, "markets": [{name, shape, period, prematch, live}]}``

        Example:
            >>> names = [m["name"] for m in client.get_markets("football")["markets"]]
        """
        return self._get(Endpoints.GET_MARKETS, build_params(sport=sport))

    # Events

    def get_events(
        self,
        sport: str,
        league: Optional[str] = None,
        participant_id: Optional[int] = None,
        status: Optional[StrList] = None,
        start: Optional[TimeLike] = None,
        end: Optional[TimeLike] = None,
        bookmaker: Optional[str] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        from_: Optional[TimeLike] = None,
        to: Optional[TimeLike] = None,
    ) -> List[Event]:
        """
        Get events with optional filters.

        Without ``to`` (or ``end``) the API returns the next 14 days. Each
        response is capped at 5000 events; page with ``limit`` and ``skip``
        or use :meth:`iter_events`.

        Args:
            sport: Sport name or slug (required)
            league: League slug
            participant_id: Filter by participant ID
            status: pending, live, settled, cancelled, or a list of them
            start: Start of the window (sent as ``from``). ``from_`` is an alias.
            end: End of the window (sent as ``to``). ``to`` is an alias.
            bookmaker: Only events this bookmaker prices
            limit: Max events per response (up to 5000)
            skip: Offset for pagination

        Example:
            >>> events = client.get_events(sport="football", status=["pending", "live"])
        """
        params = build_params(
            sport=sport,
            league=league,
            participantId=participant_id,
            status=status,
            bookmaker=bookmaker,
            limit=limit,
            skip=skip,
        )
        params.update(
            build_params(
                **{"from": format_time(from_ or start), "to": format_time(to or end)}
            )
        )
        return self._get(Endpoints.GET_EVENTS, params)

    def iter_events(
        self, sport: str, page_size: int = 1000, **filters: Any
    ) -> Iterator[Event]:
        """
        Iterate over every event matching the filters, paging with ``limit``/``skip``.

        Example:
            >>> for event in client.iter_events("football", to="2026-12-31T00:00:00Z"):
            ...     print(event["id"])
        """
        skip = 0
        while True:
            page = self.get_events(sport, limit=page_size, skip=skip, **filters)
            yield from page
            if len(page) < page_size:
                return
            skip += len(page)

    def get_event_by_id(self, event_id: Union[int, str]) -> Event:
        """Get one event by ID."""
        return self._get(Endpoints.GET_EVENT_BY_ID.format(id=event_id))

    def get_live_events(self, sport: Optional[str] = None) -> List[Event]:
        """
        Get live events, for one sport or all. Live events carry a ``clock``.

        Example:
            >>> live = client.get_live_events(sport="basketball")
        """
        return self._get(Endpoints.GET_LIVE_EVENTS, build_params(sport=sport))

    def search_events(self, query: str, status: Optional[str] = None) -> List[Event]:
        """
        Search events by team or league name (up to 10 results, min 3 characters).

        Args:
            query: Search term
            status: "upcoming" (default) or "live"

        Example:
            >>> client.search_events("Liverpool", status="live")
        """
        return self._get(
            Endpoints.SEARCH_EVENTS, build_params(query=query, status=status)
        )

    # Odds

    def get_event_odds(
        self,
        event_id: Union[int, str],
        bookmakers: StrList,
        markets: Optional[StrList] = None,
        include_seq: Optional[bool] = None,
    ) -> EventOdds:
        """
        Get odds for one event.

        Args:
            event_id: Event ID
            bookmakers: Bookmaker names (max 30), e.g. ["Bet365", "SingBet"]
            markets: Market names (max 40), e.g. ["ML", "Spread", "Totals"].
                See :meth:`get_markets`. Omit for every market.
            include_seq: True to get the WebSocket sequence number in the
                ``X-OddsAPI-Seq`` header (``client.last_response_headers``)

        Example:
            >>> odds = client.get_event_odds(123456, ["Bet365", "SingBet"], markets=["ML", "Totals"])
            >>> odds["bookmakers"]["Bet365"][0]["name"]
            'ML'
        """
        check_max("bookmakers", bookmakers, MAX_BOOKMAKERS)
        check_max("markets", markets, MAX_MARKETS)
        params = build_params(
            eventId=event_id,
            bookmakers=bookmakers,
            markets=markets,
            includeSeq=include_seq,
        )
        return self._get(Endpoints.GET_EVENT_ODDS, params)

    def get_odds_for_multiple_events(
        self,
        event_ids: IdList,
        bookmakers: StrList,
        markets: Optional[StrList] = None,
        include_seq: Optional[bool] = None,
    ) -> List[EventOdds]:
        """
        Get odds for up to 10 events in one request (counts as 1 call).

        Example:
            >>> client.get_odds_for_multiple_events([123, 456], "Bet365,SingBet", markets="ML")
        """
        check_max("event_ids", event_ids, MAX_MULTI_EVENTS)
        check_max("bookmakers", bookmakers, MAX_BOOKMAKERS)
        check_max("markets", markets, MAX_MARKETS)
        params = build_params(
            eventIds=event_ids,
            bookmakers=bookmakers,
            markets=markets,
            includeSeq=include_seq,
        )
        return self._get(Endpoints.GET_ODDS_FOR_MULTIPLE_EVENTS, params)

    def get_updated_odds_since_timestamp(
        self,
        since: int,
        bookmaker: str,
        sport: str,
        markets: StrList,
        limit: Optional[int] = None,
    ) -> List[EventOdds]:
        """
        Get the odds that changed since a timestamp (a delta, not a snapshot).

        Each event carries only the markets that changed. Pass the
        ``X-Next-Since`` header (``client.last_response_headers["X-Next-Since"]``)
        as ``since`` on the next call to continue with no gap.

        Args:
            since: Unix seconds, at most 90 seconds old
            bookmaker: Bookmaker name, e.g. "Bet365"
            sport: Sport name or slug
            markets: Market names, required, max 40, e.g. ["ML", "Spread", "Totals"]
            limit: Max results per response (1-10000)

        Example:
            >>> import time
            >>> rows = client.get_updated_odds_since_timestamp(
            ...     int(time.time()) - 20, "Bet365", "football", ["ML", "Totals"])
        """
        check_max("markets", markets, MAX_MARKETS)
        params = build_params(
            since=since, bookmaker=bookmaker, sport=sport, markets=markets, limit=limit
        )
        return self._get(Endpoints.GET_UPDATED_ODDS_SINCE_TIMESTAMP, params)

    def get_odds_movement(
        self,
        event_id: Union[int, str],
        bookmaker: str,
        market: str,
        market_line: Optional[Union[str, float]] = None,
    ) -> OddsMovements:
        """
        Get the pre-match price history of one market line.

        Args:
            event_id: Event ID
            bookmaker: Bookmaker name, e.g. "Bet365"
            market: Market name, e.g. "ML", "Spread", "Totals"
            market_line: Line such as 2.5 or -1.25; omit for the main line

        Returns:
            ``{opening, latest, movements}``; timestamps are Unix milliseconds.
            A 404 message lists the markets or lines that do have history.

        Example:
            >>> client.get_odds_movement(123456, "SingBet", "ML")
        """
        params = build_params(
            eventId=event_id, bookmaker=bookmaker, market=market, marketLine=market_line
        )
        return self._get(Endpoints.GET_ODDS_MOVEMENT, params)

    def get_odds_summary(
        self,
        event_id: Union[int, str],
        markets: Optional[StrList] = None,
        lines: Optional[str] = None,
        bookmakers: Optional[StrList] = None,
        include_exchanges: Optional[bool] = None,
    ) -> OddsSummary:
        """
        Best, average, median, worst and fair price per line across bookmakers.

        Growth plans and above; lower plans get a sample with ``demo: True``.

        Args:
            event_id: Event ID
            markets: Market names (max 20). Default ML, Spread, Totals.
            lines: "main" (default) or "all"
            bookmakers: Narrow to some of your selected bookmakers
            include_exchanges: True adds a separate exchanges block

        Example:
            >>> summary = client.get_odds_summary(123456, markets=["ML"])
        """
        check_max("markets", markets, MAX_SUMMARY_MARKETS)
        params = build_params(
            eventId=event_id,
            markets=markets,
            lines=lines,
            bookmakers=bookmakers,
            includeExchanges=include_exchanges,
        )
        return self._get(Endpoints.GET_ODDS_SUMMARY, params)

    def get_odds_summary_multi(
        self,
        event_ids: IdList,
        markets: Optional[StrList] = None,
        lines: Optional[str] = None,
        bookmakers: Optional[StrList] = None,
        include_exchanges: Optional[bool] = None,
    ) -> List[OddsSummary]:
        """Odds summary for up to 10 events in one request. See :meth:`get_odds_summary`."""
        check_max("event_ids", event_ids, MAX_MULTI_EVENTS)
        check_max("markets", markets, MAX_SUMMARY_MARKETS)
        params = build_params(
            eventIds=event_ids,
            markets=markets,
            lines=lines,
            bookmakers=bookmakers,
            includeExchanges=include_exchanges,
        )
        return self._get(Endpoints.GET_ODDS_SUMMARY_MULTI, params)

    # Historical

    def get_historical_events(
        self, sport: str, league: str, from_: TimeLike, to: TimeLike
    ) -> List[Event]:
        """
        Get finished events for one league in a date range of at most 31 days.

        Example:
            >>> client.get_historical_events(
            ...     "football", "england-premier-league",
            ...     "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z")
        """
        start, end = format_time(from_), format_time(to)
        check_span(start, end, MAX_HISTORICAL_SPAN_DAYS)
        params = build_params(sport=sport, league=league, **{"from": start, "to": end})
        return self._get(Endpoints.GET_HISTORICAL_EVENTS, params)

    def search_historical_events(
        self,
        query: str,
        sport: Optional[str] = None,
        from_: Optional[TimeLike] = None,
        to: Optional[TimeLike] = None,
    ) -> List[Event]:
        """
        Search finished events by team name (min 3 characters).

        The date range is at most 31 days and defaults to the trailing 31 days.

        Example:
            >>> client.search_historical_events("Arsenal", sport="football")
        """
        start, end = format_time(from_), format_time(to)
        check_span(start, end, MAX_HISTORICAL_SPAN_DAYS)
        params = build_params(query=query, sport=sport, **{"from": start, "to": end})
        return self._get(Endpoints.SEARCH_HISTORICAL_EVENTS, params)

    def get_historical_odds(
        self,
        event_id: Union[int, str],
        bookmakers: StrList,
        markets: Optional[StrList] = None,
    ) -> EventOdds:
        """
        Get the stored odds of a finished event (same shape as :meth:`get_event_odds`).

        Example:
            >>> client.get_historical_odds(123456, ["Bet365"], markets=["ML"])
        """
        check_max("bookmakers", bookmakers, MAX_BOOKMAKERS)
        params = build_params(eventId=event_id, bookmakers=bookmakers, markets=markets)
        return self._get(Endpoints.GET_HISTORICAL_ODDS, params)

    def get_closing_lines(
        self,
        sport: str,
        leagues: StrList,
        from_: TimeLike,
        to: TimeLike,
        markets: StrList,
        bookmakers: StrList,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> List[EventOdds]:
        """
        Get closing odds for every settled event in up to 10 leagues.

        Paid plans. The range may span up to 366 days; responses hold at most
        100 events, so page with ``skip`` or use :meth:`iter_closing_lines`.

        Example:
            >>> rows = client.get_closing_lines(
            ...     "football", ["england-premier-league"],
            ...     "2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z",
            ...     markets=["ML"], bookmakers=["Bet365", "SingBet"])
        """
        start, end = format_time(from_), format_time(to)
        check_span(start, end, MAX_CLOSING_LINES_SPAN_DAYS)
        check_max("leagues", leagues, MAX_CLOSING_LINES_LEAGUES)
        check_max("bookmakers", bookmakers, MAX_BOOKMAKERS)
        params = build_params(
            sport=sport,
            leagues=leagues,
            markets=markets,
            bookmakers=bookmakers,
            limit=limit,
            skip=skip,
            **{"from": start, "to": end},
        )
        return self._get(Endpoints.GET_CLOSING_LINES, params)

    def iter_closing_lines(
        self,
        sport: str,
        leagues: StrList,
        from_: TimeLike,
        to: TimeLike,
        markets: StrList,
        bookmakers: StrList,
        page_size: int = MAX_CLOSING_LINES_PAGE,
    ) -> Iterator[EventOdds]:
        """Iterate over every closing line in the range, paging with ``skip``."""
        skip = 0
        while True:
            page = self.get_closing_lines(
                sport,
                leagues,
                from_,
                to,
                markets,
                bookmakers,
                limit=page_size,
                skip=skip,
            )
            yield from page
            if len(page) < page_size:
                return
            skip += len(page)

    # Participants

    def get_participants(
        self, sport: str, search: Optional[str] = None
    ) -> List[Participant]:
        """
        Get teams and players for a sport.

        Example:
            >>> client.get_participants("basketball", search="Warriors")
        """
        return self._get(
            Endpoints.GET_PARTICIPANTS, build_params(sport=sport, search=search)
        )

    def get_participant_by_id(self, participant_id: Union[int, str]) -> Participant:
        """Get one participant by ID."""
        return self._get(Endpoints.GET_PARTICIPANT_BY_ID.format(id=participant_id))

    def get_participant_logo(self, participant_id: Union[int, str]) -> bytes:
        """
        Get a participant's crest as PNG bytes. Raises NotFoundError when there is none.

        Example:
            >>> open("crest.png", "wb").write(client.get_participant_logo(45))
        """
        path = Endpoints.GET_PARTICIPANT_LOGO.format(id=participant_id)
        return self._request("GET", path, raw=True)

    # Bookmakers

    def get_bookmakers(self) -> List[Bookmaker]:
        """
        Get all bookmakers with ``status`` (ok, degraded, down) and ``reason``.

        Example:
            >>> down = [b["name"] for b in client.get_bookmakers() if b.get("status") == "down"]
        """
        return self._get(Endpoints.GET_BOOKMAKERS)

    def get_selected_bookmakers(self) -> Dict[str, Any]:
        """Get the bookmakers selected for your key."""
        return self._get(Endpoints.GET_SELECTED_BOOKMAKERS)

    def select_bookmakers(self, bookmakers: StrList) -> Dict[str, Any]:
        """
        Add bookmakers to your selection.

        Example:
            >>> client.select_bookmakers(["Bet365", "SingBet"])
        """
        return self._put(
            Endpoints.SELECT_BOOKMAKERS, build_params(bookmakers=bookmakers)
        )

    def clear_selected_bookmakers(self) -> Dict[str, Any]:
        """Clear your bookmaker selection. Allowed once every 12 hours."""
        return self._put(Endpoints.CLEAR_SELECTED_BOOKMAKERS)

    # Betting analysis

    def get_arbitrage_bets(
        self,
        bookmakers: StrList,
        limit: Optional[int] = None,
        include_event_details: Optional[bool] = None,
        sport: Optional[str] = None,
        league: Optional[str] = None,
        markets: Optional[StrList] = None,
        min_profit: Optional[float] = None,
        all_combinations: Optional[bool] = None,
    ) -> List[ArbitrageBet]:
        """
        Get pre-match price gaps where the best odds across bookmakers imply under 100%.

        Prices move fast and bookmakers can void or limit bets, so check every
        leg before acting.

        Args:
            bookmakers: Bookmakers every leg must come from
            limit: Max results (default 50, max 500)
            include_event_details: Include teams, date, sport and league
            sport: Sport name or slug
            league: League slug (requires ``sport``)
            markets: Market names, e.g. ["ML", "Totals"]
            min_profit: Minimum ``profitMargin`` in percent (0-100)
            all_combinations: True for every bookmaker combination, not only the best

        Example:
            >>> client.get_arbitrage_bets(["Bet365", "SingBet"], sport="football", min_profit=1)
        """
        params = build_params(
            bookmakers=bookmakers,
            sport=sport,
            league=league,
            markets=markets,
            minProfit=min_profit,
            allCombinations=all_combinations,
            limit=limit,
            includeEventDetails=include_event_details,
        )
        return self._get(Endpoints.GET_ARBITRAGE_BETS, params)

    def get_value_bets(
        self,
        bookmaker: str,
        include_event_details: Optional[bool] = None,
        sport: Optional[str] = None,
        league: Optional[str] = None,
    ) -> List[ValueBet]:
        """
        Get prices above a fair-odds estimate at one bookmaker.

        Args:
            bookmaker: Bookmaker name
            include_event_details: Include teams, date, sport and league
            sport: Sport name or slug
            league: League slug (requires ``sport``)

        Example:
            >>> client.get_value_bets("Bet365", sport="baseball", league="usa-mlb")
        """
        params = build_params(
            bookmaker=bookmaker,
            sport=sport,
            league=league,
            includeEventDetails=include_event_details,
        )
        return self._get(Endpoints.GET_VALUE_BETS, params)

    def get_dropping_odds(
        self,
        sport: Optional[str] = None,
        league: Optional[str] = None,
        leagues: Optional[StrList] = None,
        markets: Optional[StrList] = None,
        time_window: Optional[str] = None,
        sort: Optional[str] = None,
        min_drop: Optional[float] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        include_event_details: Optional[bool] = None,
    ) -> List[DroppingOdds]:
        """
        Get prices that dropped at sharp bookmakers (paid plans).

        Args:
            sport: Sport name or slug
            league: One league slug (requires ``sport``); exclusive with ``leagues``
            leagues: Several league slugs
            markets: Market names, e.g. ["Spread", "Totals"]
            time_window: "opening" (default), "12h", "24h" or "48h"
            sort: "drop" (default), "recent" or "kickoff"
            min_drop: Minimum drop in percent
            limit: Results per page (max 200)
            page: Page number, 1-based. ``X-Total-Count`` is in ``last_response_headers``.
            include_event_details: Include teams, date, sport and league

        Example:
            >>> client.get_dropping_odds(sport="football", min_drop=10, include_event_details=True)
        """
        params = build_params(
            sport=sport,
            league=league,
            leagues=leagues,
            markets=markets,
            timeWindow=time_window,
            sort=sort,
            minDrop=min_drop,
            limit=limit,
            page=page,
            includeEventDetails=include_event_details,
        )
        return self._get(Endpoints.GET_DROPPING_ODDS, params)

    # Mappings

    def get_mappings(
        self,
        bookmaker: str,
        event_id: Optional[Union[int, str]] = None,
        event_ids: Optional[IdList] = None,
        market_id: Optional[str] = None,
        market_ids: Optional[StrList] = None,
        outcome_id: Optional[str] = None,
        market: Optional[str] = None,
        active: Optional[bool] = None,
        sport: Optional[str] = None,
        league: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> MappingsPage:
        """
        Map our events and selections to a bookmaker's own ids (paid plans).

        Look up by ``event_id(s)`` or ``market_id(s)``/``outcome_id``, or pass
        none of them for a bulk sync paged by ``cursor`` (see :meth:`iter_mappings`).

        Example:
            >>> client.get_mappings("Polymarket", event_id=71515842)["data"]
        """
        params = build_params(
            bookmaker=bookmaker,
            eventId=event_id,
            eventIds=event_ids,
            marketId=market_id,
            marketIds=market_ids,
            outcomeId=outcome_id,
            market=market,
            active=active,
            sport=sport,
            league=league,
            limit=limit,
            cursor=cursor,
        )
        return self._get(Endpoints.GET_MAPPINGS, params)

    def iter_mappings(self, bookmaker: str, **filters: Any) -> Iterator[MappingRow]:
        """
        Iterate over every mapping row, following ``nextCursor``.

        Example:
            >>> for row in client.iter_mappings("Kalshi", sport="american-football", limit=5000):
            ...     print(row["marketId"])
        """
        cursor = filters.pop("cursor", None)
        while True:
            page = self.get_mappings(bookmaker, cursor=cursor, **filters)
            yield from page.get("data") or []
            cursor = page.get("nextCursor")
            if not cursor:
                return

    # Settlement

    def get_settlements(self, event_ids: IdList) -> SettlementsResponse:
        """
        Get status, final score and the ``final`` flag for up to 50 events (paid plans).

        Example:
            >>> client.get_settlements([72908962, 72221318])["settlements"]
        """
        check_max("event_ids", event_ids, MAX_SETTLEMENT_EVENTS)
        return self._get(Endpoints.GET_SETTLEMENTS, build_params(eventIds=event_ids))

    def grade_bets(self, selections: Sequence[GradeSelection]) -> GradesResponse:
        """
        Grade up to 50 bets as won, lost, void, half_won or half_lost (paid plans).

        Each selection needs ``eventId``, ``market`` and ``side``, plus ``hdp``
        on markets with a line and ``label`` for player props. ``ref`` is
        echoed back. Re-send selections whose grade is not ``final``.

        Example:
            >>> client.grade_bets([
            ...     {"ref": "bet-1", "eventId": 72221292, "market": "Spread",
            ...      "hdp": -0.75, "side": "home"},
            ... ])["grades"]
        """
        check_max("selections", list(selections), MAX_SETTLEMENT_EVENTS)
        return self._post(Endpoints.GRADE_BETS, {"selections": list(selections)})

    # Outrights (add-on)

    def get_outrights(
        self,
        sport: str = "golf",
        league: Optional[str] = None,
        status: Optional[StrList] = None,
    ) -> List[Outright]:
        """
        List outright tournaments (golf today). Needs the Outrights add-on.

        Args:
            sport: Sport name or slug (default "golf")
            league: pga-tour, dp-world-tour, liv-golf or majors
            status: pending, live, settled, cancelled (default pending,live)

        Raises:
            AddOnRequiredError: the key does not have the Outrights add-on

        Example:
            >>> [t["name"] for t in client.get_outrights(league="majors")]
        """
        return self._get(
            Endpoints.GET_OUTRIGHTS,
            build_params(sport=sport, league=league, status=status),
        )

    def get_outright_odds(
        self, outright_id: Union[int, str], bookmakers: StrList
    ) -> OutrightOdds:
        """
        Get prices for one tournament.

        Markets: Winner, Top 5, Top 10, Top 20, their "(Incl. Ties)" variants
        and Make Cut. Winner and Top N runners carry ``odds`` (and ``layOdds``
        on exchanges); Make Cut runners carry ``yes``/``no``.

        Example:
            >>> odds = client.get_outright_odds(1001, ["DraftKings", "Betfair Exchange"])
        """
        check_max("bookmakers", bookmakers, MAX_BOOKMAKERS)
        params = build_params(id=outright_id, bookmakers=bookmakers)
        return self._get(Endpoints.GET_OUTRIGHT_ODDS, params)

    def get_outright_results(self, outright_id: Union[int, str]) -> OutrightResults:
        """
        Get final positions and per-market winners for one tournament.

        ``results`` and ``winners`` stay empty until the tournament is settled.

        Example:
            >>> client.get_outright_results(1001)["winners"]["Top 10"]
        """
        return self._get(Endpoints.GET_OUTRIGHT_RESULTS, build_params(id=outright_id))

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "OddsAPIClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
