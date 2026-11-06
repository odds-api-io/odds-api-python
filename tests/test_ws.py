import asyncio
import json
from urllib.parse import parse_qs, urlparse

import pytest

websockets = pytest.importorskip("websockets")

from odds_api import InvalidAPIKeyError  # noqa: E402
from odds_api.ws import ConnectionReplacedError, OddsStream  # noqa: E402


def test_connect_url_includes_filters_and_last_seq():
    stream = OddsStream(
        "k",
        markets=["ML", "Totals"],
        channels=["odds", "scores"],
        sport="football",
        status="live",
        last_seq=42,
    )
    query = parse_qs(urlparse(stream.connect_url()).query)
    assert query["markets"] == ["ML,Totals"]
    assert query["channels"] == ["odds,scores"]
    assert query["lastSeq"] == ["42"]
    assert query["replayComplete"] == ["true"]
    assert query["status"] == ["live"]
    assert urlparse(stream.connect_url()).netloc == "api.odds-api.io"


def test_leagues_and_event_ids_are_exclusive():
    with pytest.raises(ValueError):
        OddsStream("k", markets="ML", leagues="x", event_ids=[1])


def test_resync_clears_last_seq():
    stream = OddsStream("k", markets="ML")
    stream._track({"type": "updated", "seq": 10})
    stream._track({"type": "updated", "seq": 7})
    assert stream.last_seq == 10
    stream._track({"type": "resync_required"})
    assert stream.last_seq is None


def _path(connection):
    request = getattr(connection, "request", None)
    return request.path if request is not None else connection.path


async def test_reconnects_with_last_seq_after_server_restart(monkeypatch):
    async def no_sleep(_):
        return None

    monkeypatch.setattr("odds_api.ws.asyncio.sleep", no_sleep)
    seen_paths = []

    async def handler(connection, *args):
        seen_paths.append(_path(connection))
        await connection.send(json.dumps({"type": "welcome"}))
        if len(seen_paths) == 1:
            await connection.send(
                json.dumps(
                    {
                        "type": "updated",
                        "seq": 5,
                        "id": "1",
                        "bookie": "Bet365",
                        "markets": [],
                    }
                )
            )
            await connection.close(code=1012, reason="restart")
        else:
            await connection.send(
                json.dumps(
                    {
                        "type": "updated",
                        "seq": 6,
                        "id": "1",
                        "bookie": "Bet365",
                        "markets": [],
                    }
                )
            )
            await asyncio.sleep(10)

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        stream = OddsStream("k", markets="ML", url=f"ws://127.0.0.1:{port}/v3/ws")
        received = []
        async for message in stream:
            received.append(message)
            if message.get("seq") == 6:
                await stream.close()
                break

    assert [m.get("seq") for m in received if "seq" in m] == [5, 6]
    assert "lastSeq" not in parse_qs(urlparse(seen_paths[0]).query)
    assert parse_qs(urlparse(seen_paths[1]).query)["lastSeq"] == ["5"]


async def test_stops_when_replaced_by_newer_connection():
    async def handler(connection, *args):
        await connection.send(json.dumps({"type": "welcome"}))
        await connection.close(
            code=1008, reason="connection limit reached, newer connection opened"
        )

    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        stream = OddsStream("k", markets="ML", url=f"ws://127.0.0.1:{port}/v3/ws")
        with pytest.raises(ConnectionReplacedError):
            async for _ in stream:
                pass


async def test_handshake_401_raises():
    def reject(connection, request):
        if isinstance(connection, str):
            return 401, [], b"Invalid API key\n"
        return connection.respond(401, "Invalid API key\n")

    async with websockets.serve(
        lambda *a: None, "127.0.0.1", 0, process_request=reject
    ) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        stream = OddsStream(
            "bad", markets="ML", url=f"ws://127.0.0.1:{port}/v3/ws", max_reconnects=1
        )
        with pytest.raises(InvalidAPIKeyError):
            async for _ in stream:
                pass
