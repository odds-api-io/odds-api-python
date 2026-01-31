"""
WebSocket Real-Time Odds Feed with Optional Initial Snapshot

Connects to the Odds-API WebSocket for real-time odds updates.
Optionally pre-fetches all current odds via REST API first, so you
have a complete snapshot before the live feed starts.

Usage:
    # WebSocket only (no initial fetch)
    python websocket_feed.py

    # With initial snapshot (recommended)
    python websocket_feed.py --prefetch

Requirements:
    pip install websocket-client odds-api-io
"""

import websocket
import json
import time
import threading
import argparse
from odds_api import OddsAPIClient

# ─── Configuration ────────────────────────────────────────────────────
API_KEY = "your_api_key_here"

# WebSocket filters
MARKETS = "ML,Spread,Totals"       # Required (max 20, comma-separated)
SPORT = "football"                  # Optional (max 10, comma-separated)
LEAGUES = "england-premier-league"  # Optional (max 20, comma-separated)
STATUS = "prematch"                 # "live" or "prematch" (optional)
BOOKMAKERS = "Bet365,SingBet"       # Bookmakers for initial fetch

# WebSocket endpoint
WS_URL = "wss://api.odds-api.io/v3/ws"
# ─────────────────────────────────────────────────────────────────────


class OddsWebSocketClient:
    """
    Real-time odds client with optional REST API pre-fetch.

    When prefetch=True, fetches all current odds via REST before
    connecting to WebSocket. This gives you a complete snapshot
    so you don't miss any data while connecting.
    """

    def __init__(self, api_key, markets, sport=None, leagues=None,
                 status=None, bookmakers=None, prefetch=False):
        self.api_key = api_key
        self.markets = markets
        self.sport = sport
        self.leagues = leagues
        self.status = status
        self.bookmakers = bookmakers or "Bet365"
        self.prefetch = prefetch
        self.ws = None
        self.should_reconnect = True
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        # In-memory odds store (event_id -> bookmaker -> markets)
        self.odds_store = {}

    def initial_fetch(self):
        """
        Pre-fetch all current odds via REST API.
        Populates self.odds_store with a complete snapshot.
        """
        print("=" * 60)
        print("INITIAL FETCH: Loading current odds via REST API...")
        print("=" * 60)

        client = OddsAPIClient(api_key=self.api_key)

        try:
            # Get events for the configured sport/league
            events = client.get_events(
                sport=self.sport or "football",
                league=self.leagues or None
            )

            # Filter by status if set
            if self.status:
                events = [e for e in events
                          if e.get('status') == self.status]

            print(f"Found {len(events)} events. Fetching odds...\n")

            for event in events:
                event_id = event['id']
                home = event.get('home', '?')
                away = event.get('away', '?')

                try:
                    odds_data = client.get_event_odds(
                        event_id=event_id,
                        bookmakers=self.bookmakers
                    )

                    bookmakers = odds_data.get('bookmakers', {})
                    if bookmakers:
                        self.odds_store[str(event_id)] = bookmakers

                        # Print summary
                        for bookie, markets in bookmakers.items():
                            ml = next((m for m in markets if m['name'] == 'ML'), None)
                            if ml and ml.get('odds'):
                                o = ml['odds'][0]
                                print(f"  {home} vs {away} [{bookie}]: "
                                      f"H {o.get('home', '-')} | "
                                      f"D {o.get('draw', '-')} | "
                                      f"A {o.get('away', '-')}")

                except Exception as e:
                    print(f"  {home} vs {away}: Could not fetch odds ({e})")

            print(f"\nInitial fetch complete: {len(self.odds_store)} events loaded")
            print("=" * 60)
            print()

        finally:
            client.close()

    def build_url(self):
        """Build WebSocket URL with query parameters."""
        params = f"apiKey={self.api_key}&markets={self.markets}"
        if self.sport:
            params += f"&sport={self.sport}"
        if self.leagues:
            params += f"&leagues={self.leagues}"
        if self.status:
            params += f"&status={self.status}"
        return f"{WS_URL}?{params}"

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages.

        The server may send multiple JSON objects in a single
        WebSocket frame (one per line), so we split and parse each.
        """
        for line in message.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                self._handle_parsed(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")

    def _handle_parsed(self, data):
        """Process a single parsed message."""
        try:
            msg_type = data.get('type')

            if msg_type == 'welcome':
                print("Connected to Odds-API WebSocket")
                print(f"  Bookmakers: {data.get('bookmakers', [])}")
                print(f"  Sports: {data.get('sport_filter', [])}")
                print(f"  Leagues: {data.get('leagues_filter', [])}")
                print(f"  Status: {data.get('status_filter', 'all')}")
                if data.get('warning'):
                    print(f"  Warning: {data['warning']}")
                print("\nListening for real-time updates...\n")

            elif msg_type in ('created', 'updated'):
                event_id = data.get('id', '?')
                bookie = data.get('bookie', '?')
                label = "NEW" if msg_type == 'created' else "UPDATE"

                # Update local store
                if event_id not in self.odds_store:
                    self.odds_store[event_id] = {}
                self.odds_store[event_id][bookie] = data.get('markets', [])

                # Print update
                print(f"[{label}] Event {event_id} | {bookie}")
                for market in data.get('markets', []):
                    odds = market.get('odds', [{}])[0]
                    name = market.get('name', '?')
                    if name == 'ML':
                        print(f"  {name}: H {odds.get('home', '-')} | "
                              f"D {odds.get('draw', '-')} | "
                              f"A {odds.get('away', '-')}")
                    elif name == 'Totals':
                        print(f"  {name} ({odds.get('hdp', '?')}): "
                              f"O {odds.get('over', '-')} | "
                              f"U {odds.get('under', '-')}")
                    elif name == 'Spread':
                        print(f"  {name} ({odds.get('hdp', '?')}): "
                              f"H {odds.get('home', '-')} | "
                              f"A {odds.get('away', '-')}")
                print()

            elif msg_type == 'deleted':
                event_id = data.get('id', '?')
                bookie = data.get('bookie', '?')
                print(f"[DELETED] Event {event_id} | {bookie}\n")
                # Remove from store
                if event_id in self.odds_store:
                    self.odds_store[event_id].pop(bookie, None)

            elif msg_type == 'no_markets':
                print(f"[NO MARKETS] Event {data.get('id', '?')}\n")

        except Exception as e:
            print(f"Error handling message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"Disconnected (code: {close_status_code})")
        if self.should_reconnect:
            self.reconnect_attempts += 1
            if self.reconnect_attempts > self.max_reconnect_attempts:
                print(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached. Giving up.")
                return
            # Exponential backoff: 1s, 2s, 4s, 8s... capped at 30s
            delay = min(2 ** (self.reconnect_attempts - 1), 30)
            print(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            time.sleep(delay)
            self._start_ws()

    def on_open(self, ws):
        print("WebSocket connection opened")
        self.reconnect_attempts = 0  # Reset on successful connection

    def _start_ws(self):
        """Start WebSocket connection in background thread."""
        self.ws = websocket.WebSocketApp(
            self.build_url(),
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        # ping_interval keeps the connection alive and detects dead connections
        ws_thread = threading.Thread(
            target=self.ws.run_forever,
            kwargs={"ping_interval": 30, "ping_timeout": 10}
        )
        ws_thread.daemon = True
        ws_thread.start()

    def start(self):
        """
        Start the client. If prefetch is enabled, loads all current
        odds via REST API first, then connects to WebSocket.
        """
        if self.prefetch:
            self.initial_fetch()

        print("Connecting to WebSocket for real-time updates...")
        self._start_ws()

    def stop(self):
        """Stop the client."""
        self.should_reconnect = False
        if self.ws:
            self.ws.close()

    def get_odds(self, event_id):
        """Get current odds for an event from the local store."""
        return self.odds_store.get(str(event_id), {})


def main():
    parser = argparse.ArgumentParser(
        description="Odds-API WebSocket feed with optional initial snapshot"
    )
    parser.add_argument(
        '--prefetch', action='store_true',
        help='Pre-fetch all current odds via REST API before connecting '
             'to WebSocket (recommended for complete data)'
    )
    args = parser.parse_args()

    print("Odds-API.io Real-Time Feed")
    print("-" * 60)

    if args.prefetch:
        print("Mode: Initial REST fetch + WebSocket (recommended)\n")
    else:
        print("Mode: WebSocket only (use --prefetch for initial snapshot)\n")

    client = OddsWebSocketClient(
        api_key=API_KEY,
        markets=MARKETS,
        sport=SPORT,
        leagues=LEAGUES,
        status=STATUS,
        bookmakers=BOOKMAKERS,
        prefetch=args.prefetch
    )

    client.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()
        print(f"Final store: {len(client.odds_store)} events cached")
        print("Goodbye!")


if __name__ == "__main__":
    main()
