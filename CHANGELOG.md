# Changelog

## 1.2.2

First release published from GitHub Actions with npm/PyPI trusted publishing and provenance. No code changes.

## 1.2.1 (2026-11-06)

### Fixed
- Docs: `expectedValue` on value bets is bookmaker odds / fair odds x 100, not a fraction. 103.42 is a 3.42% edge (edge % = `expectedValue - 100`). The `ValueBet` docstring, `get_value_bets` docstrings, README and `examples/value_bets.py` now say so; the example prints and filters on `expectedValue - 100`.

## 1.2.0 (2026-11-06)

Brings the SDK up to the full Odds-API.io v3 API.

### Added
- Markets catalogue: `get_markets(sport=None)`.
- Odds summary: `get_odds_summary()` and `get_odds_summary_multi()`.
- Dropping odds: `get_dropping_odds()` with `sport`, `league`, `leagues`, `markets`, `time_window`, `sort`, `min_drop`, `limit`, `page`.
- Historical data: `get_historical_events()` (`league` required, 31-day span), `search_historical_events()`, `get_historical_odds()`, `get_closing_lines()` (up to 10 leagues and 366 days) and `iter_closing_lines()`.
- Golf outrights (Outrights add-on): `get_outrights()`, `get_outright_odds()` (Winner, Top 5/10/20, the "(Incl. Ties)" variants, Make Cut) and `get_outright_results()`. `GOLF_OUTRIGHT_MARKETS` lists the market names.
- Id mappings: `get_mappings()` and `iter_mappings()` (follows `nextCursor`).
- `get_participant_logo()` returns PNG bytes.
- `iter_events()` pages through `/events` with `limit`/`skip`.
- New parameters: `get_events(limit, skip, from_, to)`, `get_live_events(sport=None)`, `search_events(status)`, `get_leagues(all)`, `get_value_bets(sport, league)`, `get_arbitrage_bets(sport, league, markets, min_profit, all_combinations)`, `markets` and `include_seq` on `get_event_odds()` and `get_odds_for_multiple_events()`, `limit` on `get_updated_odds_since_timestamp()`.
- Comma-separated parameters accept lists; date parameters accept `datetime` objects.
- Errors: `ForbiddenError` (403), `AddOnRequiredError` (403 for a missing add-on, with `.add_on`), `ServerError` (5xx), `RateLimitError` alias with `.retry_after` from `Retry-After` or `X-RateLimit-Reset`, and `BadRequestError` alias. Every error carries `.status_code`, `.body`, `.headers` and `.rate_limit`.
- Optional retries with backoff on 429, 5xx and network errors: `max_retries` (default 0, off) and `max_retry_wait`.
- `client.last_rate_limit` and `client.last_response_headers` (for `X-Next-Since`, `X-OddsAPI-Seq`, `X-Total-Count`).
- Typed responses in `odds_api.types` (`TypedDict`).
- pandas helpers in `odds_api.dataframes` (`to_dataframe`, `odds_to_dataframe`, `events_to_dataframe`, `closing_lines_to_dataframe`, `outright_odds_to_dataframe`), extra `odds-api-io[pandas]`.
- WebSocket helper `odds_api.ws.OddsStream`: async iterator with reconnect and `lastSeq` resume, extra `odds-api-io[ws]`.
- Unit tests for every method and error class.

### Changed
- Default base URL is now `https://api.odds-api.io/v3`.
- Error messages are the server's own message instead of a fixed text for 401, 404 and 429.
- `get_updated_odds_since_timestamp()` requires `markets` (max 40), as the API has since 19 October 2026.
- Docstrings use the current market names (`ML`, `Spread`, `Totals`) and event statuses (`pending`, `live`, `settled`, `cancelled`).
- Requests send a `User-Agent: odds-api-io-python/<version>` header.
- Examples updated to the current response shapes; new examples for closing lines, golf outrights and the WebSocket stream.

### Notes
- Period scores use `p1`..`pN`, `ft`, `ot` and `ap`. The older keys (`period1`, `overtime`, `penalties`, `fulltime`) stop on 12 November 2026.

## 1.1.1 (2026-11-06)
- Point to paid plans and update the bookmaker count to 450+.

## 1.1.0 (2026-10-13)
- Settlement: `get_settlements()` and `grade_bets()`.
