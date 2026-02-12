"""Synchronous client for the Odds-API.io API."""

from typing import Any, Dict, Optional, List
import requests

from .constants import BASE_API_URL, DEFAULT_TIMEOUT, Endpoints
from .exceptions import (
    InvalidAPIKeyError,
    NotFoundError,
    OddsAPIError,
    RateLimitExceededError,
    ValidationError,
)


class OddsAPIClient:
    """
    Synchronous client for the Odds-API.io API.

    Args:
        api_key: Your Odds-API.io API key
        timeout: Request timeout in seconds (default: 10)
        base_url: Base API URL (default: https://api2.odds-api.io/v3)

    Example:
        >>> client = OddsAPIClient(api_key="your_api_key")
        >>> sports = client.get_sports()
        >>> events = client.get_events(sport="basketball", league="usa-nba")
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT,
        base_url: str = BASE_API_URL,
    ):
        """Initialize the Odds API client."""
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url
        self.session = requests.Session()

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle API response and raise appropriate exceptions."""
        if response.ok:
            return response.json()

        status = response.status_code

        if status == 400:
            raise ValidationError(f"Invalid request: {response.text}")
        elif status == 401:
            raise InvalidAPIKeyError("Invalid API key")
        elif status == 404:
            raise NotFoundError("Resource not found")
        elif status == 429:
            raise RateLimitExceededError(
                "Rate limit exceeded - please wait before retrying"
            )
        else:
            raise OddsAPIError(f"API error {status}: {response.text}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a GET request to the API."""
        url = f"{self.base_url}/{path}"
        params = params or {}
        params["apiKey"] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise OddsAPIError(f"Request failed: {e}") from e

        return self._handle_response(response)

    def _put(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a PUT request to the API."""
        url = f"{self.base_url}/{path}"
        params = params or {}
        params["apiKey"] = self.api_key

        try:
            response = self.session.put(url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise OddsAPIError(f"Request failed: {e}") from e

        return self._handle_response(response)

    @staticmethod
    def _build_params(**kwargs) -> Dict[str, Any]:
        """Build parameter dictionary, excluding None values."""
        return {k: v for k, v in kwargs.items() if v is not None}

    # Sports & Leagues

    def get_sports(self) -> List[Dict[str, Any]]:
        """
        Get all available sports.

        Returns:
            List of sports with their details

        Example:
            >>> sports = client.get_sports()
            >>> for sport in sports:
            ...     print(sport['name'])
        """
        return self._get(Endpoints.GET_SPORTS)

    def get_leagues(self, sport: str) -> List[Dict[str, Any]]:
        """
        Get all leagues for a specific sport.

        Args:
            sport: Sport identifier (e.g., "basketball", "football")

        Returns:
            List of leagues for the specified sport

        Example:
            >>> leagues = client.get_leagues(sport="basketball")
        """
        params = self._build_params(sport=sport)
        return self._get(Endpoints.GET_LEAGUES, params)

    # Events

    def get_events(
        self,
        sport: str,
        league: Optional[str] = None,
        participant_id: Optional[int] = None,
        status: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        bookmaker: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get events with optional filters.

        Args:
            sport: Sport identifier (required)
            league: League identifier
            participant_id: Filter by participant ID
            status: Event status (e.g., "upcoming", "live", "finished")
            start: Start date/time filter (ISO 8601 format)
            end: End date/time filter (ISO 8601 format)
            bookmaker: Filter by bookmaker

        Returns:
            List of events matching the filters

        Example:
            >>> events = client.get_events(
            ...     sport="basketball",
            ...     league="usa-nba",
            ...     status="upcoming"
            ... )
        """
        params = self._build_params(
            sport=sport,
            league=league,
            participantId=participant_id,
            status=status,
            bookmaker=bookmaker,
        )

        # Map start/end to from/to
        if start:
            params["from"] = start
        if end:
            params["to"] = end

        return self._get(Endpoints.GET_EVENTS, params)

    def get_event_by_id(self, event_id: int) -> Dict[str, Any]:
        """
        Get a specific event by ID.

        Args:
            event_id: The event ID

        Returns:
            Event details

        Example:
            >>> event = client.get_event_by_id(event_id=12345)
        """
        path = Endpoints.GET_EVENT_BY_ID.format(id=event_id)
        return self._get(path)

    def get_live_events(self, sport: str) -> List[Dict[str, Any]]:
        """
        Get currently live events for a sport.

        Args:
            sport: Sport identifier

        Returns:
            List of live events

        Example:
            >>> live_events = client.get_live_events(sport="basketball")
        """
        params = self._build_params(sport=sport)
        return self._get(Endpoints.GET_LIVE_EVENTS, params)

    def search_events(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for events by keyword.

        Args:
            query: Search query

        Returns:
            List of matching events

        Example:
            >>> events = client.search_events(query="Lakers")
        """
        params = self._build_params(query=query)
        return self._get(Endpoints.SEARCH_EVENTS, params)

    # Odds

    def get_event_odds(
        self, event_id: str, bookmakers: str
    ) -> Dict[str, Any]:
        """
        Get odds for a specific event.

        Args:
            event_id: Event ID
            bookmakers: Comma-separated bookmaker slugs

        Returns:
            Odds data for the event

        Example:
            >>> odds = client.get_event_odds(
            ...     event_id="12345",
            ...     bookmakers="singbet,bet365"
            ... )
        """
        params = self._build_params(eventId=event_id, bookmakers=bookmakers)
        return self._get(Endpoints.GET_EVENT_ODDS, params)

    def get_odds_movement(
        self,
        event_id: str,
        bookmaker: str,
        market: str,
        market_line: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Track odds changes over time for an event.

        Args:
            event_id: Event ID
            bookmaker: Bookmaker slug
            market: Market type (e.g., "moneyline", "spread")
            market_line: Market line (optional, for handicap markets)

        Returns:
            List of odds movements

        Example:
            >>> movements = client.get_odds_movement(
            ...     event_id="12345",
            ...     bookmaker="singbet",
            ...     market="moneyline"
            ... )
        """
        params = self._build_params(
            eventId=event_id,
            bookmaker=bookmaker,
            market=market,
            marketLine=market_line,
        )
        return self._get(Endpoints.GET_ODDS_MOVEMENT, params)

    def get_odds_for_multiple_events(
        self, event_ids: str, bookmakers: str
    ) -> List[Dict[str, Any]]:
        """
        Get odds for multiple events at once.

        Args:
            event_ids: Comma-separated event IDs
            bookmakers: Comma-separated bookmaker slugs

        Returns:
            Odds data for multiple events

        Example:
            >>> odds = client.get_odds_for_multiple_events(
            ...     event_ids="12345,67890",
            ...     bookmakers="singbet,bet365"
            ... )
        """
        params = self._build_params(eventIds=event_ids, bookmakers=bookmakers)
        return self._get(Endpoints.GET_ODDS_FOR_MULTIPLE_EVENTS, params)

    def get_updated_odds_since_timestamp(
        self, since: int, bookmaker: str, sport: str
    ) -> List[Dict[str, Any]]:
        """
        Get odds updated since a given timestamp.

        Args:
            since: Unix timestamp
            bookmaker: Bookmaker slug
            sport: Sport identifier

        Returns:
            List of updated odds

        Example:
            >>> updated = client.get_updated_odds_since_timestamp(
            ...     since=1640000000,
            ...     bookmaker="singbet",
            ...     sport="basketball"
            ... )
        """
        params = self._build_params(since=since, bookmaker=bookmaker, sport=sport)
        return self._get(Endpoints.GET_UPDATED_ODDS_SINCE_TIMESTAMP, params)

    # Participants

    def get_participants(
        self, sport: str, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get participants (teams/players) for a sport.

        Args:
            sport: Sport identifier
            search: Optional search query

        Returns:
            List of participants

        Example:
            >>> participants = client.get_participants(
            ...     sport="basketball",
            ...     search="Warriors"
            ... )
        """
        params = self._build_params(sport=sport, search=search)
        return self._get(Endpoints.GET_PARTICIPANTS, params)

    def get_participant_by_id(self, participant_id: int) -> Dict[str, Any]:
        """
        Get a specific participant by ID.

        Args:
            participant_id: Participant ID

        Returns:
            Participant details

        Example:
            >>> participant = client.get_participant_by_id(participant_id=3428)
        """
        path = Endpoints.GET_PARTICIPANT_BY_ID.format(id=participant_id)
        return self._get(path)

    # Bookmakers

    def get_bookmakers(self) -> List[Dict[str, Any]]:
        """
        Get all available bookmakers.

        Returns:
            List of bookmakers with their details

        Example:
            >>> bookmakers = client.get_bookmakers()
        """
        return self._get(Endpoints.GET_BOOKMAKERS)

    def get_selected_bookmakers(self) -> Dict[str, Any]:
        """
        Get bookmakers currently selected for your account.

        Returns:
            Selected bookmakers configuration

        Example:
            >>> selected = client.get_selected_bookmakers()
        """
        return self._get(Endpoints.GET_SELECTED_BOOKMAKERS)

    def select_bookmakers(self, bookmakers: str) -> Dict[str, Any]:
        """
        Select bookmakers for your account.

        Args:
            bookmakers: Comma-separated bookmaker slugs

        Returns:
            Updated bookmaker selection

        Example:
            >>> client.select_bookmakers(bookmakers="singbet,bet365")
        """
        params = self._build_params(bookmakers=bookmakers)
        return self._put(Endpoints.SELECT_BOOKMAKERS, params)

    def clear_selected_bookmakers(self) -> Dict[str, Any]:
        """
        Clear all selected bookmakers.

        Returns:
            Confirmation response

        Example:
            >>> client.clear_selected_bookmakers()
        """
        return self._put(Endpoints.CLEAR_SELECTED_BOOKMAKERS)

    # Betting Analysis

    def get_arbitrage_bets(
        self,
        bookmakers: str,
        limit: Optional[int] = None,
        include_event_details: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage betting opportunities.

        Args:
            bookmakers: Comma-separated bookmaker slugs
            limit: Maximum number of results
            include_event_details: Include full event details

        Returns:
            List of arbitrage opportunities

        Example:
            >>> arb_bets = client.get_arbitrage_bets(
            ...     bookmakers="singbet,bet365",
            ...     limit=10,
            ...     include_event_details=True
            ... )
        """
        params = self._build_params(
            bookmakers=bookmakers,
            limit=limit,
            includeEventDetails=include_event_details,
        )
        return self._get(Endpoints.GET_ARBITRAGE_BETS, params)

    def get_value_bets(
        self,
        bookmaker: str,
        include_event_details: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find value betting opportunities.

        Args:
            bookmaker: Bookmaker slug
            include_event_details: Include full event details

        Returns:
            List of value bets

        Example:
            >>> value_bets = client.get_value_bets(
            ...     bookmaker="singbet",
            ...     include_event_details=True
            ... )
        """
        params = self._build_params(
            bookmaker=bookmaker,
            includeEventDetails=include_event_details,
        )
        return self._get(Endpoints.GET_VALUE_BETS, params)

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
