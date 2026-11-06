"""Constants and endpoint definitions for the Odds-API.io API."""

BASE_API_URL = "https://api.odds-api.io/v3"
WEBSOCKET_URL = "wss://api.odds-api.io/v3/ws"
DEFAULT_TIMEOUT = 10

EVENT_STATUSES = ("pending", "live", "settled", "cancelled")

GOLF_OUTRIGHT_MARKETS = (
    "Winner",
    "Top 5",
    "Top 5 (Incl. Ties)",
    "Top 10",
    "Top 10 (Incl. Ties)",
    "Top 20",
    "Top 20 (Incl. Ties)",
    "Make Cut",
)

GOLF_OUTRIGHT_LEAGUES = ("pga-tour", "dp-world-tour", "liv-golf", "majors")

MAX_MARKETS = 40
MAX_SUMMARY_MARKETS = 20
MAX_BOOKMAKERS = 30
MAX_MULTI_EVENTS = 10
MAX_SETTLEMENT_EVENTS = 50
MAX_HISTORICAL_SPAN_DAYS = 31
MAX_CLOSING_LINES_SPAN_DAYS = 366
MAX_CLOSING_LINES_LEAGUES = 10
MAX_CLOSING_LINES_PAGE = 100


class Endpoints:
    """API endpoint paths."""

    GET_ARBITRAGE_BETS = "arbitrage-bets"
    GET_DROPPING_ODDS = "dropping-odds"
    GET_VALUE_BETS = "value-bets"

    GET_BOOKMAKERS = "bookmakers"
    GET_SELECTED_BOOKMAKERS = "bookmakers/selected"
    CLEAR_SELECTED_BOOKMAKERS = "bookmakers/selected/clear"
    SELECT_BOOKMAKERS = "bookmakers/selected/select"

    GET_EVENTS = "events"
    GET_LIVE_EVENTS = "events/live"
    SEARCH_EVENTS = "events/search"
    GET_EVENT_BY_ID = "events/{id}"

    GET_SPORTS = "sports"
    GET_LEAGUES = "leagues"
    GET_MARKETS = "markets"

    GET_EVENT_ODDS = "odds"
    GET_ODDS_MOVEMENT = "odds/movements"
    GET_ODDS_FOR_MULTIPLE_EVENTS = "odds/multi"
    GET_UPDATED_ODDS_SINCE_TIMESTAMP = "odds/updated"
    GET_ODDS_SUMMARY = "odds/summary"
    GET_ODDS_SUMMARY_MULTI = "odds/summary/multi"

    GET_HISTORICAL_EVENTS = "historical/events"
    SEARCH_HISTORICAL_EVENTS = "historical/events/search"
    GET_HISTORICAL_ODDS = "historical/odds"
    GET_CLOSING_LINES = "historical/closing-lines"

    GET_PARTICIPANTS = "participants"
    GET_PARTICIPANT_BY_ID = "participants/{id}"
    GET_PARTICIPANT_LOGO = "participants/{id}/logo"

    GET_MAPPINGS = "mappings"

    GET_SETTLEMENTS = "settlements"
    GRADE_BETS = "settlements/grade"

    GET_OUTRIGHTS = "outrights"
    GET_OUTRIGHT_ODDS = "outrights/odds"
    GET_OUTRIGHT_RESULTS = "outrights/results"
