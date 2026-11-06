import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from odds_api import (
    AddOnRequiredError,
    ForbiddenError,
    InvalidAPIKeyError,
    NotFoundError,
    OddsAPIClient,
    OddsAPIError,
    RateLimitError,
    RateLimitExceededError,
    ServerError,
    ValidationError,
    __version__,
)

BASE = "https://api.odds-api.io/v3"


@pytest.fixture
def client():
    with OddsAPIClient(api_key="test-key") as c:
        yield c


def last_call():
    request = responses.calls[-1].request
    parsed = urlparse(request.url)
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    return request.method, parsed.path.replace("/v3/", "", 1), query, request


CASES = [
    (lambda c: c.get_sports(), "sports", {}),
    (
        lambda c: c.get_leagues("football", all=True),
        "leagues",
        {"sport": "football", "all": "true"},
    ),
    (lambda c: c.get_markets("football"), "markets", {"sport": "football"}),
    (lambda c: c.get_markets(), "markets", {}),
    (
        lambda c: c.get_events(
            "football",
            league="england-premier-league",
            status=["pending", "live"],
            from_="2026-11-01T00:00:00Z",
            to=datetime(2026, 11, 30, tzinfo=timezone.utc),
            limit=100,
            skip=200,
            participant_id=38,
            bookmaker="Bet365",
        ),
        "events",
        {
            "sport": "football",
            "league": "england-premier-league",
            "status": "pending,live",
            "from": "2026-11-01T00:00:00Z",
            "to": "2026-11-30T00:00:00Z",
            "limit": "100",
            "skip": "200",
            "participantId": "38",
            "bookmaker": "Bet365",
        },
    ),
    (
        lambda c: c.get_events(
            "football", start="2026-11-01T00:00:00Z", end="2026-11-02T00:00:00Z"
        ),
        "events",
        {
            "sport": "football",
            "from": "2026-11-01T00:00:00Z",
            "to": "2026-11-02T00:00:00Z",
        },
    ),
    (lambda c: c.get_event_by_id(123), "events/123", {}),
    (lambda c: c.get_live_events(), "events/live", {}),
    (lambda c: c.get_live_events("tennis"), "events/live", {"sport": "tennis"}),
    (
        lambda c: c.search_events("Liverpool", status="live"),
        "events/search",
        {"query": "Liverpool", "status": "live"},
    ),
    (
        lambda c: c.get_event_odds(
            1, ["Bet365", "SingBet"], markets=["ML", "Totals"], include_seq=True
        ),
        "odds",
        {
            "eventId": "1",
            "bookmakers": "Bet365,SingBet",
            "markets": "ML,Totals",
            "includeSeq": "true",
        },
    ),
    (
        lambda c: c.get_odds_for_multiple_events([1, 2], "Bet365", markets="ML"),
        "odds/multi",
        {"eventIds": "1,2", "bookmakers": "Bet365", "markets": "ML"},
    ),
    (
        lambda c: c.get_updated_odds_since_timestamp(
            1700000000, "Bet365", "football", ["ML", "Spread"], limit=500
        ),
        "odds/updated",
        {
            "since": "1700000000",
            "bookmaker": "Bet365",
            "sport": "football",
            "markets": "ML,Spread",
            "limit": "500",
        },
    ),
    (
        lambda c: c.get_odds_movement(1, "SingBet", "Totals", market_line=2.5),
        "odds/movements",
        {
            "eventId": "1",
            "bookmaker": "SingBet",
            "market": "Totals",
            "marketLine": "2.5",
        },
    ),
    (
        lambda c: c.get_odds_summary(
            1,
            markets=["ML"],
            lines="all",
            bookmakers=["Bet365"],
            include_exchanges=True,
        ),
        "odds/summary",
        {
            "eventId": "1",
            "markets": "ML",
            "lines": "all",
            "bookmakers": "Bet365",
            "includeExchanges": "true",
        },
    ),
    (
        lambda c: c.get_odds_summary_multi([1, 2]),
        "odds/summary/multi",
        {"eventIds": "1,2"},
    ),
    (
        lambda c: c.get_historical_events(
            "football",
            "england-premier-league",
            "2026-08-01T00:00:00Z",
            "2026-08-31T00:00:00Z",
        ),
        "historical/events",
        {
            "sport": "football",
            "league": "england-premier-league",
            "from": "2026-08-01T00:00:00Z",
            "to": "2026-08-31T00:00:00Z",
        },
    ),
    (
        lambda c: c.search_historical_events("Arsenal", sport="football"),
        "historical/events/search",
        {"query": "Arsenal", "sport": "football"},
    ),
    (
        lambda c: c.get_historical_odds(9, ["Bet365"], markets=["ML"]),
        "historical/odds",
        {"eventId": "9", "bookmakers": "Bet365", "markets": "ML"},
    ),
    (
        lambda c: c.get_closing_lines(
            "football",
            ["england-premier-league", "spain-laliga"],
            "2026-01-01T00:00:00Z",
            "2026-12-31T00:00:00Z",
            ["ML"],
            ["Bet365"],
            limit=100,
            skip=0,
        ),
        "historical/closing-lines",
        {
            "sport": "football",
            "leagues": "england-premier-league,spain-laliga",
            "from": "2026-01-01T00:00:00Z",
            "to": "2026-12-31T00:00:00Z",
            "markets": "ML",
            "bookmakers": "Bet365",
            "limit": "100",
            "skip": "0",
        },
    ),
    (
        lambda c: c.get_participants("football", search="Chelsea"),
        "participants",
        {"sport": "football", "search": "Chelsea"},
    ),
    (lambda c: c.get_participant_by_id(45), "participants/45", {}),
    (lambda c: c.get_bookmakers(), "bookmakers", {}),
    (lambda c: c.get_selected_bookmakers(), "bookmakers/selected", {}),
    (
        lambda c: c.get_arbitrage_bets(
            ["Bet365", "SingBet"],
            sport="football",
            league="england-premier-league",
            markets=["Totals"],
            min_profit=1.5,
            all_combinations=True,
            limit=10,
            include_event_details=True,
        ),
        "arbitrage-bets",
        {
            "bookmakers": "Bet365,SingBet",
            "sport": "football",
            "league": "england-premier-league",
            "markets": "Totals",
            "minProfit": "1.5",
            "allCombinations": "true",
            "limit": "10",
            "includeEventDetails": "true",
        },
    ),
    (
        lambda c: c.get_value_bets(
            "Bet365", sport="baseball", league="usa-mlb", include_event_details=False
        ),
        "value-bets",
        {
            "bookmaker": "Bet365",
            "sport": "baseball",
            "league": "usa-mlb",
            "includeEventDetails": "false",
        },
    ),
    (
        lambda c: c.get_dropping_odds(
            sport="football",
            leagues=["england-premier-league", "spain-laliga"],
            markets=["Spread"],
            time_window="24h",
            sort="recent",
            min_drop=10,
            limit=50,
            page=2,
            include_event_details=True,
        ),
        "dropping-odds",
        {
            "sport": "football",
            "leagues": "england-premier-league,spain-laliga",
            "markets": "Spread",
            "timeWindow": "24h",
            "sort": "recent",
            "minDrop": "10",
            "limit": "50",
            "page": "2",
            "includeEventDetails": "true",
        },
    ),
    (
        lambda c: c.get_mappings(
            "Kalshi", market_id="KX-1", outcome_id="no", active=True
        ),
        "mappings",
        {
            "bookmaker": "Kalshi",
            "marketId": "KX-1",
            "outcomeId": "no",
            "active": "true",
        },
    ),
    (lambda c: c.get_settlements([1, 2, 3]), "settlements", {"eventIds": "1,2,3"}),
    (
        lambda c: c.get_outrights(league="majors", status=["pending", "live"]),
        "outrights",
        {"sport": "golf", "league": "majors", "status": "pending,live"},
    ),
    (
        lambda c: c.get_outright_odds(1001, ["DraftKings", "Betfair Exchange"]),
        "outrights/odds",
        {"id": "1001", "bookmakers": "DraftKings,Betfair Exchange"},
    ),
    (lambda c: c.get_outright_results(1001), "outrights/results", {"id": "1001"}),
]


