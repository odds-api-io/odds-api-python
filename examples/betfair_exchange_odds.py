"""
Betfair Exchange back and lay prices example.

Guide: https://odds-api.io/blog/betfair-api

Lists the next Premier League fixtures the Exchange prices, then prints
the home back and lay price for ten of them, the gap between the two,
and the midpoint as a probability.
"""

import os
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")

# Bookmaker names are case-sensitive; use them as /bookmakers lists them
BOOK = "Betfair Exchange"


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
            if "layHome" not in ml:
                continue
            back, lay = float(ml["home"]), float(ml["layHome"])
            mid = 1 / ((1 / back + 1 / lay) / 2)
            print(f'{board["home"]} v {board["away"]}: '
                  f'back {back:.2f}  lay {lay:.2f}  '
                  f'gap {(lay / back - 1) * 100:.1f}%  '
                  f'mid {mid:.2f} ({100 / mid:.1f}%)')


if __name__ == "__main__":
    main()
