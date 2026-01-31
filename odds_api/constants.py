"""Constants and endpoint definitions for the Odds-API.io API."""

BASE_API_URL = "https://api2.odds-api.io/v3"
DEFAULT_TIMEOUT = 10


class Endpoints:
    """API endpoint paths."""

    # Arbitrage
    GET_ARBITRAGE_BETS = "arbitrage-bets"

    # Bookmakers
    GET_BOOKMAKERS = "bookmakers"
    GET_SELECTED_BOOKMAKERS = "bookmakers/selected"
    CLEAR_SELECTED_BOOKMAKERS = "bookmakers/selected/clear"
    SELECT_BOOKMAKERS = "bookmakers/selected/select"

    # Events
    GET_EVENTS = "events"
    GET_LIVE_EVENTS = "events/live"
    SEARCH_EVENTS = "events/search"
    GET_EVENT_BY_ID = "events/{id}"

    # Leagues
    GET_LEAGUES = "leagues"

    # Odds
    GET_EVENT_ODDS = "odds"
    GET_ODDS_MOVEMENT = "odds/movements"
    GET_ODDS_FOR_MULTIPLE_EVENTS = "odds/multi"
    GET_UPDATED_ODDS_SINCE_TIMESTAMP = "odds/updated"

    # Participants
    GET_PARTICIPANTS = "participants"
    GET_PARTICIPANT_BY_ID = "participants/{id}"

    # Sports
    GET_SPORTS = "sports"

    # Value Bets
    GET_VALUE_BETS = "value-bets"
