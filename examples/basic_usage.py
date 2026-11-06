"""
Basic usage of the Odds-API.io SDK: sports, leagues, markets, events and odds.
"""

import os

from odds_api import OddsAPIClient

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        sports = client.get_sports()
        print(f"{len(sports)} sports, e.g. {[s['slug'] for s in sports[:5]]}")

        leagues = client.get_leagues(sport="basketball")
        print(f"{len(leagues)} basketball leagues")

        markets = client.get_markets("basketball")["markets"]
        print("Basketball markets:", [m["name"] for m in markets[:8]])

        events = client.get_events(sport="basketball", league="usa-nba", status="pending")
        for event in events[:5]:
            print(f"{event['id']}: {event['away']} @ {event['home']} - {event['date']}")

        if events:
            odds = client.get_event_odds(
                events[0]["id"], ["Bet365", "SingBet"], markets=["ML", "Spread", "Totals"]
            )
            for bookmaker, book_markets in odds.get("bookmakers", {}).items():
                for market in book_markets:
                    print(bookmaker, market["name"], market["odds"][:1])

        for event in client.search_events("Lakers")[:3]:
            print(f"Search: {event['away']} @ {event['home']}")

        for event in client.get_live_events(sport="basketball")[:3]:
            scores = event.get("scores", {})
            print(f"LIVE: {event['home']} {scores.get('home')}-{scores.get('away')} {event['away']}")

        down = [b["name"] for b in client.get_bookmakers() if b.get("status") == "down"]
        print("Bookmakers down right now:", down or "none")


if __name__ == "__main__":
    main()
