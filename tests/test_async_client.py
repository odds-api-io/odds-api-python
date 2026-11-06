import json

import aiohttp
import pytest
from aiohttp import web

from odds_api import (
    AddOnRequiredError,
    AsyncOddsAPIClient,
    NotFoundError,
    OddsAPIError,
    RateLimitExceededError,
    ServerError,
    __version__,
)

from .test_client import CASES


class FakeAPI:
    """A local aiohttp server that replays queued responses and records requests."""

    def __init__(self):
        self.queue = {}
        self.requests = []

    def add(
        self,
        method,
        path,
        payload=None,
        status=200,
        headers=None,
        body=None,
        content_type=None,
    ):
        self.queue.setdefault((method, path), []).append(
            (payload, status, headers or {}, body, content_type)
        )

    async def handle(self, request):
        path = request.path.replace("/v3/", "", 1)
        raw = await request.read()
        self.requests.append(
            {
                "method": request.method,
                "path": path,
                "query": dict(request.query),
                "json": json.loads(raw) if raw else None,
                "headers": dict(request.headers),
            }
        )
        queued = self.queue.get((request.method, path)) or []
        if not queued:
            return web.json_response({"error": "not queued"}, status=599)
        payload, status, headers, body, content_type = (
            queued.pop(0) if len(queued) > 1 else queued[0]
        )
        if body is not None:
            return web.Response(
                body=body, status=status, headers=headers, content_type=content_type
            )
        return web.json_response(payload, status=status, headers=headers)


@pytest.fixture
async def api():
    fake = FakeAPI()
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    fake.base_url = f"http://127.0.0.1:{port}/v3"
    yield fake
    await runner.cleanup()


@pytest.fixture
async def client(api):
    async with AsyncOddsAPIClient(api_key="test-key", base_url=api.base_url) as c:
        yield c


@pytest.mark.parametrize("call,path,expected", CASES)
async def test_get_endpoints_send_expected_query(api, client, call, path, expected):
    api.add("GET", path, {"ok": True})
    assert await call(client) == {"ok": True}
    request = api.requests[-1]
    assert request["method"] == "GET" and request["path"] == path
    query = request["query"]
    assert query.pop("apiKey") == "test-key"
    assert query == expected
    assert request["headers"]["User-Agent"] == f"odds-api-io-python/{__version__}"


async def test_put_and_post(api, client):
    api.add("PUT", "bookmakers/selected/select", {"ok": 1})
    api.add("PUT", "bookmakers/selected/clear", {"ok": 2})
    api.add("POST", "settlements/grade", {"grades": []})
    assert await client.select_bookmakers(["Bet365", "SingBet"]) == {"ok": 1}
    assert api.requests[-1]["query"]["bookmakers"] == "Bet365,SingBet"
    assert await client.clear_selected_bookmakers() == {"ok": 2}
    selections = [{"eventId": 1, "market": "ML", "side": "home"}]
    assert await client.grade_bets(selections) == {"grades": []}
    assert api.requests[-1]["json"] == {"selections": selections}
    assert api.requests[-1]["query"] == {"apiKey": "test-key"}


async def test_logo_bytes(api, client):
    api.add("GET", "participants/45/logo", body=b"\x89PNG", content_type="image/png")
    assert await client.get_participant_logo(45) == b"\x89PNG"


async def test_add_on_error_keeps_message(api, client):
    message = "Outrights are a paid add-on. Add it in your dashboard: https://odds-api.io/dashboard/billing#outrights"
    api.add("GET", "outrights/odds", {"error": message}, status=403)
    with pytest.raises(AddOnRequiredError) as info:
        await client.get_outright_odds(1, "DraftKings")
    assert str(info.value) == message
    assert info.value.status_code == 403


async def test_not_found_keeps_message(api, client):
    api.add("GET", "odds/movements", {"error": "Markets with history: ML"}, status=404)
    with pytest.raises(NotFoundError, match="Markets with history: ML"):
        await client.get_odds_movement(1, "Bet365", "Totals")


async def test_rate_limit_and_headers(api, client):
    api.add(
        "GET",
        "sports",
        {"error": "limit"},
        status=429,
        headers={"Retry-After": "5", "X-RateLimit-Remaining": "0"},
    )
    with pytest.raises(RateLimitExceededError) as info:
        await client.get_sports()
    assert info.value.retry_after == 5
    assert client.last_rate_limit.remaining == 0


async def test_retry_then_success(api, monkeypatch):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr("odds_api.async_client.asyncio.sleep", fake_sleep)
    api.add(
        "GET", "sports", {"error": "busy"}, status=503, headers={"Retry-After": "1"}
    )
    api.add("GET", "sports", [{"slug": "golf"}])
    async with AsyncOddsAPIClient("k", base_url=api.base_url, max_retries=2) as client:
        assert await client.get_sports() == [{"slug": "golf"}]
    assert sleeps == [1.0]
    assert len(api.requests) == 2


async def test_no_retry_by_default(api, client):
    api.add("GET", "sports", {"error": "busy"}, status=503)
    with pytest.raises(ServerError, match="busy"):
        await client.get_sports()
    assert len(api.requests) == 1


async def test_network_error():
    async with AsyncOddsAPIClient(
        "k", base_url="http://127.0.0.1:9/v3", timeout=2
    ) as client:
        with pytest.raises(OddsAPIError, match="Request failed") as info:
            await client.get_sports()
    assert isinstance(info.value.__cause__, (aiohttp.ClientError, OSError))


async def test_async_iterators(api, client):
    api.add("GET", "events", [{"id": 1}, {"id": 2}])
    api.add("GET", "events", [])
    api.add("GET", "mappings", {"data": [{"marketId": "a"}], "nextCursor": "x"})
    api.add("GET", "mappings", {"data": [{"marketId": "b"}], "nextCursor": None})
    api.add("GET", "historical/closing-lines", [{"id": 9}])
    assert [e["id"] async for e in client.iter_events("football", page_size=2)] == [
        1,
        2,
    ]
    assert [r["marketId"] async for r in client.iter_mappings("Kalshi")] == ["a", "b"]
    assert api.requests[-1]["query"]["cursor"] == "x"
    rows = [
        r
        async for r in client.iter_closing_lines(
            "football",
            "x",
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
            "ML",
            "Bet365",
        )
    ]
    assert rows == [{"id": 9}]
