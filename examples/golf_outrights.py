"""
Golf outright odds (Winner, Top 5/10/20, the "(Incl. Ties)" variants, Make Cut)
and results. Needs the Outrights add-on on your plan.
"""

import os

from odds_api import AddOnRequiredError, OddsAPIClient

# Get an API key at https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")
BOOKMAKERS = ["DraftKings", "Betfair Exchange"]


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        try:
            tournaments = client.get_outrights(sport="golf", league="pga-tour")
        except AddOnRequiredError as e:
            print(e)  # the server's message, with the link to add Outrights
            return

        priced = [t for t in tournaments if t.get("bookmakerCount")]
        if not priced:
            print("No priced tournaments right now.")
            return
        tournament = priced[0]
        print(f"{tournament['name']} ({tournament['date']})")

        odds = client.get_outright_odds(tournament["id"], BOOKMAKERS)
        for bookmaker, markets in odds["bookmakers"].items():
            for market in markets:
                runners = market["odds"][:3]
                if market["name"] == "Make Cut":
                    prices = [f"{r['label']} yes {r.get('yes')}" for r in runners]
                else:
                    prices = [f"{r['label']} {r.get('odds')}" for r in runners]
                print(f"  {bookmaker} | {market['name']}: {', '.join(prices)}")

        settled = client.get_outrights(sport="golf", status="settled")
        if settled:
            results = client.get_outright_results(settled[-1]["id"])
            print(f"{results['name']} winner ids: {results['winners'].get('Winner')}")


if __name__ == "__main__":
    main()
