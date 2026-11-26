"""The API key must never appear in an error, its chain or its traceback."""

import asyncio
import socket
import traceback

import aiohttp
import pytest
import requests
import responses
import websockets
from aiohttp import web
from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, ReadTimeoutError

from odds_api import (
    AsyncOddsAPIClient,
    InvalidAPIKeyError,
    OddsAPIClient,
    OddsAPIError,
    ServerError,
)
from odds_api._redact import redact, scrub_exception
from odds_api.ws import OddsStream

KEY = "sk-live-7f3a9c1e5b2d4f60a8e1"
BASE = "https://api.odds-api.io/v3"
URL_WITH_KEY = f"{BASE}/sports?apiKey={KEY}"


def _closed_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _chain(error):
    seen, todo = [], [error]
    while todo:
        current = todo.pop()
        if current is None or any(current is s for s in seen):
            continue
        seen.append(current)
        todo += [current.__cause__, current.__context__]
        todo += [a for a in current.args if isinstance(a, BaseException)]
        todo += (
            [getattr(current, "reason", None)]
            if isinstance(getattr(current, "reason", None), BaseException)
            else []
        )
    return seen


def assert_no_key(error):
    text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert KEY not in text
    for link in _chain(error):
        assert KEY not in str(link)
        assert KEY not in repr(link)
        assert KEY not in repr(link.args)
        for name in ("url", "body", "headers", "message"):
            assert KEY not in str(getattr(link, name, ""))
        for name in ("request", "response"):
            obj = getattr(link, name, None)
            assert KEY not in str(getattr(obj, "url", ""))
    assert "apiKey=***" in text or "apiKey" not in text


def test_redact_masks_key_and_key_like_params():
    text = f"GET /x?apiKey={KEY}&token=abc&api_key=def X-API-Key: ghi Authorization: Bearer jkl"
    clean = redact(text, (KEY,))
    for secret in (KEY, "abc", "def", "ghi", "jkl"):
        assert secret not in clean
    assert "apiKey=***" in clean


def test_redact_masks_url_encoded_key():
    key = "a+b/c=d"
    clean = redact("q=a%2Bb%2Fc%3Dd and a+b/c=d", (key,))
    assert "a%2Bb%2Fc%3Dd" not in clean and "a+b/c=d" not in clean


def test_redact_leaves_ordinary_words_alone():
    assert redact("monkey=1&sport=football", (KEY,)) == "monkey=1&sport=football"


def test_sync_connection_error_hides_key():
    client = OddsAPIClient(
        KEY, base_url=f"http://127.0.0.1:{_closed_port()}/v3", timeout=2
    )
    with pytest.raises(OddsAPIError) as info:
        client.get_sports()
    assert "Request failed" in str(info.value)
    assert isinstance(info.value.__cause__, requests.ConnectionError)
    assert_no_key(info.value)


@pytest.mark.parametrize(
    "error",
    [
        lambda req: requests.exceptions.ConnectTimeout(
            MaxRetryError(
                None, f"/v3/sports?apiKey={KEY}", ConnectTimeoutError(None, "timed out")
            ),
            request=req,
        ),
        lambda req: requests.exceptions.ReadTimeout(
            ReadTimeoutError(None, f"/v3/sports?apiKey={KEY}", "Read timed out."),
            request=req,
        ),
        lambda req: requests.exceptions.ConnectionError(
            MaxRetryError(None, f"/v3/sports?apiKey={KEY}", OSError("refused")),
            request=req,
        ),
    ],
    ids=["connect-timeout", "read-timeout", "connection-error"],
)
@responses.activate
def test_sync_timeouts_and_connection_errors_hide_key(error):
    prepared = requests.Request("GET", URL_WITH_KEY).prepare()
    responses.add(responses.GET, f"{BASE}/sports", body=error(prepared))
    with OddsAPIClient(KEY) as client, pytest.raises(OddsAPIError) as info:
        client.get_sports()
    assert_no_key(info.value)


