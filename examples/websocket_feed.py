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

    # Override config via environment variables
    ODDS_API_KEY=abc123 python websocket_feed.py --prefetch

Requirements:
    pip install websocket-client odds-api-io
"""

import os
import websocket
import json
import time
import threading
import argparse
from datetime import datetime, timezone
from urllib.parse import urlencode
from odds_api import OddsAPIClient

# ─── Configuration ────────────────────────────────────────────────────
# Set your API key via environment variable or replace the fallback below.
# Keep your key out of version control (use a .env file or export it).
API_KEY = os.environ.get("ODDS_API_KEY", "your_api_key_here")

# WebSocket filters
MARKETS = "ML,Spread,Totals"       # Required (max 20, comma-separated)
SPORT = "football"                  # Optional (max 10, comma-separated)
LEAGUES = "england-premier-league"  # Optional (max 20, comma-separated)
STATUS = "prematch"                 # "live" or "prematch" (optional)
BOOKMAKERS = "Bet365,SingBet"       # Bookmakers for initial fetch

# WebSocket endpoint
WS_URL = "wss://api.odds-api.io/v3/ws"

# Batch size for multi-event odds fetch (max event IDs per request)
PREFETCH_BATCH_SIZE = 10
# ─────────────────────────────────────────────────────────────────────


def _timestamp():
    """Return a human-readable UTC timestamp for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


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
        self._reconnect_timer = None

        # In-memory odds store: {event_id: {bookmaker: [markets]}}
        self.odds_store = {}

    # WebSocket uses "prematch"/"live", REST API uses "pending"/"live"
    WS_TO_REST_STATUS = {
        "prematch": "pending",
        "live": "live",
    }

    def initial_fetch(self):
        """
        Pre-fetch all current odds via REST API using batched
        multi-event requests. Populates self.odds_store with a
        complete snapshot.
        """
        print("=" * 60)
        print("INITIAL FETCH: Loading current odds via REST API...")
        print("=" * 60)

        client = OddsAPIClient(api_key=self.api_key)

        try:
            # Map WebSocket status to REST API status
            rest_status = self.WS_TO_REST_STATUS.get(
                self.status, self.status
            ) if self.status else None

            # Get events for the configured sport/league
            events = client.get_events(
                sport=self.sport or "football",
                league=self.leagues or None,
                status=rest_status
            )

            event_ids = [str(e['id']) for e in events]
            # Build a lookup for readable names
            event_names = {
                str(e['id']): f"{e.get('home', '?')} vs {e.get('away', '?')}"
                for e in events
            }

            print(f"Found {len(events)} events. "
                  f"Fetching odds in batches of {PREFETCH_BATCH_SIZE}...\n")

            # Fetch odds in batches using the multi-event endpoint
            for i in range(0, len(event_ids), PREFETCH_BATCH_SIZE):
                batch = event_ids[i:i + PREFETCH_BATCH_SIZE]
                try:
                    results = client.get_odds_for_multiple_events(
                        event_ids=",".join(batch),
                        bookmakers=self.bookmakers,
                    )

                    for item in results:
                        eid = str(item.get('id', ''))
                        bookmakers = item.get('bookmakers', {})
                        if bookmakers:
                            # Normalise: ensure value is always
                            # {bookie: [market, ...]}
                            store_entry = {}
                            for bookie, markets in bookmakers.items():
                                store_entry[bookie] = (
                                    markets if isinstance(markets, list)
                                    else []
                                )
                            self.odds_store[eid] = store_entry

                            # Print summary
                            name = event_names.get(eid, eid)
                            for bookie, mkts in store_entry.items():
                                ml = next(
                                    (m for m in mkts if m.get('name') == 'ML'),
                                    None,
                                )
                                if ml and ml.get('odds'):
                                    o = ml['odds'][0]
                                    print(
                                        f"  {name} [{bookie}]: "
                                        f"H {o.get('home', '-')} | "
                                        f"D {o.get('draw', '-')} | "
                                        f"A {o.get('away', '-')}"
                                    )

                except Exception as e:
                    print(f"  Batch {i // PREFETCH_BATCH_SIZE + 1} failed: {e}")

            print(f"\nInitial fetch complete: "
                  f"{len(self.odds_store)} events loaded")
            print("=" * 60)
            print()

        finally:
            client.close()

    def build_url(self):
        """Build WebSocket URL with properly encoded query parameters."""
        params = {"apiKey": self.api_key, "markets": self.markets}
        if self.sport:
            params["sport"] = self.sport
        if self.leagues:
            params["leagues"] = self.leagues
        if self.status:
            params["status"] = self.status
        return f"{WS_URL}?{urlencode(params)}"

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
                print(f"[{_timestamp()}] JSON parse error: {e}")

    def _handle_parsed(self, data):
        """Process a single parsed message."""
        try:
            msg_type = data.get('type')
            ts = _timestamp()

            if msg_type == 'welcome':
                print(f"[{ts}] Connected to Odds-API WebSocket")
                print(f"  Bookmakers: {data.get('bookmakers', [])}")
                print(f"  Sports: {data.get('sport_filter', [])}")
                print(f"  Leagues: {data.get('leagues_filter', [])}")
                print(f"  Status: {data.get('status_filter', 'all')}")
                if data.get('warning'):
                    print(f"  Warning: {data['warning']}")
                print("\nListening for real-time updates...\n")

            elif msg_type in ('created', 'updated'):
                event_id = str(data.get('id', '?'))
                bookie = data.get('bookie', '?')
                label = "NEW" if msg_type == 'created' else "UPDATE"

                # Update local store (always list of markets)
                if event_id not in self.odds_store:
                    self.odds_store[event_id] = {}
                self.odds_store[event_id][bookie] = data.get('markets', [])

                # Print update
                print(f"[{ts}] [{label}] Event {event_id} | {bookie}")
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
                event_id = str(data.get('id', '?'))
                bookie = data.get('bookie', '?')
                print(f"[{ts}] [DELETED] Event {event_id} | {bookie}\n")
                # Remove from store
                if event_id in self.odds_store:
                    self.odds_store[event_id].pop(bookie, None)

            elif msg_type == 'no_markets':
                print(f"[{ts}] [NO MARKETS] Event {data.get('id', '?')}\n")

        except Exception as e:
            print(f"[{_timestamp()}] Error handling message: {e}")

    def on_error(self, ws, error):
        print(f"[{_timestamp()}] WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"[{_timestamp()}] Disconnected (code: {close_status_code})")
        if self.should_reconnect:
            self.reconnect_attempts += 1
            if self.reconnect_attempts > self.max_reconnect_attempts:
                print(f"Max reconnect attempts "
                      f"({self.max_reconnect_attempts}) reached. Giving up.")
                return
            # Exponential backoff: 1s, 2s, 4s, 8s... capped at 30s
            delay = min(2 ** (self.reconnect_attempts - 1), 30)
            print(f"Reconnecting in {delay}s "
                  f"(attempt {self.reconnect_attempts}"
                  f"/{self.max_reconnect_attempts})...")
            # Schedule reconnect on a separate timer thread so we don't
            # block the WebSocket callback thread.
            self._reconnect_timer = threading.Timer(delay, self._start_ws)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()

    def on_open(self, ws):
        print(f"[{_timestamp()}] WebSocket connection opened")
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
        # ping_interval keeps the connection alive and detects dead
        # connections
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

        print(f"[{_timestamp()}] Connecting to WebSocket "
              f"for real-time updates...")
        self._start_ws()

    def stop(self):
        """Stop the client."""
        self.should_reconnect = False
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
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

    if API_KEY == "your_api_key_here":
        print("ERROR: Set your API key via the ODDS_API_KEY environment "
              "variable or edit API_KEY in this script.")
        raise SystemExit(1)

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
