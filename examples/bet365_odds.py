"""
Bet365 odds example.

Guide: https://odds-api.io/blog/bet365-api

Lists the next Premier League fixtures Bet365 prices, then prints the
1X2 (ML) and the 2.5 goal line (Totals) for ten of them.
"""

import os
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")

# Bookmaker names are case-sensitive; use them as /bookmakers lists them
BOOK = "Bet365"


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        events = client.get_events(
            sport="football",
            league="england-premier-league",
            bookmaker=BOOK,
        )
        if not events:
            print(f"No upcoming Premier League events with {BOOK} odds.")
            return

        # /odds/multi takes up to ten event ids per request
        ids = ",".join(str(e["id"]) for e in events[:10])
        boards = client.get_odds_for_multiple_events(event_ids=ids, bookmakers=BOOK)

        for board in boards:
            markets = {m["name"]: m["odds"] for m in board["bookmakers"].get(BOOK, [])}
            ml = markets.get("ML", [{}])[0]
            main_line = next((o for o in markets.get("Totals", []) if o["hdp"] == 2.5), {})
            print(f'{board["home"]} v {board["away"]}: '
                  f'{ml.get("home")} / {ml.get("draw")} / {ml.get("away")}  '
                  f'O2.5 {main_line.get("over")}  U2.5 {main_line.get("under")}')


if __name__ == "__main__":
    main()
