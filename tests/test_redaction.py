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


def _find_key(value, path, seen, depth=0):
    """Paths under ``value`` (attributes, items, the exception chain) that show the key."""
    if value is None or isinstance(value, (bool, int, float)) or id(value) in seen:
        return []
    if depth > 8:
        return []
    seen.add(id(value))
    found = []
    try:
        if KEY in str(value) or KEY in repr(value):
            found.append(path)
    except Exception:
        found.append(path + " (str/repr raised)")
    if isinstance(value, (str, bytes)):
        return found
    if isinstance(value, dict):
        children = list(value.items())
    elif isinstance(value, (list, tuple, set)):
        children = list(enumerate(value))
    else:
        children = []
        names = list(getattr(value, "__dict__", None) or {})
        for cls in type(value).__mro__:
            slots = cls.__dict__.get("__slots__", ())
            names += [slots] if isinstance(slots, str) else list(slots)
        for name in dict.fromkeys(names):
            try:
                children.append((name, getattr(value, name)))
            except Exception:
                pass
        if isinstance(value, BaseException):
            children += [
                ("args", value.args),
                ("__cause__", value.__cause__),
                ("__context__", value.__context__),
            ]
    for name, child in children:
        found += _find_key(child, f"{path}.{name}", seen, depth + 1)
    return found


def assert_no_key(error):
    text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert KEY not in text
    assert _find_key(error, "error", set()) == []
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


def _raised(error):
    try:
        raise error
    except BaseException as e:
        return e


def test_read_only_url_property_is_replaced_by_a_masked_stand_in():
    from yarl import URL

    error = _raised(aiohttp.InvalidURL(URL(URL_WITH_KEY), "bad redirect"))
    clean = scrub_exception(error, (KEY,))
    assert "apiKey=***" in str(clean)
    assert_no_key(clean)


@pytest.mark.parametrize(
    "error",
    [
        lambda: websockets.exceptions.InvalidHeader("Location", URL_WITH_KEY),
        lambda: websockets.exceptions.InvalidHeaderValue("Location", URL_WITH_KEY),
        lambda: websockets.exceptions.InvalidURI(URL_WITH_KEY, "bad"),
    ],
    ids=["invalid-header", "invalid-header-value", "invalid-uri"],
)
def test_websockets_exceptions_with_the_key_are_masked(error):
    clean = scrub_exception(_raised(error()), (KEY,))
    assert_no_key(clean)


def test_nested_transport_objects_are_masked():
    class Response:
        def __init__(self):
            self.body = f"echo {URL_WITH_KEY}".encode()
            self.headers = {"Location": URL_WITH_KEY}

        def __repr__(self):
            return f"Response(body={self.body!r}, headers={self.headers!r})"

    inner = _raised(OSError(f"refused {URL_WITH_KEY}"))
    error = RuntimeError("handshake failed")
    error.response = Response()
    error.__cause__ = inner
    clean = scrub_exception(_raised(error), (KEY,))
    assert clean is error
    assert_no_key(clean)


async def test_ws_malformed_header_hides_key(monkeypatch):
    def connect(url, **kwargs):
        raise websockets.exceptions.InvalidHeaderValue("Location", url)

    monkeypatch.setattr("odds_api.ws.websockets.connect", connect)
    stream = OddsStream(KEY, markets="ML", max_reconnects=0)
    with pytest.raises(websockets.exceptions.InvalidHeaderValue) as info:
        async for _ in stream:
            pass
    assert_no_key(info.value)


def test_an_exception_reached_twice_gets_the_same_stand_in():
    from yarl import URL

    shared = _raised(aiohttp.InvalidURL(URL(URL_WITH_KEY), "bad redirect"))
    outer = RuntimeError("outer")
    outer.reason = shared
    outer.__cause__ = shared
    clean = scrub_exception(_raised(outer), (KEY,))
    assert clean.reason is clean.__cause__
    assert_no_key(clean)


def test_credential_fields_in_mappings_are_masked():
    error = OddsAPIError(
        "boom",
        body={"apiKey": "other-key", "detail": "x"},
        headers={"Authorization": "Bearer other-token", "Content-Type": "json"},
    )
    clean = scrub_exception(error, (KEY,))
    assert clean.body == {"apiKey": "***", "detail": "x"}
    assert clean.headers == {"Authorization": "***", "Content-Type": "json"}


def test_live_transport_objects_are_not_modified():
    class Pool:
        def __init__(self):
            self.proxy_headers = {"Proxy-Authorization": "Basic cHJveHk6c2VjcmV0"}
            self.url = URL_WITH_KEY

    pool = Pool()
    headers = pool.proxy_headers
    error = RuntimeError("connection failed")
    error.pool = pool
    clean = scrub_exception(_raised(error), (KEY,))
    assert_no_key(clean)
    assert pool.proxy_headers is headers
    assert headers == {"Proxy-Authorization": "Basic cHJveHk6c2VjcmV0"}
    assert pool.url == URL_WITH_KEY
    assert clean.pool is not pool


def test_requests_prepared_request_is_not_modified():
    prepared = requests.Request("GET", URL_WITH_KEY).prepare()
    error = requests.ConnectionError("refused", request=prepared)
    clean = scrub_exception(_raised(error), (KEY,))
    assert_no_key(clean)
    assert prepared.url == URL_WITH_KEY
