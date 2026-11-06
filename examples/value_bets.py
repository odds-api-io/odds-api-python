"""
Find prices above a fair-odds estimate at one bookmaker.

expectedValue is bookmaker odds / fair odds x 100: 103.42 means a 3.42% edge at that price.
The edge in percent is expectedValue - 100; values below 100 are a negative edge.
"""

import os

from odds_api import OddsAPIClient

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")
MIN_EDGE_PERCENT = 2


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        bets = client.get_value_bets("Bet365", sport="football", include_event_details=True)
        bets = sorted(bets, key=lambda b: b["expectedValue"], reverse=True)
        bets = [b for b in bets if b["expectedValue"] - 100 >= MIN_EDGE_PERCENT]
        if not bets:
            print("No value bets at the moment.")
            return

        for bet in bets[:15]:
            event = bet.get("event", {})
            market = bet["market"]
            line = f" {market['hdp']}" if "hdp" in market else ""
            price = bet.get("bookmakerOdds", {}).get(bet["betSide"])
            print(f"{event.get('home')} vs {event.get('away')} ({event.get('date')})")
            print(
                f"  {market['name']}{line} {bet['betSide']} @ {price}: "
                f"edge {bet['expectedValue'] - 100:+.2f}%"
            )


if __name__ == "__main__":
    main()