@responses.activate
def test_sync_http_error_echoing_url_hides_key():
    responses.add(
        responses.GET,
        f"{BASE}/sports",
        json={"error": f"Invalid API key for {URL_WITH_KEY}", "apiKey": KEY},
        status=401,
    )
    with OddsAPIClient(KEY) as client, pytest.raises(InvalidAPIKeyError) as info:
        client.get_sports()
    assert_no_key(info.value)
    assert info.value.status_code == 401


@responses.activate
def test_sync_html_proxy_error_hides_key():
    responses.add(
        responses.GET,
        f"{BASE}/sports",
        body=f"<html>502 Bad Gateway for {URL_WITH_KEY}</html>",
        status=502,
        content_type="text/html",
    )
    with OddsAPIClient(KEY) as client, pytest.raises(ServerError) as info:
        client.get_sports()
    assert_no_key(info.value)


def test_sync_json_encoding_error_hides_key():
    with OddsAPIClient(KEY) as client, pytest.raises(OddsAPIError) as info:
        client._post("sgp/quote", {"stake": float("nan")})
    assert isinstance(info.value.__cause__, requests.exceptions.InvalidJSONError)
    assert_no_key(info.value)


async def test_async_connection_error_hides_key():
    async with AsyncOddsAPIClient(
        KEY, base_url=f"http://127.0.0.1:{_closed_port()}/v3", timeout=2
    ) as client:
        with pytest.raises(OddsAPIError) as info:
            await client.get_sports()
    assert_no_key(info.value)


@pytest.fixture
async def slow_server():
    async def handler(request):
        await asyncio.sleep(2)
        return web.json_response({"error": f"slow {request.url}"}, status=500)

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    yield f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/v3"
    await runner.cleanup()


async def test_async_timeout_hides_key(slow_server):
    async with AsyncOddsAPIClient(KEY, base_url=slow_server, timeout=0.2) as client:
        with pytest.raises(OddsAPIError) as info:
            await client.get_sports()
    assert_no_key(info.value)


@pytest.fixture
async def echo_server():
    async def handler(request):
        if request.path.endswith("/html"):
            return web.Response(text=f"bad gateway {request.url}", status=502)
        return web.json_response({"error": f"bad key in {request.url}"}, status=401)

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    yield f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/v3"
    await runner.cleanup()


async def test_async_http_and_non_json_errors_hide_key(echo_server):
    async with AsyncOddsAPIClient(KEY, base_url=echo_server) as client:
        with pytest.raises(InvalidAPIKeyError) as info:
            await client.get_sports()
        assert_no_key(info.value)
        with pytest.raises(ServerError) as info:
            await client._get("html")
        assert_no_key(info.value)


async def test_async_client_response_error_request_info_is_scrubbed():
    from yarl import URL

    info = aiohttp.RequestInfo(URL(URL_WITH_KEY), "GET", {}, URL(URL_WITH_KEY))
    error = aiohttp.ClientResponseError(info, (), status=500, message="boom")
    try:
        raise error
    except aiohttp.ClientResponseError as e:
        scrub_exception(e, (KEY,))
        assert_no_key(e)
        assert KEY not in str(e.request_info.real_url)


async def test_ws_invalid_url_hides_key():
    stream = OddsStream(KEY, markets="ML", url="not a websocket url")
    with pytest.raises(Exception) as info:
        async for _ in stream:
            pass
    assert_no_key(info.value)


async def test_ws_handshake_refusal_hides_key():
    def reject(connection, request):
        if isinstance(connection, str):
            return 401, [], f"Invalid API key {connection}\n".encode()
        return connection.respond(401, f"Invalid API key {request.path}\n")

    async with websockets.serve(
        lambda *a: None, "127.0.0.1", 0, process_request=reject
    ) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        stream = OddsStream(
            KEY, markets="ML", url=f"ws://127.0.0.1:{port}/v3/ws", max_reconnects=1
        )
        with pytest.raises(InvalidAPIKeyError) as info:
            async for _ in stream:
                pass
    assert_no_key(info.value)
