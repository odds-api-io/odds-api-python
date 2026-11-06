"""
Closing lines for a league, as a pandas DataFrame, plus closing line value (CLV)
of a price you took.

Needs: pip install "odds-api-io[pandas]"
"""

import os

from odds_api import OddsAPIClient
from odds_api.dataframes import closing_lines_to_dataframe

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def main():
    with OddsAPIClient(api_key=API_KEY, max_retries=2) as client:
        rows = list(
            client.iter_closing_lines(
                sport="football",
                leagues=["england-premier-league"],
                from_="2026-08-01T00:00:00Z",
                to="2026-10-31T23:59:59Z",
                markets=["ML"],
                bookmakers=["Bet365", "SingBet"],
            )
        )
        df = closing_lines_to_dataframe(rows)
        print(df[["date", "home_team", "away_team", "bookmaker", "home", "draw", "away"]].head())

        # CLV of a 2.30 home bet against the SingBet close: positive means you beat the close.
        close = df[(df.bookmaker == "SingBet") & (df.market == "ML")].iloc[0]
        print(f"CLV on {close.home_team}: {2.30 / close.home - 1:+.2%}")


if __name__ == "__main__":
    main()
