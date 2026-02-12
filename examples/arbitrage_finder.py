"""
Arbitrage betting finder example.

This example demonstrates how to find arbitrage opportunities
across multiple bookmakers.
"""

import os
from odds_api import OddsAPIClient

# Get your API key from https://odds-api.io/#pricing
API_KEY = os.getenv("ODDS_API_KEY", "your_api_key_here")


def calculate_arbitrage_profit(arb):
    """Calculate the profit percentage for an arbitrage opportunity."""
    # This is a simplified example - actual calculation depends on the bet structure
    if 'profitPercentage' in arb:
        return arb['profitPercentage']
    return 0


def main():
    with OddsAPIClient(api_key=API_KEY) as client:
        
        # First, get available bookmakers
        print("=== Getting Bookmakers ===")
        bookmakers = client.get_bookmakers()
        
        # Select the bookmakers you want to use for arbitrage
        # Free tier only allows 2 bookmakers, so we'll use SingBet and Bet365
        selected_bookies = "SingBet,Bet365"
        
        print(f"Using bookmakers: {selected_bookies}\n")
        
        # Find arbitrage opportunities
        print("=== Finding Arbitrage Opportunities ===")
        arb_bets = client.get_arbitrage_bets(
            bookmakers=selected_bookies,
            limit=20,  # Get top 20 opportunities
            include_event_details=True
        )
        
        if not arb_bets:
            print("No arbitrage opportunities found at the moment.")
            return
        
        print(f"Found {len(arb_bets)} arbitrage opportunities!\n")
        
        # Display the top opportunities
        for i, arb in enumerate(arb_bets[:10], 1):
            print(f"=== Opportunity #{i} ===")
            
            # Display event details if available
            if 'event' in arb:
                event = arb['event']
                home = event['home']
                away = event['away']
                print(f"Match: {away} @ {home}")
                print(f"Sport: {event['sport']}")
                print(f"League: {event['league']}")
            
            # Display arbitrage details
            profit = calculate_arbitrage_profit(arb)
            print(f"Profit: {profit:.2f}%")
            
            # Display the bets needed
            if 'bets' in arb:
                print("Required bets:")
                for bet in arb['bets']:
                    print(f"  - {bet['outcome']}: {bet['odds']} @ {bet['bookmaker']}")
            
            print()
        
        # You can also get odds for specific events
        if arb_bets:
            first_arb = arb_bets[0]
            if 'event' in first_arb and 'id' in first_arb['event']:
                event_id = str(first_arb['event']['id'])
                
                print(f"=== Detailed Odds for Event {event_id} ===")
                odds = client.get_event_odds(
                    event_id=event_id,
                    bookmakers=selected_bookies
                )
                
                # Display odds from different bookmakers
                if 'bookmakers' in odds:
                    for bookie in odds['bookmakers']:
                        print(f"\n{bookie['name']}:")
                        if 'markets' in bookie:
                            for market in bookie['markets']:
                                print(f"  {market['name']}:")
                                for outcome in market['outcomes']:
                                    print(f"    {outcome['name']}: {outcome['price']}")


if __name__ == "__main__":
    main()
