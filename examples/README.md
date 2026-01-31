# Examples

This directory contains example scripts demonstrating how to use the Odds-API.io Python SDK.

## Getting Started

Before running the examples, make sure you have:

1. Installed the SDK:
   ```bash
   pip install odds-api-io
   ```

2. Obtained an API key from [odds-api.io](https://odds-api.io/#pricing)

3. Set your API key as an environment variable:
   ```bash
   export ODDS_API_KEY="your_api_key_here"
   ```

   Or modify the examples to use your API key directly.

## Available Examples

### 1. Basic Usage (`basic_usage.py`)

Learn the fundamentals of the SDK:
- Initializing the client
- Getting sports and leagues
- Fetching events
- Searching for games
- Working with bookmakers

```bash
python basic_usage.py
```

### 2. Async Client (`async_example.py`)

Use the async client for concurrent operations:
- Async/await syntax
- Concurrent requests with `asyncio.gather`
- Async context managers

```bash
python async_example.py
```

### 3. Arbitrage Finder (`arbitrage_finder.py`)

Find arbitrage betting opportunities:
- Discovering risk-free betting opportunities
- Comparing odds across bookmakers
- Calculating potential profits

```bash
python arbitrage_finder.py
```

### 4. Value Bets (`value_bets.py`)

Identify value betting opportunities:
- Finding positive expected value bets
- Understanding implied vs true probability
- Analyzing betting edges

```bash
python value_bets.py
```

### 5. Odds Tracking (`odds_tracking.py`)

Track odds movements over time:
- Monitoring odds changes
- Historical odds data
- Batch odds fetching
- Recent updates tracking

```bash
python odds_tracking.py
```

## Tips

- **Rate Limits**: Be mindful of the API rate limits (5,000 requests/hour)
- **Error Handling**: All examples use context managers for proper resource cleanup
- **Free Tier**: Some features may be limited on the free tier (e.g., 2 bookmakers max)
- **Real Data**: These examples use real API data, so results will vary

## Need Help?

- 📚 [Full Documentation](https://docs.odds-api.io)
- 🌐 [Odds-API.io Website](https://odds-api.io)
- 🐛 [Report Issues](https://github.com/odds-api-io/odds-api-python/issues)
- 📧 [Email Support](mailto:markus@odds-api.io)
