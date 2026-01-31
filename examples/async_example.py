"""
Async client usage examples for the Odds-API.io SDK.

This example demonstrates:
- Using the async client
- Concurrent requests with asyncio.gather
- Async context manager
"""

import asyncio
import os
from odds_api import AsyncOddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


async def fetch_multiple_sports_data(client):
    """Fetch data for multiple sports concurrently."""
    
    # Fetch events for multiple sports in parallel
    basketball_events, football_events, tennis_events = await asyncio.gather(
        client.get_events(sport="basketball", league="usa-nba"),
        client.get_events(sport="american-football", league="usa-nfl"),
        client.get_events(sport="tennis"),
    )
    
    print(f"Basketball events: {len(basketball_events)}")
    print(f"Football events: {len(football_events)}")
    print(f"Tennis events: {len(tennis_events)}")
    
    return basketball_events, football_events, tennis_events


async def search_multiple_teams(client):
    """Search for multiple teams concurrently."""
    
    teams = ["Lakers", "Warriors", "Celtics", "Heat"]
    
    # Search for all teams in parallel
    results = await asyncio.gather(
        *[client.search_events(query=team) for team in teams]
    )
    
    print("\n=== Team Search Results ===")
    for team, events in zip(teams, results):
        print(f"{team}: {len(events)} games found")


async def main():
    """Main async function."""
    
    # Use async context manager for automatic cleanup
    async with AsyncOddsAPIClient(api_key=API_KEY) as client:
        
        print("=== Fetching Sports ===")
        sports = await client.get_sports()
        print(f"Found {len(sports)} sports\n")
        
        print("=== Concurrent Sports Data Fetch ===")
        await fetch_multiple_sports_data(client)
        
        print("\n=== Concurrent Team Searches ===")
        await search_multiple_teams(client)
        
        print("\n=== Live Events ===")
        live_basketball = await client.get_live_events(sport="basketball")
        if live_basketball:
            print(f"Found {len(live_basketball)} live basketball games")
            for event in live_basketball[:3]:
                home = event['participants'][0]['name']
                away = event['participants'][1]['name']
                print(f"🔴 LIVE: {away} @ {home}")
        else:
            print("No live basketball games at the moment")
        
        print("\n=== Value Bets ===")
        value_bets = await client.get_value_bets(
            bookmaker="pinnacle",
            include_event_details=True
        )
        print(f"Found {len(value_bets)} value betting opportunities")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
