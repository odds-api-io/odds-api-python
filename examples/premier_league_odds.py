"""
Premier League Odds Example

This example demonstrates how to fetch odds for all upcoming
Premier League matches from multiple bookmakers.
"""

from odds_api import OddsAPIClient

def main():
    # Initialize client with your API key
    client = OddsAPIClient(api_key="YOUR_API_KEY")
    
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
        
        print(f"Found {len(events)} upcoming Premier League matches\n")
        print("=" * 100)
        
        # Fetch odds for each event
        for event in events:
            print(f"\n{event['home']} vs {event['away']}")
            print(f"Starts: {event['starts_at']}")
            print("-" * 100)
            
            # Get odds from multiple bookmakers
            # Note: Bookmaker names are case-sensitive!
            odds_data = client.get_event_odds(
                event_id=event['id'],
                bookmakers="Bet365,SingBet,FanDuel"
            )
            
            if not odds_data or 'bookmakers' not in odds_data:
                print("No odds available for this match")
                continue
            
            # Display odds in a table format
            print(f"{'Bookmaker':<15} {'Home':<10} {'Draw':<10} {'Away':<10}")
            print("-" * 100)
            
            for bookmaker in odds_data['bookmakers']:
                bookie_name = bookmaker['name']
                
                # Find the moneyline (ML) market
                ml_market = None
                for market in bookmaker.get('markets', []):
                    if market['name'] == 'ML':
                        ml_market = market
                        break
                
                if ml_market and ml_market.get('odds'):
                    odds = ml_market['odds'][0]  # Get first odds object
                    home_odds = odds.get('home', 'N/A')
                    draw_odds = odds.get('draw', 'N/A')
                    away_odds = odds.get('away', 'N/A')
                    
                    print(f"{bookie_name:<15} {home_odds:<10} {draw_odds:<10} {away_odds:<10}")
                else:
                    print(f"{bookie_name:<15} {'No ML odds available'}")
            
            print("=" * 100)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Clean up
        client.close()

if __name__ == "__main__":
    main()
