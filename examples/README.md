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

### 6. Fair odds and closing lines (`fair-odds-and-closing-lines.ipynb`)

A Jupyter notebook, viewable without running anything at
[nbviewer.org/github/odds-api-io/odds-api-python/blob/main/examples/fair-odds-and-closing-lines.ipynb](https://nbviewer.org/github/odds-api-io/odds-api-python/blob/main/examples/fair-odds-and-closing-lines.ipynb):
- Devigging with the multiplicative and power methods
- Bookmaker margin per fixture on moneyline and spread markets, from a real `/odds/multi` snapshot of six bookmakers
- Expected value of every soft-book price against the sharp consensus fair line
- Closing lines for a week of settled Premier League matches from `/historical/closing-lines`
- Closing line value and a line-movement chart from `/odds/movements`

It runs with plain `requests`, `pandas` and `matplotlib` (no SDK needed). With `ODDS_API_KEY` set it fetches live data; without a key it uses the frozen snapshot in `data/snapshot-2026-09-19.json`, so every cell runs offline.

```bash
pip install jupyter requests pandas matplotlib
jupyter notebook fair-odds-and-closing-lines.ipynb
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
- 📧 [Email Support](mailto:hello@odds-api.io)
