"""
Find price gaps across bookmakers with the arbitrage endpoint.

Prices move fast and bookmakers can void or limit bets, so check every leg
before acting on a result.
"""

import os

from odds_api import OddsAPIClient

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")
BOOKMAKERS = ["Bet365", "SingBet"]


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        arbs = client.get_arbitrage_bets(
            BOOKMAKERS,
            sport="football",
            markets=["ML", "Totals"],
            min_profit=0.5,
            limit=20,
            include_event_details=True,
        )
        if not arbs:
            print("No arbitrage opportunities at the moment.")
            return

        for arb in arbs[:10]:
            event = arb.get("event", {})
            market = arb["market"]
            line = f" {market['hdp']}" if "hdp" in market else ""
            print(f"{event.get('home')} vs {event.get('away')} | {market['name']}{line}")
            print(f"  margin {arb['profitMargin']:.2f}% on a total stake of {arb['totalStake']}")
            for leg, stake in zip(arb["legs"], arb["optimalStakes"]):
                print(f"  {leg['side']:>5} @ {leg['odds']} at {leg['bookmaker']}: stake {stake['stake']}")


if __name__ == "__main__":
    main()
