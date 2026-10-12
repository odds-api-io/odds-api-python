"""
Bet settlement example.

Guide: https://odds-api.io/blog/bet-grading-api

Grades the stored bets in data/bets.json, 50 per request, and keeps the ones
whose result is not final yet so they can be sent again later.
"""

import json
import os
from pathlib import Path

from odds_api import OddsAPIClient

# Settlement needs a paid plan: https://odds-api.io/pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")

BETS_FILE = Path(__file__).parent / "data" / "bets.json"


def main():
    bets = json.loads(BETS_FILE.read_text())
    open_bets = []

    with OddsAPIClient(api_key=API_KEY) as client:
        for start in range(0, len(bets), 50):
            chunk = bets[start:start + 50]
            grades = client.grade_bets(chunk)["grades"]

            for bet, grade in zip(chunk, grades):
                basis = grade.get("basis") or {}
                score = (
                    f'{basis["home"]}-{basis["away"]} {basis["scope"]}'
                    if "home" in basis else ""
                )
                print(
                    f'{grade["ref"]:<16} {grade["result"]:<12} '
                    f'{grade["reason"] or "":<20} '
                    f'final={str(grade["final"]).lower():<6} {score}'
                )
                if not grade["final"]:
                    open_bets.append(bet)

    print(f"{len(bets) - len(open_bets)} settled, {len(open_bets)} to check again later")


if __name__ == "__main__":
    main()
