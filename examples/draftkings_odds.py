"""
DraftKings NFL odds example.

Guide: https://odds-api.io/blog/draftkings-api

Lists the next NFL games DraftKings prices, then prints the moneyline,
spread and total for ten of them, converted from decimal to American odds.
"""

import os
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")

# Bookmaker names are case-sensitive; use them as /bookmakers lists them
BOOK = "DraftKings"


def american(decimal):
    """Convert a decimal price string to American odds."""
    d = float(decimal)
    return f"{round((d - 1) * 100):+d}" if d >= 2 else f"{round(-100 / (d - 1)):+d}"


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        events = client.get_events(
            sport="american-football",
            league="usa-nfl",
            bookmaker=BOOK,
        )
        if not events:
            print(f"No upcoming NFL events with {BOOK} odds.")
            return
        events.sort(key=lambda e: e["date"])

        # /odds/multi takes up to ten event ids per request
        ids = ",".join(str(e["id"]) for e in events[:10])
        boards = client.get_odds_for_multiple_events(event_ids=ids, bookmakers=BOOK)

        for board in sorted(boards, key=lambda b: b["date"]):
            markets = {m["name"]: m["odds"][0] for m in board["bookmakers"].get(BOOK, [])}
            if not {"ML", "Spread", "Totals"} <= markets.keys():
                continue
            ml, spread, total = markets["ML"], markets["Spread"], markets["Totals"]
            print(f'{board["home"]} v {board["away"]}: '
                  f'ML {american(ml["home"])} / {american(ml["away"])}  '
                  f'spread {spread["hdp"]:+g} ({american(spread["home"])} / {american(spread["away"])})  '
                  f'total {total["hdp"]:g} (o {american(total["over"])} / u {american(total["under"])})')


if __name__ == "__main__":
    main()
