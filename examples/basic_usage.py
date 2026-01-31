"""
Basic usage examples for the Odds-API.io SDK.

This example demonstrates:
- Initializing the client
- Getting sports and leagues
- Fetching events
- Searching for specific games
"""

from odds_api import OddsAPIClient
import os

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def main():
    # Initialize the client (use context manager for automatic cleanup)
    with OddsAPIClient(api_key=API_KEY) as client:
        
        # Get all available sports
        print("=== Available Sports ===")
        sports = client.get_sports()
        for sport in sports[:5]:  # Show first 5
            print(f"- {sport['name']} ({sport['slug']})")
        
        print(f"\nTotal: {len(sports)} sports\n")
        
        # Get leagues for basketball
        print("=== Basketball Leagues ===")
        leagues = client.get_leagues(sport="basketball")
        for league in leagues[:5]:  # Show first 5
            print(f"- {league['name']} ({league['slug']})")
        
        print(f"\nTotal: {len(leagues)} basketball leagues\n")
        
        # Get upcoming NBA events
        print("=== Upcoming NBA Games ===")
        events = client.get_events(
            sport="basketball",
            league="usa-nba",
            status="upcoming"
        )
        
        for event in events[:5]:  # Show first 5
            home = event['participants'][0]['name']
            away = event['participants'][1]['name']
            start_time = event['startTime']
            print(f"{away} @ {home} - {start_time}")
        
        print(f"\nTotal: {len(events)} upcoming NBA games\n")
        
        # Search for Lakers games
        print("=== Lakers Games ===")
        lakers_games = client.search_events(query="Lakers")
        
        for event in lakers_games[:3]:  # Show first 3
            home = event['participants'][0]['name']
            away = event['participants'][1]['name']
            print(f"{away} vs {home}")
        
        print(f"\nTotal: {len(lakers_games)} Lakers games found\n")
        
        # Get live events
        print("=== Live Basketball Events ===")
        live_events = client.get_live_events(sport="basketball")
        
        if live_events:
            for event in live_events[:3]:  # Show first 3
                home = event['participants'][0]['name']
                away = event['participants'][1]['name']
                print(f"🔴 LIVE: {away} vs {home}")
            print(f"\nTotal: {len(live_events)} live games")
        else:
            print("No live games at the moment")
        
        # Get bookmakers
        print("\n=== Available Bookmakers ===")
        bookmakers = client.get_bookmakers()
        for bookie in bookmakers[:10]:  # Show first 10
            print(f"- {bookie['name']} ({bookie['slug']})")
        
        print(f"\nTotal: {len(bookmakers)} bookmakers available")


if __name__ == "__main__":
    main()
