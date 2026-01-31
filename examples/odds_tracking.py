"""
Odds movement tracking example.

This example demonstrates how to track odds changes over time
for specific events and markets.
"""

import os
import time
from datetime import datetime
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def display_odds_movement(movements):
    """Display odds movements in a readable format."""
    if not movements:
        print("No odds movements found.")
        return
    
    print(f"Total movements recorded: {len(movements)}\n")
    
    for i, movement in enumerate(movements[-10:], 1):  # Show last 10
        timestamp = movement.get('timestamp', 'N/A')
        if isinstance(timestamp, int):
            dt = datetime.fromtimestamp(timestamp)
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Movement #{i}:")
        print(f"  Time: {timestamp}")
        
        if 'odds' in movement:
            print(f"  Odds: {movement['odds']}")
        
        if 'price' in movement:
            print(f"  Price: {movement['price']}")
        
        print()


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        
        # First, get some upcoming NBA events
        print("=== Getting NBA Events ===")
        events = client.get_events(
            sport="basketball",
            league="usa-nba",
            status="upcoming"
        )
        
        if not events:
            print("No upcoming NBA events found.")
            return
        
        # Use the first event for tracking
        event = events[0]
        event_id = str(event['id'])
        
        home = event['home']
        away = event['away']
        
        print(f"\nTracking odds for: {away} @ {home}")
        print(f"Event ID: {event_id}\n")
        
        # Get current odds for this event
        print("=== Current Odds ===")
        odds = client.get_event_odds(
            event_id=event_id,
            bookmakers="Pinnacle,Bet365"
        )
        
        if 'bookmakers' in odds:
            for bookie in odds['bookmakers']:
                print(f"\n{bookie['name']}:")
                if 'markets' in bookie:
                    for market in bookie['markets'][:2]:  # Show first 2 markets
                        print(f"  {market['name']}:")
                        for outcome in market['outcomes']:
                            print(f"    {outcome['name']}: {outcome['price']}")
        
        # Track odds movements for moneyline market
        print("\n=== Odds Movement History (Moneyline) ===")
        
        movements = client.get_odds_movement(
            event_id=event_id,
            bookmaker="Pinnacle",
            market="moneyline"
        )
        
        display_odds_movement(movements)
        
        # Example: Track updates since a specific timestamp
        # Get odds updated in the last hour
        one_hour_ago = int(time.time()) - 3600
        
        print("=== Recently Updated Odds (Last Hour) ===")
        
        try:
            updated_odds = client.get_updated_odds_since_timestamp(
                since=one_hour_ago,
                bookmaker="Pinnacle",
                sport="basketball"
            )
            
            if updated_odds:
                print(f"Found {len(updated_odds)} odds updates in the last hour")
                
                for i, update in enumerate(updated_odds[:5], 1):
                    print(f"\nUpdate #{i}:")
                    if 'event' in update:
                        event = update['event']
                        home = event['home']
                        away = event['away']
                        print(f"  Match: {away} @ {home}")
                    
                    if 'timestamp' in update:
                        dt = datetime.fromtimestamp(update['timestamp'])
                        print(f"  Updated: {dt.strftime('%H:%M:%S')}")
            else:
                print("No odds updates in the last hour.")
        
        except Exception as e:
            print(f"Could not fetch recent updates: {e}")
        
        # Get odds for multiple events at once
        print("\n=== Batch Odds Fetch ===")
        
        if len(events) >= 3:
            event_ids = ",".join(str(e['id']) for e in events[:3])
            
            batch_odds = client.get_odds_for_multiple_events(
                event_ids=event_ids,
                bookmakers="Pinnacle"
            )
            
            print(f"Fetched odds for {len(batch_odds)} events in one request")


if __name__ == "__main__":
    main()
