# Odds-API.io Python SDK

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22836643.svg)](https://doi.org/10.5281/zenodo.22836643)
[![PyPI version](https://img.shields.io/pypi/v/odds-api-io.svg)](https://pypi.org/project/odds-api-io/)
[![Python versions](https://img.shields.io/pypi/pyversions/odds-api-io.svg)](https://pypi.org/project/odds-api-io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-odds--api.io-blue.svg)](https://docs.odds-api.io)

Official Python SDK for [**Odds-API.io**](https://odds-api.io), the sports betting odds API: live and pre-match odds from 450+ bookmakers across 34 sports, player props, golf outrights, closing lines, bet settlement, arbitrage, value bets and a WebSocket feed. Sync and async clients, typed responses, optional pandas helpers.

## Documentation

- [Quickstart: make your first request](https://docs.odds-api.io/quickstart)
- [Python, Node.js and R SDK guide](https://docs.odds-api.io/guides/sdks)
- [Fetching pre-match and live odds](https://docs.odds-api.io/guides/fetching-odds)
- [Stream live odds over WebSocket](https://docs.odds-api.io/guides/websockets)
- [Find value bets](https://docs.odds-api.io/guides/value-bets) and [arbitrage opportunities](https://docs.odds-api.io/guides/arbitrage-bets)
- [Historical odds and closing lines](https://docs.odds-api.io/guides/historical)
- [Full API reference](https://docs.odds-api.io/api-reference/introduction)

## Quickstart

```bash
pip install odds-api-io
```

```python
from odds_api import OddsAPIClient

with OddsAPIClient(api_key="YOUR_API_KEY") as client:
    events = client.get_events(sport="football", league="england-premier-league", status="pending")
    odds = client.get_event_odds(
        events[0]["id"],
        bookmakers=["Bet365", "SingBet"],
        markets=["ML", "Spread", "Totals"],
    )
    for bookmaker, markets in odds["bookmakers"].items():
        for market in markets:
            print(bookmaker, market["name"], market["odds"][0])
```

Market names are exact: `ML`, `Spread`, `Totals`, `Both Teams To Score`, `Spread HT` and so on. `client.get_markets("football")` lists every name a sport serves. Pass `markets` on odds calls so you only download what you use.

## Get an API key

You need an API key from a paid plan: **[get your API key at odds-api.io/pricing](https://odds-api.io/pricing?ref=pypi)**. Plans are monthly and can be cancelled anytime.

## Features

- **Odds**: pre-match and live odds per event or for 10 events per call, filtered to the markets you want, including player props
- **Odds summary**: best, average, median, worst and fair price per line across bookmakers
- **Golf outrights**: Winner, Top 5/10/20, the "(Incl. Ties)" variants and Make Cut, plus results (Outrights add-on)
- **Historical data**: past events, stored odds and closing lines for up to 10 leagues and a full season per sweep
- **Settlement**: final scores with a `final` flag, and grading of up to 50 bets per call (won, lost, void, half won, half lost)
- **Analysis**: arbitrage and value bets with sport, league, market and margin filters; dropping odds from sharp bookmakers
- **Odds movements**: pre-match price history per market line
- **Id mappings**: our events and selections mapped to Polymarket and Kalshi ids
- **WebSocket**: `odds_api.ws.OddsStream`, an async iterator that reconnects and resumes from the last sequence number
- **pandas**: `to_dataframe()` for events, odds, closing lines and outright odds (`pip install "odds-api-io[pandas]"`)
- **Errors that keep the server's message**, a `RateLimitError` with `retry_after`, and optional retries with backoff
- **Typed responses** (`TypedDict`), sync and async (aiohttp) clients, Python 3.8+

## Examples

### Closing lines and CLV

```python
from odds_api import OddsAPIClient
from odds_api.dataframes import closing_lines_to_dataframe  # pip install "odds-api-io[pandas]"

client = OddsAPIClient(api_key="YOUR_API_KEY")
rows = client.iter_closing_lines(
    sport="football",
    leagues=["england-premier-league", "spain-laliga"],
    from_="2026-08-01T00:00:00Z",
    to="2026-10-31T23:59:59Z",   # up to 366 days per request
    markets=["ML", "Totals"],
    bookmakers=["Bet365", "SingBet"],
)
df = closing_lines_to_dataframe(list(rows))
print(df[["date", "home_team", "away_team", "bookmaker", "market", "hdp", "home", "away", "over", "under"]])
```

`get_historical_events(sport, league, from_, to)` lists finished events for one league over at most 31 days, and `get_historical_odds(event_id, bookmakers, markets=...)` returns the stored odds of one of them.

### Golf outrights

```python
from odds_api import AddOnRequiredError, OddsAPIClient

client = OddsAPIClient(api_key="YOUR_API_KEY")
try:
    tournaments = client.get_outrights(sport="golf", league="majors")
except AddOnRequiredError as e:
    print(e)  # the server's message, with the link to add the Outrights add-on
else:
    odds = client.get_outright_odds(tournaments[0]["id"], ["DraftKings", "Betfair Exchange"])
    for bookmaker, markets in odds["bookmakers"].items():
        for market in markets:  # Winner, Top 5, Top 5 (Incl. Ties), ..., Make Cut
            favourite = market["odds"][0]
            print(bookmaker, market["name"], favourite["label"], favourite.get("odds") or favourite.get("yes"))

    results = client.get_outright_results(tournaments[0]["id"])
    print(results["winners"].get("Top 10"))  # participant ids, filled once settled
```

Winner and Top N runners carry `odds` (and `layOdds` on exchanges); Make Cut runners carry `yes` and `no`.

### Settle bets

```python
result = client.grade_bets([
    {"ref": "bet-1", "eventId": 74919888, "market": "Spread", "hdp": -0.75, "side": "home"},
    {"ref": "bet-2", "eventId": 74919888, "market": "Totals", "hdp": 2.5, "side": "over"},
])
for grade in result["grades"]:
    print(grade["ref"], grade["result"], grade["reason"], grade["final"])
```

`get_settlements([ids])` returns status, final score and a `final` flag for up to 50 events. Period scores use the keys `p1`..`pN`, `ft`, `ot` and `ap`; the older keys (`period1`, `overtime`, `penalties`, `fulltime`) stop on 12 November 2026.

### Arbitrage and value bets

```python
arbs = client.get_arbitrage_bets(
    ["Bet365", "SingBet"], sport="football", markets=["ML", "Totals"], min_profit=1.0,
    include_event_details=True,
)
# profitMargin is already a percentage (2.48 means 2.48%)
value = client.get_value_bets("Bet365", sport="baseball", league="usa-mlb")
# expectedValue is bookmaker odds / fair odds x 100, so 103.42 is a 3.42% edge
edges = [b for b in value if b["expectedValue"] - 100 >= 3]
drops = client.get_dropping_odds(sport="football", markets=["Spread"], time_window="24h", min_drop=10)
```

Arbitrage rows are calculated at the quoted prices. Prices move and bookmakers can void or limit bets, so check every leg before acting.

### Polling for changes

`/odds/updated` returns only what changed. Pass the `X-Next-Since` header back as `since`:

```python
import time

since = int(time.time()) - 20
while True:
    changed = client.get_updated_odds_since_timestamp(since, "Bet365", "football", markets=["ML", "Totals"])
    ...  # merge by event, bookmaker and market
    since = int(client.last_response_headers["X-Next-Since"])
    time.sleep(5)
```

### WebSocket

```python
import asyncio
from odds_api.ws import OddsStream  # pip install "odds-api-io[ws]"

async def main():
    stream = OddsStream("YOUR_API_KEY", markets=["ML", "Totals"], sport="football", status="live")
    async for message in stream:
        if message["type"] in ("created", "updated"):
            print(message["id"], message["bookie"], message["markets"])  # replace, do not merge

asyncio.run(main())
```

The stream tracks the highest `seq` in `stream.last_seq` and reconnects with `lastSeq` after a drop or a server restart. A close because a newer connection opened with the same key raises `ConnectionReplacedError` instead of fighting it.

### Async client

```python
import asyncio
from odds_api import AsyncOddsAPIClient

async def main():
    async with AsyncOddsAPIClient(api_key="YOUR_API_KEY") as client:
        nba, nfl = await asyncio.gather(
            client.get_events(sport="basketball", league="usa-nba"),
            client.get_events(sport="american-football", league="usa-nfl"),
        )

asyncio.run(main())
```

More in [`examples/`](examples/): [basic_usage.py](examples/basic_usage.py), [closing_lines.py](examples/closing_lines.py), [golf_outrights.py](examples/golf_outrights.py), [settle_bets.py](examples/settle_bets.py), [odds_stream.py](examples/odds_stream.py), [arbitrage_finder.py](examples/arbitrage_finder.py), [value_bets.py](examples/value_bets.py), [odds_tracking.py](examples/odds_tracking.py) and the notebook [fair-odds-and-closing-lines.ipynb](examples/fair-odds-and-closing-lines.ipynb).

## Errors, rate limits and retries

Every error keeps the server's own message, which often says exactly what to fix (for example which markets do have history, or which bookmakers your plan includes).

| Exception | Status | When |
|---|---|---|
| `ValidationError` (alias `BadRequestError`) | 400 | A parameter is missing or invalid |
| `InvalidAPIKeyError` | 401 | The key is missing or invalid |
| `ForbiddenError` | 403 | The plan does not include this endpoint or bookmaker |
| `AddOnRequiredError` | 403 | The key lacks an add-on such as Outrights (`.add_on == "outrights"`) |
| `NotFoundError` | 404 | The resource does not exist |
| `RateLimitExceededError` (alias `RateLimitError`) | 429 | Rate limit hit; `.retry_after` is the wait in seconds |
| `ServerError` | 5xx | Server error or temporarily busy |
| `OddsAPIError` | any | Base class; also network failures |

All carry `.status_code`, `.body`, `.headers` and `.rate_limit`. After each call, `client.last_rate_limit` holds `limit`, `remaining` and `reset`.

```python
from odds_api import OddsAPIClient, RateLimitError

client = OddsAPIClient(api_key="YOUR_API_KEY", max_retries=3)  # retries 429, 5xx and network errors
try:
    client.get_sports()
except RateLimitError as e:
    print(f"Rate limited, retry in {e.retry_after:.0f}s: {e}")
```

Retries are off by default (`max_retries=0`). With retries on, the client honours `Retry-After` and `X-RateLimit-Reset`, backs off exponentially otherwise, and raises at once when the server asks for a wait longer than `max_retry_wait` (30 seconds by default).

## Method reference

Comma-separated parameters accept a string or a list. Dates accept RFC3339 strings or `datetime` objects. The async client has the same methods as coroutines.

| Method | Endpoint |
|---|---|
| `get_sports()` | `GET /sports` |
| `get_leagues(sport, all=None)` | `GET /leagues` |
| `get_markets(sport=None)` | `GET /markets` |
| `get_bookmakers()` | `GET /bookmakers` (with `status` and `reason`) |
| `get_selected_bookmakers()`, `select_bookmakers(bookmakers)`, `clear_selected_bookmakers()` | `/bookmakers/selected` |
| `get_events(sport, league, participant_id, status, from_/start, to/end, bookmaker, limit, skip)`, `iter_events(...)` | `GET /events` |
| `get_event_by_id(event_id)` | `GET /events/{id}` |
| `get_live_events(sport=None)` | `GET /events/live` |
| `search_events(query, status=None)` | `GET /events/search` (`upcoming` or `live`) |
| `get_event_odds(event_id, bookmakers, markets, include_seq)` | `GET /odds` |
| `get_odds_for_multiple_events(event_ids, bookmakers, markets, include_seq)` | `GET /odds/multi` (10 events) |
| `get_updated_odds_since_timestamp(since, bookmaker, sport, markets, limit)` | `GET /odds/updated` (`markets` required, max 40) |
| `get_odds_movement(event_id, bookmaker, market, market_line)` | `GET /odds/movements` |
| `get_odds_summary(event_id, ...)`, `get_odds_summary_multi(event_ids, ...)` | `GET /odds/summary`, `/odds/summary/multi` |
| `get_value_bets(bookmaker, include_event_details, sport, league)` | `GET /value-bets` |
| `get_arbitrage_bets(bookmakers, limit, include_event_details, sport, league, markets, min_profit, all_combinations)` | `GET /arbitrage-bets` |
| `get_dropping_odds(sport, league, leagues, markets, time_window, sort, min_drop, limit, page, include_event_details)` | `GET /dropping-odds` |
| `get_historical_events(sport, league, from_, to)` | `GET /historical/events` (max 31 days) |
| `search_historical_events(query, sport, from_, to)` | `GET /historical/events/search` |
| `get_historical_odds(event_id, bookmakers, markets)` | `GET /historical/odds` |
| `get_closing_lines(sport, leagues, from_, to, markets, bookmakers, limit, skip)`, `iter_closing_lines(...)` | `GET /historical/closing-lines` |
| `get_settlements(event_ids)` | `GET /settlements` |
| `grade_bets(selections)` | `POST /settlements/grade` |
| `get_outrights(sport="golf", league, status)` | `GET /outrights` |
| `get_outright_odds(outright_id, bookmakers)` | `GET /outrights/odds` |
| `get_outright_results(outright_id)` | `GET /outrights/results` |
| `get_participants(sport, search)`, `get_participant_by_id(id)`, `get_participant_logo(id)` | `/participants` |
| `get_mappings(bookmaker, ...)`, `iter_mappings(bookmaker, ...)` | `GET /mappings` |

Full API documentation: [docs.odds-api.io](https://docs.odds-api.io).

## Migrating from The Odds API

| The Odds API (v4) | Odds-API.io |
|---|---|
| Sport key such as `soccer_epl` | `sport="football"` plus `league="england-premier-league"` (`get_leagues`) |
| `regions=us,uk` | `bookmakers=["DraftKings", "Bet365"]` by name (`get_bookmakers`) |
| `markets=h2h,spreads,totals` | `markets=["ML", "Spread", "Totals"]` (`get_markets`) |
| `oddsFormat=decimal` | Prices are always decimal strings |
| `/v4/sports/{sport}/odds` | `get_events(...)` then `get_odds_for_multiple_events(ids, ...)`, 10 events per call |
| `/v4/sports/{sport}/scores` | `scores` on events, or `get_settlements(ids)` |
| Historical snapshots | `get_historical_odds()` and `get_closing_lines()` |
| `x-requests-remaining` header | `client.last_rate_limit.remaining` |

## Requirements

- Python 3.8 or higher
- `requests` (sync client) and `aiohttp` (async client)
- Optional: `pandas` (`[pandas]` extra), `websockets` (`[ws]` extra), or both with `[all]`

## Links

- Website: [odds-api.io](https://odds-api.io)
- Documentation: [docs.odds-api.io](https://docs.odds-api.io)
- API key: [odds-api.io/pricing](https://odds-api.io/pricing?ref=pypi)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Issues: [github.com/odds-api-io/odds-api-python/issues](https://github.com/odds-api-io/odds-api-python/issues)
- Node.js SDK: [odds-api-io/odds-api-node](https://github.com/odds-api-io/odds-api-node). Building with AI? See the [AI and vibe coding guide](https://docs.odds-api.io/ai-vibe-coding).
- Support: hello@odds-api.io

## License

MIT. See [LICENSE](LICENSE).

## Citation

If you use this package in research or a publication, please cite it. Citation metadata is in [CITATION.cff](CITATION.cff) (GitHub renders a "Cite this repository" button from it) and Zenodo metadata is in `.zenodo.json`.

```
Outlier AS. odds-api-io: Official Python SDK for Odds-API.io (version 1.2.2). https://github.com/odds-api-io/odds-api-python
```