@responses.activate
@pytest.mark.parametrize("call,path,expected", CASES)
def test_get_endpoints_send_expected_query(client, call, path, expected):
    responses.get(f"{BASE}/{path}", json={"ok": True})
    assert call(client) == {"ok": True}
    method, sent_path, query, request = last_call()
    assert method == "GET"
    assert sent_path == path
    assert query.pop("apiKey") == "test-key"
    assert query == expected
    assert request.headers["User-Agent"] == f"odds-api-io-python/{__version__}"


@responses.activate
def test_put_endpoints(client):
    responses.put(f"{BASE}/bookmakers/selected/select", json={"ok": 1})
    responses.put(f"{BASE}/bookmakers/selected/clear", json={"ok": 2})
    assert client.select_bookmakers(["Bet365", "SingBet"]) == {"ok": 1}
    assert last_call()[2]["bookmakers"] == "Bet365,SingBet"
    assert client.clear_selected_bookmakers() == {"ok": 2}


@responses.activate
def test_grade_bets_posts_json_body(client):
    responses.post(
        f"{BASE}/settlements/grade", json={"grades": [{"ref": "a", "result": "won"}]}
    )
    selections = [
        {"ref": "a", "eventId": 1, "market": "Spread", "hdp": -0.75, "side": "home"}
    ]
    assert client.grade_bets(selections)["grades"][0]["result"] == "won"
    method, path, query, request = last_call()
    assert method == "POST" and query == {"apiKey": "test-key"}
    assert json.loads(request.body) == {"selections": selections}


