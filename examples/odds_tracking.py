"""
Track prices: pre-match history of one market, then a delta loop on /odds/updated.
"""

import os
import time
from datetime import datetime, timezone

from odds_api import OddsAPIClient

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")
BOOKMAKER = "SingBet"
MARKETS = ["ML", "Spread", "Totals"]


def main():
    with OddsAPIClient(api_key=API_KEY, max_retries=2) as client:
        events = client.get_events(sport="basketball", league="usa-nba", status="pending")
        if not events:
            print("No upcoming NBA events found.")
            return
        event = events[0]
        print(f"Tracking {event['away']} @ {event['home']} ({event['id']})")

        history = client.get_odds_movement(event["id"], BOOKMAKER, "ML")
        for point in history.get("movements", [])[-10:]:
            when = datetime.fromtimestamp(point["timestamp"] / 1000, tz=timezone.utc)
            print(f"  {when:%Y-%m-%d %H:%M} home {point.get('home')} away {point.get('away')}")

        # /odds/updated is a delta: merge each response into what you hold.
        board = {}
        since = int(time.time()) - 20
        for _ in range(3):
            rows = client.get_updated_odds_since_timestamp(since, BOOKMAKER, "basketball", MARKETS)
            for row in rows:
                for market in row.get("bookmakers", {}).get(BOOKMAKER, []):
                    board[(row["id"], market["name"])] = market["odds"]
            print(f"{len(rows)} events changed, {len(board)} markets held")
            since = int(client.last_response_headers.get("X-Next-Since", int(time.time()) - 10))
            time.sleep(5)


if __name__ == "__main__":
    main()
