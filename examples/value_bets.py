"""
Value betting finder example.

This example demonstrates how to find value betting opportunities
with positive expected value.
"""

import os
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        
        print("=== Finding Value Bets ===\n")
        
        # Find value bets from Pinnacle
        # Pinnacle is often used as the "sharp" bookmaker for true probability
        value_bets = client.get_value_bets(
            bookmaker="Pinnacle",
            include_event_details=True
        )
        
        if not value_bets:
            print("No value bets found at the moment.")
            return
        
        print(f"Found {len(value_bets)} value betting opportunities!\n")
        
        # Display value bets sorted by expected value
        for i, bet in enumerate(value_bets[:15], 1):
            print(f"=== Value Bet #{i} ===")
            
            # Event details
            if 'event' in bet:
                event = bet['event']
                home = event['home']
                away = event['away']
                print(f"Match: {away} @ {home}")
                print(f"Sport: {event.get('sport', 'N/A')}")
                print(f"League: {event.get('league', 'N/A')}")
                print(f"Start: {event.get('startTime', 'N/A')}")
            
            # Value bet details
            if 'expectedValue' in bet:
                ev = bet['expectedValue']
                print(f"Expected Value: {ev:.2f}%")
            
            if 'outcome' in bet:
                print(f"Bet on: {bet['outcome']}")
            
            if 'odds' in bet:
                print(f"Odds: {bet['odds']}")
            
            if 'impliedProbability' in bet:
                print(f"Implied Probability: {bet['impliedProbability']:.2f}%")
            
            if 'trueProbability' in bet:
                print(f"True Probability: {bet['trueProbability']:.2f}%")
            
            print()
        
        # Example: Get more details about a specific event
        if value_bets and 'event' in value_bets[0]:
            first_event = value_bets[0]['event']
            if 'id' in first_event:
                event_id = str(first_event['id'])
                
                print(f"=== Detailed Event Information ===")
                event_details = client.get_event_by_id(event_id=int(event_id))
                
                print(f"Event ID: {event_details.get('id')}")
                print(f"Status: {event_details.get('status')}")
                
                if 'participants' in event_details:
                    print("Participants:")
                    for participant in event_details['participants']:
                        print(f"  - {participant['name']}")


if __name__ == "__main__":
    main()