@responses.activate
def test_participant_logo_returns_bytes(client):
    responses.get(
        f"{BASE}/participants/45/logo", body=b"\x89PNG", content_type="image/png"
    )
    assert client.get_participant_logo(45) == b"\x89PNG"


@responses.activate
def test_default_base_url_and_headers_recorded(client):
    responses.get(
        f"{BASE}/odds/updated",
        json=[],
        headers={
            "X-Next-Since": "1700000010",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "2026-11-06T13:00:00Z",
        },
    )
    client.get_updated_odds_since_timestamp(1700000000, "Bet365", "football", "ML")
    assert client.last_response_headers["X-Next-Since"] == "1700000010"
    assert client.last_rate_limit.limit == 5000
    assert client.last_rate_limit.remaining == 4999
    assert client.last_rate_limit.reset == datetime(
        2026, 11, 6, 13, tzinfo=timezone.utc
    )


def test_client_side_limits(client):
    with pytest.raises(ValidationError, match="31 days"):
        client.get_historical_events(
            "football", "x", "2026-01-01T00:00:00Z", "2026-03-01T00:00:00Z"
        )
    with pytest.raises(ValidationError, match="366 days"):
        client.get_closing_lines(
            "football",
            "x",
            "2025-01-01T00:00:00Z",
            "2026-03-01T00:00:00Z",
            "ML",
            "Bet365",
        )
    with pytest.raises(ValidationError, match="leagues"):
        client.get_closing_lines(
            "football",
            [str(i) for i in range(11)],
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "ML",
            "Bet365",
        )
    with pytest.raises(ValidationError, match="markets"):
        client.get_updated_odds_since_timestamp(
            1, "Bet365", "football", [str(i) for i in range(41)]
        )
    with pytest.raises(ValidationError, match="event_ids"):
        client.get_odds_for_multiple_events(list(range(11)), "Bet365")
    with pytest.raises(ValidationError, match="before"):
        client.search_historical_events(
            "Arsenal", from_="2026-02-01T00:00:00Z", to="2026-01-01T00:00:00Z"
        )


def test_updated_odds_requires_markets(client):
    with pytest.raises(TypeError):
        client.get_updated_odds_since_timestamp(1, "Bet365", "football")


@responses.activate
def test_iter_events_pages_with_skip(client):
    responses.get(f"{BASE}/events", json=[{"id": 1}, {"id": 2}])
    responses.get(f"{BASE}/events", json=[{"id": 3}])
    assert [e["id"] for e in client.iter_events("football", page_size=2)] == [1, 2, 3]
    assert parse_qs(urlparse(responses.calls[1].request.url).query)["skip"] == ["2"]


@responses.activate
def test_iter_closing_lines_pages_with_skip(client):
    responses.get(f"{BASE}/historical/closing-lines", json=[{"id": 1}])
    rows = list(
        client.iter_closing_lines(
            "football",
            "x",
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "ML",
            "Bet365",
            page_size=5,
        )
    )
    assert rows == [{"id": 1}]


@responses.activate
def test_iter_mappings_follows_cursor(client):
    responses.get(
        f"{BASE}/mappings", json={"data": [{"marketId": "a"}], "nextCursor": "c1"}
    )
    responses.get(
        f"{BASE}/mappings", json={"data": [{"marketId": "b"}], "nextCursor": None}
    )
    rows = list(client.iter_mappings("Kalshi", sport="american-football", limit=5000))
    assert [r["marketId"] for r in rows] == ["a", "b"]
    assert parse_qs(urlparse(responses.calls[1].request.url).query)["cursor"] == ["c1"]


# Errors


