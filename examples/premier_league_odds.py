"""
Premier League Odds Example

This example demonstrates how to fetch odds for all upcoming
Premier League matches from multiple bookmakers, including
direct bet links to each bookmaker.
"""

from odds_api import OddsAPIClient


def main():
    # Initialize client with your API key
    client = OddsAPIClient(api_key="your_api_key_here")

    try:
        print("Fetching Premier League events...\n")

        # Get all upcoming Premier League events
        events = client.get_events(
            sport="football",
            league="england-premier-league"
        )

        if not events:
            print("No upcoming Premier League events found.")
            return

        # Filter for pending/live events
        active_events = [e for e in events if e.get('status') in ('pending', 'live')]

        print(f"Found {len(active_events)} upcoming Premier League matches\n")
        print("=" * 100)

        for event in active_events:
            print(f"\n{event['home']} vs {event['away']}")
            print(f"Starts: {event['date']} | Status: {event.get('status', 'N/A')}")
            print("-" * 100)

            # Get odds from multiple bookmakers
            # Note: Bookmaker names are case-sensitive!
            odds_data = client.get_event_odds(
                event_id=event['id'],
                bookmakers="Bet365,SingBet,FanDuel"
            )

            if not odds_data or 'bookmakers' not in odds_data:
                print("No odds available for this match")
                print("=" * 100)
                continue

            # Display odds table
            print(f"{'Bookmaker':<15} {'Home':<10} {'Draw':<10} {'Away':<10}")
            print("-" * 100)

            for bookie_name, markets in odds_data['bookmakers'].items():
                # Find the moneyline (ML) market
                ml_market = next((m for m in markets if m['name'] == 'ML'), None)

                if ml_market and ml_market.get('odds'):
                    odds = ml_market['odds'][0]
                    home = odds.get('home', 'N/A')
                    draw = odds.get('draw', 'N/A')
                    away = odds.get('away', 'N/A')
                    print(f"{bookie_name:<15} {home:<10} {draw:<10} {away:<10}")

            # Display direct bet links
            urls = odds_data.get('urls', {})
            if urls:
                print(f"\n  Direct bet links:")
                for bookie, url in urls.items():
                    if url and url != 'N/A':
                        print(f"    {bookie}: {url}")

            print("=" * 100)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
