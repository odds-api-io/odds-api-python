# Odds-API.io Python SDK

[![PyPI version](https://img.shields.io/pypi/v/odds-api-io.svg)](https://pypi.org/project/odds-api-io/)
[![Python versions](https://img.shields.io/pypi/pyversions/odds-api-io.svg)](https://pypi.org/project/odds-api-io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-odds--api.io-blue.svg)](https://docs.odds-api.io)

Official Python SDK for [**Odds-API.io**](https://odds-api.io) - Real-time sports betting odds from 250+ bookmakers.

## 🚀 Features

- ⚡ **Fast & Reliable** - Built on requests and aiohttp for both sync and async workflows
- 🏀 **20+ Sports** - Basketball, football, tennis, baseball, and more
- 📊 **250+ Bookmakers** - Comprehensive odds coverage from major sportsbooks worldwide
- 💰 **Arbitrage Detection** - Find risk-free betting opportunities across bookmakers
- 📈 **Value Bets** - Identify positive expected value betting opportunities
- 🔴 **Live Events** - Real-time in-play event tracking and odds
- 🔍 **Advanced Search** - Search events, participants, and leagues
- ✨ **Type Hints** - Full type annotations for better IDE support
- 🐍 **Modern Python** - Supports Python 3.8+

## 📦 Installation

```bash
pip install odds-api-io
```

## 🔑 Get Your API Key

**[Get your free API key here →](https://odds-api.io/#pricing)**

Sign up at [**odds-api.io**](https://odds-api.io) to get started. Free tier includes:
- 5,000 requests/hour
- Access to all endpoints
- No credit card required

## 📚 Documentation

Full API documentation is available at [**docs.odds-api.io**](https://docs.odds-api.io)

## 🏃 Quick Start

### Synchronous Client

```python
from odds_api import OddsAPIClient

# Initialize the client
client = OddsAPIClient(api_key="your_api_key_here")

# Get available sports
sports = client.get_sports()
print(f"Found {len(sports)} sports")

# Get upcoming NBA events
events = client.get_events(sport="basketball", league="usa-nba")

# Search for specific games
lakers_games = client.search_events(query="Lakers")

# Get live basketball events
live = client.get_live_events(sport="basketball")

# Find arbitrage opportunities
arb_bets = client.get_arbitrage_bets(
    bookmakers="singbet,bet365",
    limit=10,
    include_event_details=True
)

# Close the client when done
client.close()
```

### Asynchronous Client

```python
import asyncio
from odds_api import AsyncOddsAPIClient

async def main():
    # Use async context manager
    async with AsyncOddsAPIClient(api_key="your_api_key_here") as client:
        # Get sports
        sports = await client.get_sports()
        
        # Get upcoming events
        events = await client.get_events(sport="basketball", league="usa-nba")
        
        # Find value bets
        value_bets = await client.get_value_bets(
            bookmaker="singbet",
            include_event_details=True
        )
        
        print(f"Found {len(value_bets)} value betting opportunities")

# Run async code
asyncio.run(main())
```

### Context Manager (Recommended)

```python
# Sync
with OddsAPIClient(api_key="your_api_key") as client:
    sports = client.get_sports()

# Async
async with AsyncOddsAPIClient(api_key="your_api_key") as client:
    sports = await client.get_sports()
```

## 📖 Examples

Check out the [`examples/`](examples/) directory for more detailed examples:

- **[basic_usage.py](examples/basic_usage.py)** - Getting started with the SDK
- **[async_example.py](examples/async_example.py)** - Using the async client
- **[arbitrage_finder.py](examples/arbitrage_finder.py)** - Finding arbitrage opportunities
- **[value_bets.py](examples/value_bets.py)** - Identifying value bets
- **[odds_tracking.py](examples/odds_tracking.py)** - Tracking odds movements

## 🔧 API Reference

### Sports & Leagues

| Method | Description | Docs |
|--------|-------------|------|
| `get_sports()` | Get all available sports | [📖](https://docs.odds-api.io/api-reference/sports/get-sports) |
| `get_leagues(sport)` | Get leagues for a sport | [📖](https://docs.odds-api.io/api-reference/leagues/get-leagues) |

### Events

| Method | Description | Docs |
|--------|-------------|------|
| `get_events(sport, **filters)` | Get events with filters | [📖](https://docs.odds-api.io/api-reference/events/get-events) |
| `get_event_by_id(event_id)` | Get specific event details | [📖](https://docs.odds-api.io/api-reference/events/get-event-by-id) |
| `get_live_events(sport)` | Get currently live events | [📖](https://docs.odds-api.io/api-reference/events/get-live-events) |
| `search_events(query)` | Search events by keyword | [📖](https://docs.odds-api.io/api-reference/events/search-events) |

### Odds

| Method | Description | Docs |
|--------|-------------|------|
| `get_event_odds(event_id, bookmakers)` | Get odds for an event | [📖](https://docs.odds-api.io/api-reference/odds/get-event-odds) |
| `get_odds_movement(event_id, bookmaker, market)` | Track odds changes | [📖](https://docs.odds-api.io/api-reference/odds/get-odds-movements) |
| `get_odds_for_multiple_events(event_ids, bookmakers)` | Get odds for multiple events | [📖](https://docs.odds-api.io/api-reference/odds/get-odds-for-multiple-events) |
| `get_updated_odds_since_timestamp(since, bookmaker, sport)` | Get recently updated odds | [📖](https://docs.odds-api.io/api-reference/odds/get-updated-event-odds-since-a-given-timestamp) |

### Participants

| Method | Description | Docs |
|--------|-------------|------|
| `get_participants(sport, search=None)` | Get teams/players | [📖](https://docs.odds-api.io/api-reference/participants/get-participants) |
| `get_participant_by_id(participant_id)` | Get participant by ID | [📖](https://docs.odds-api.io/api-reference/participants/get-participant-by-id) |

### Bookmakers

| Method | Description | Docs |
|--------|-------------|------|
| `get_bookmakers()` | Get all available bookmakers | [📖](https://docs.odds-api.io/api-reference/bookmakers/get-bookmakers) |
| `get_selected_bookmakers()` | Get your selected bookmakers | [📖](https://docs.odds-api.io/api-reference/bookmakers/get-selected-bookmakers) |
| `select_bookmakers(bookmakers)` | Select bookmakers | [📖](https://docs.odds-api.io/api-reference/bookmakers/select-bookmakers) |
| `clear_selected_bookmakers()` | Clear selection | [📖](https://docs.odds-api.io/api-reference/bookmakers/clear-selected-bookmakers) |

### Betting Analysis

| Method | Description | Docs |
|--------|-------------|------|
| `get_arbitrage_bets(bookmakers, **options)` | Find arbitrage opportunities | [📖](https://docs.odds-api.io/api-reference/arbitrage-bets/get-arbitrage-betting-opportunities) |
| `get_value_bets(bookmaker, **options)` | Find value bets | [📖](https://docs.odds-api.io/api-reference/value-bets/get-value-bets) |

## ⚠️ Error Handling

The SDK provides custom exceptions for different error scenarios:

```python
from odds_api import (
    OddsAPIClient,
    OddsAPIError,
    InvalidAPIKeyError,
    RateLimitExceededError,
    NotFoundError,
    ValidationError
)

client = OddsAPIClient(api_key="your_api_key")

try:
    events = client.get_events(sport="basketball")
except InvalidAPIKeyError:
    print("Your API key is invalid")
except RateLimitExceededError:
    print("Rate limit exceeded - wait before retrying")
except NotFoundError:
    print("Resource not found")
except ValidationError as e:
    print(f"Invalid parameters: {e}")
except OddsAPIError as e:
    print(f"API error: {e}")
```

## 🌟 Why Odds-API.io?

- **✅ Most Comprehensive Coverage** - 250+ bookmakers across 20+ sports
- **✅ Near-Zero Latency** - Real-time odds updates with minimal delay
- **✅ Direct Bet Links** - Deep links directly to bookmaker bet slips
- **✅ Value Bet Detection** - Automatically calculated expected value
- **✅ Historical Data** - Access to past odds and results
- **✅ Developer Friendly** - Clean API design with excellent documentation

## 💡 Use Cases

Build powerful betting tools and analytics:
- 🎯 Arbitrage betting platforms
- 📊 Odds comparison sites
- 📈 Value betting calculators
- 🤖 Automated betting systems
- 📉 Sports analytics dashboards
- 🔔 Odds movement alerts

## 🆓 Free Tier Limitations

- Limited to 2 bookmakers selected at once
- 5,000 requests per hour (shared across all plans)
- No WebSocket access on free tier

[**Upgrade for more features →**](https://odds-api.io/#pricing)

## 📋 Requirements

- Python 3.8 or higher
- `requests` library (for sync client)
- `aiohttp` library (for async client)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Website**: [odds-api.io](https://odds-api.io)
- **Documentation**: [docs.odds-api.io](https://docs.odds-api.io)
- **API Key**: [Get your API key](https://odds-api.io/#pricing)
- **GitHub**: [github.com/odds-api-io/odds-api-python](https://github.com/odds-api-io/odds-api-python)
- **Issues**: [Report a bug](https://github.com/odds-api-io/odds-api-python/issues)
- **PyPI**: [pypi.org/project/odds-api-io](https://pypi.org/project/odds-api-io/)

## 💬 Support

Need help? We're here for you:

- 📧 **Email**: hello@odds-api.io
- 📚 **Documentation**: [docs.odds-api.io](https://docs.odds-api.io)
- 🐛 **Issues**: [GitHub Issues](https://github.com/odds-api-io/odds-api-python/issues)
- ⏱️ **Response Time**: Usually within 24 hours

## ⚡ Quick Links

- [**Get Started →**](https://odds-api.io/#pricing)
- [**View Documentation →**](https://docs.odds-api.io)
- [**See Examples →**](examples/)

---

Built with ❤️ by the [Odds-API.io](https://odds-api.io) team
