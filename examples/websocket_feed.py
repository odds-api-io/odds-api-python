"""
WebSocket Real-Time Odds Feed Example

This example demonstrates how to connect to the Odds-API WebSocket feed
to receive real-time odds updates for live football matches.

Requirements:
    pip install websocket-client
"""

import websocket
import json
import time
import threading

# WebSocket endpoint
WS_URL = "wss://api.odds-api.io/v3/ws"

# Configuration
API_KEY = "YOUR_API_KEY"
MARKETS = "ML,Spread,Totals"  # Markets to subscribe to (required, max 20)
SPORT = "football"  # Sport filter (optional, max 10 sports comma-separated)
STATUS = "live"  # Only live events (or 'prematch' for upcoming events)

class OddsWebSocketClient:
    def __init__(self, api_key, markets, sport=None, status=None):
        self.api_key = api_key
        self.markets = markets
        self.sport = sport
        self.status = status
        self.ws = None
        self.should_reconnect = True
        
    def build_url(self):
        """Build WebSocket URL with query parameters"""
        url = f"{WS_URL}?apiKey={self.api_key}&markets={self.markets}"
        if self.sport:
            url += f"&sport={self.sport}"
        if self.status:
            url += f"&status={self.status}"
        return url
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'welcome':
                print(f"✓ Connected to Odds-API WebSocket")
                print(f"  Filters: markets={self.markets}, sport={self.sport}, status={self.status}")
                print(f"  Message: {data.get('message', 'N/A')}")
                print("\nListening for odds updates...\n")
                
            elif msg_type == 'created':
                print(f"[NEW] Event {data.get('id')} - {data.get('bookie')}")
                self.print_odds_update(data)
                
            elif msg_type == 'updated':
                print(f"[UPDATE] Event {data.get('id')} - {data.get('bookie')}")
                self.print_odds_update(data)
                
            elif msg_type == 'deleted':
                print(f"[DELETED] Event {data.get('id')} - {data.get('bookie')}")
                
            elif msg_type == 'no_markets':
                print(f"[INFO] No markets available for event {data.get('id')}")
                
            else:
                print(f"[UNKNOWN] Message type: {msg_type}")
                
        except json.JSONDecodeError:
            print(f"Error decoding message: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")
    
    def print_odds_update(self, data):
        """Pretty print odds update"""
        timestamp = data.get('timestamp', 'N/A')
        markets = data.get('markets', [])
        
        print(f"  Time: {timestamp}")
        
        for market in markets:
            market_name = market.get('name')
            updated_at = market.get('updatedAt', 'N/A')
            odds_list = market.get('odds', [])
            
            print(f"  Market: {market_name} (updated: {updated_at})")
            
            for odds in odds_list:
                home = odds.get('home', 'N/A')
                draw = odds.get('draw', '-')
                away = odds.get('away', 'N/A')
                max_stake = odds.get('max', 'N/A')
                
                if draw != '-':
                    print(f"    Home: {home} | Draw: {draw} | Away: {away} | Max: {max_stake}")
                else:
                    print(f"    Home: {home} | Away: {away} | Max: {max_stake}")
        
        print()  # Empty line for readability
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        print(f"WebSocket connection closed (code: {close_status_code}, msg: {close_msg})")
        
        # Attempt to reconnect after a delay
        if self.should_reconnect:
            print("Reconnecting in 5 seconds...")
            time.sleep(5)
            self.connect()
    
    def on_open(self, ws):
        """Handle WebSocket open"""
        print("WebSocket connection opened")
    
    def connect(self):
        """Connect to WebSocket"""
        url = self.build_url()
        
        # Enable trace for debugging (optional)
        # websocket.enableTrace(True)
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run WebSocket in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.should_reconnect = False
        if self.ws:
            self.ws.close()

def main():
    """Main function to run the WebSocket client"""
    print("Starting Odds-API WebSocket Feed...")
    print("-" * 60)
    
    # Create WebSocket client
    client = OddsWebSocketClient(
        api_key=API_KEY,
        markets=MARKETS,
        sport=SPORT,
        status=STATUS
    )
    
    # Connect to WebSocket
    client.connect()
    
    try:
        # Keep the main thread alive
        # Press Ctrl+C to stop
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping WebSocket feed...")
        client.disconnect()
        print("Disconnected. Goodbye!")

if __name__ == "__main__":
    main()