@responses.activate
@pytest.mark.parametrize(
    "status,body,cls",
    [
        (400, {"error": "Missing markets parameter"}, ValidationError),
        (401, {"error": "Invalid API key"}, InvalidAPIKeyError),
        (
            403,
            {"error": "Access denied. You do not have permission for 'Bet365'."},
            ForbiddenError,
        ),
        (
            404,
            {"error": "No history for market Totals. Markets with history: ML"},
            NotFoundError,
        ),
        (500, {"error": "Failed to fetch outrights"}, ServerError),
        (418, {"error": "teapot"}, OddsAPIError),
    ],
)
def test_errors_keep_server_message(client, status, body, cls):
    responses.get(f"{BASE}/sports", json=body, status=status)
    with pytest.raises(cls) as info:
        client.get_sports()
    assert str(info.value) == body["error"]
    assert info.value.status_code == status
    assert info.value.body == body


@responses.activate
def test_outrights_add_on_error(client):
    message = "Outrights are a paid add-on. Add it in your dashboard: https://odds-api.io/dashboard/billing#outrights"
    responses.get(f"{BASE}/outrights", json={"error": message}, status=403)
    with pytest.raises(AddOnRequiredError) as info:
        client.get_outrights()
    assert str(info.value) == message
    assert info.value.add_on == "outrights"
    assert isinstance(info.value, ForbiddenError)


@responses.activate
def test_rate_limit_error_has_retry_after_from_reset_header(client):
    responses.get(
        f"{BASE}/sports",
        json={"error": "You have exceeded your rate limit of 5000 requests per hour."},
        status=429,
        headers={
            "X-RateLimit-Reset": "2999-01-01T00:00:00Z",
            "X-RateLimit-Remaining": "0",
        },
    )
    with pytest.raises(RateLimitError) as info:
        client.get_sports()
    assert RateLimitError is RateLimitExceededError
    assert info.value.retry_after > 1000
    assert info.value.rate_limit.remaining == 0
    assert "exceeded your rate limit" in str(info.value)


@responses.activate
def test_rate_limit_error_prefers_retry_after_header(client):
    responses.get(
        f"{BASE}/sports",
        json={"error": "slow down"},
        status=429,
        headers={"Retry-After": "7"},
    )
    with pytest.raises(RateLimitExceededError) as info:
        client.get_sports()
    assert info.value.retry_after == 7


@responses.activate
def test_non_json_error_body(client):
    responses.get(f"{BASE}/sports", body="Bad Gateway", status=502)
    with pytest.raises(ServerError, match="Bad Gateway"):
        client.get_sports()


@responses.activate
def test_network_error_wrapped(client):
    import requests

    responses.get(f"{BASE}/sports", body=requests.ConnectionError("boom"))
    with pytest.raises(OddsAPIError, match="Request failed"):
        client.get_sports()


# Retries


@responses.activate
def test_no_retry_by_default(client):
    responses.get(f"{BASE}/sports", json={"error": "busy"}, status=503)
    with pytest.raises(ServerError):
        client.get_sports()
    assert len(responses.calls) == 1


@responses.activate
def test_retries_5xx_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr("odds_api.client.time.sleep", sleeps.append)
    responses.get(
        f"{BASE}/sports",
        json={"error": "busy"},
        status=503,
        headers={"Retry-After": "2"},
    )
    responses.get(f"{BASE}/sports", json={"error": "bad gateway"}, status=502)
    responses.get(f"{BASE}/sports", json=[{"slug": "football"}])
    client = OddsAPIClient("k", max_retries=3)
    assert client.get_sports() == [{"slug": "football"}]
    assert len(responses.calls) == 3
    assert sleeps[0] == 2 and 0 < sleeps[1] <= 30


@responses.activate
def test_429_with_long_reset_is_not_slept_on(monkeypatch):
    monkeypatch.setattr(
        "odds_api.client.time.sleep", lambda s: pytest.fail("should not sleep")
    )
    responses.get(
        f"{BASE}/sports",
        json={"error": "limit"},
        status=429,
        headers={"Retry-After": "1800"},
    )
    client = OddsAPIClient("k", max_retries=3, max_retry_wait=30)
    with pytest.raises(RateLimitExceededError):
        client.get_sports()
    assert len(responses.calls) == 1


@responses.activate
def test_4xx_is_never_retried(monkeypatch):
    responses.get(f"{BASE}/sports", json={"error": "bad"}, status=400)
    client = OddsAPIClient("k", max_retries=3)
    with pytest.raises(ValidationError):
        client.get_sports()
    assert len(responses.calls) == 1


def test_requires_api_key():
    with pytest.raises(ValueError):
        OddsAPIClient("")


def test_custom_base_url_strips_slash():
    assert (
        OddsAPIClient("k", base_url="https://example.test/v3/").base_url
        == "https://example.test/v3"
    )
