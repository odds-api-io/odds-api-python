"""
Live odds over WebSocket with automatic reconnect and lastSeq resume.

Needs: pip install "odds-api-io[ws]" and a plan with WebSocket access.
For a fuller client with a REST prefetch, see websocket_feed.py.
"""

import asyncio
import os

from odds_api.ws import OddsStream

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


async def main():
    board = {}
    stream = OddsStream(
        API_KEY,
        markets=["ML", "Spread", "Totals"],
        channels=["odds", "scores", "status"],
        sport="football",
        status="live",
    )
    async for message in stream:
        kind = message.get("type")
        if kind in ("created", "updated"):
            board[(message["id"], message["bookie"])] = message["markets"]  # replace, never merge
        elif kind in ("deleted", "no_markets"):
            board.pop((message["id"], message["bookie"]), None)
        elif kind == "score":
            print(message["id"], message["scores"].get("home"), "-", message["scores"].get("away"))
        elif kind == "resync_required":
            board.clear()  # rebuild from REST, then set stream.last_seq
        print(f"{kind}: holding {len(board)} event/bookmaker boards, last seq {stream.last_seq}")


if __name__ == "__main__":
    asyncio.run(main())
