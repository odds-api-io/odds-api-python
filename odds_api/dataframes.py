"""pandas helpers. Install with ``pip install "odds-api-io[pandas]"``.

Example:
    >>> from odds_api.dataframes import to_dataframe
    >>> df = to_dataframe(client.get_event_odds(123456, ["Bet365", "SingBet"], markets=["ML"]))
"""

from typing import Any, Dict, Iterable, List, Mapping, Union

try:
    import pandas as pd
except ImportError as e:  # pragma: no cover
    raise ImportError(
        'pandas is required for odds_api.dataframes: pip install "odds-api-io[pandas]"'
    ) from e

_LINE_KEYS = ("hdp", "label")


def _as_list(
    data: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]],
) -> List[Mapping[str, Any]]:
    if isinstance(data, Mapping):
        return [data]
    return list(data)


def _number(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _name(value: Any) -> Any:
    return value.get("name") if isinstance(value, Mapping) else value


def _slug(value: Any) -> Any:
    return value.get("slug") if isinstance(value, Mapping) else None


def events_to_dataframe(events: Iterable[Mapping[str, Any]]) -> "pd.DataFrame":
    """One row per event, with the headline score. Period scores stay in ``periods``."""
    rows = []
    for event in _as_list(events):
        scores = event.get("scores") or {}
        rows.append(
            {
                "event_id": event.get("id"),
                "date": event.get("date"),
                "status": event.get("status"),
                "sport": _name(event.get("sport")),
                "league": _name(event.get("league")),
                "league_slug": _slug(event.get("league")),
                "home": event.get("home"),
                "away": event.get("away"),
                "home_id": event.get("homeId"),
                "away_id": event.get("awayId"),
                "home_score": scores.get("home"),
                "away_score": scores.get("away"),
                "periods": scores.get("periods"),
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
    return frame


def odds_to_dataframe(
    event_odds: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]],
) -> "pd.DataFrame":
    """
    Flatten ``/odds``, ``/odds/multi``, ``/historical/odds`` or closing-line
    responses: one row per event, bookmaker, market and line, with a float
    column per side (``home``, ``draw``, ``away``, ``over``, ``under``, ...).
    """
    rows: List[Dict[str, Any]] = []
    for event in _as_list(event_odds):
        base = {
            "event_id": event.get("id"),
            "date": event.get("date"),
            "status": event.get("status"),
            "sport": _name(event.get("sport")),
            "league": _name(event.get("league")),
            "home_team": event.get("home"),
            "away_team": event.get("away"),
        }
        for bookmaker, markets in (event.get("bookmakers") or {}).items():
            for market in markets or []:
                for line in market.get("odds") or []:
                    row = dict(base)
                    row.update(
                        bookmaker=bookmaker,
                        market=market.get("name"),
                        updated_at=market.get("updatedAt"),
                        hdp=line.get("hdp"),
                        label=line.get("label"),
                    )
                    for key, value in line.items():
                        if key not in _LINE_KEYS:
                            row[key] = _number(value)
                    rows.append(row)
    frame = pd.DataFrame(rows)
    for column in ("date", "updated_at"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
    return frame


closing_lines_to_dataframe = odds_to_dataframe


def outright_odds_to_dataframe(outright_odds: Mapping[str, Any]) -> "pd.DataFrame":
    """One row per bookmaker, market and golfer from ``/outrights/odds``."""
    rows: List[Dict[str, Any]] = []
    for bookmaker, markets in (outright_odds.get("bookmakers") or {}).items():
        for market in markets or []:
            for runner in market.get("odds") or []:
                row: Dict[str, Any] = {
                    "outright_id": outright_odds.get("id"),
                    "tournament": outright_odds.get("name"),
                    "bookmaker": bookmaker,
                    "market": market.get("name"),
                    "updated_at": market.get("updatedAt"),
                    "label": runner.get("label"),
                    "participant_id": runner.get("participantId"),
                }
                for key in ("odds", "layOdds", "yes", "no", "layYes", "layNo"):
                    if key in runner:
                        row[key] = _number(runner[key])
                rows.append(row)
    frame = pd.DataFrame(rows)
    if "updated_at" in frame:
        frame["updated_at"] = pd.to_datetime(
            frame["updated_at"], utc=True, errors="coerce"
        )
    return frame


def to_dataframe(data: Any) -> "pd.DataFrame":
    """
    Turn an events, odds, closing-lines or outright-odds response into a DataFrame.

    Responses with ``bookmakers`` are flattened with :func:`odds_to_dataframe`
    (or :func:`outright_odds_to_dataframe` for golf outrights); event lists
    use :func:`events_to_dataframe`; anything else goes to ``pd.DataFrame``.
    """
    items = _as_list(data)
    if not items:
        return pd.DataFrame()
    first = items[0]
    if isinstance(first, Mapping) and "bookmakers" in first:
        if isinstance(data, Mapping) and _looks_like_outright(data):
            return outright_odds_to_dataframe(data)
        return odds_to_dataframe(items)
    if isinstance(first, Mapping) and "home" in first and "away" in first:
        return events_to_dataframe(items)
    return pd.DataFrame(items)


def _looks_like_outright(data: Mapping[str, Any]) -> bool:
    for markets in (data.get("bookmakers") or {}).values():
        for market in markets or []:
            for runner in market.get("odds") or []:
                return "participantId" in runner and "home" not in runner
    return "home" not in data
