import pytest

pd = pytest.importorskip("pandas")

from odds_api.dataframes import (  # noqa: E402
    closing_lines_to_dataframe,
    events_to_dataframe,
    odds_to_dataframe,
    outright_odds_to_dataframe,
    to_dataframe,
)

EVENT_ODDS = {
    "id": 1,
    "home": "Arsenal",
    "away": "Chelsea",
    "date": "2026-11-08T15:00:00Z",
    "status": "pending",
    "sport": {"name": "Football", "slug": "football"},
    "league": {"name": "England - Premier League", "slug": "england-premier-league"},
    "bookmakers": {
        "Bet365": [
            {
                "name": "ML",
                "updatedAt": "2026-11-06T10:00:00Z",
                "odds": [{"home": "2.10", "draw": "3.40", "away": "3.20"}],
            },
            {
                "name": "Totals",
                "updatedAt": "2026-11-06T10:00:00Z",
                "odds": [{"hdp": 2.5, "over": "1.90", "under": "1.95", "max": 500}],
            },
        ],
        "SingBet": [
            {
                "name": "ML",
                "updatedAt": "2026-11-06T10:01:00Z",
                "odds": [{"home": "2.15", "draw": "3.30", "away": "3.25"}],
            }
        ],
    },
}

OUTRIGHT_ODDS = {
    "id": 1001,
    "name": "The Masters",
    "bookmakers": {
        "Betfair Exchange": [
            {
                "name": "Winner",
                "updatedAt": "2026-11-06T10:00:00Z",
                "odds": [
                    {
                        "label": "Ben Griffin",
                        "participantId": 9,
                        "odds": "18.50",
                        "layOdds": "19.00",
                    }
                ],
            },
            {
                "name": "Make Cut",
                "updatedAt": "2026-11-06T10:00:00Z",
                "odds": [
                    {
                        "label": "Ben Griffin",
                        "participantId": 9,
                        "yes": "1.149",
                        "no": "6.667",
                    }
                ],
            },
        ]
    },
}


def test_odds_to_dataframe_one_row_per_line():
    df = odds_to_dataframe(EVENT_ODDS)
    assert len(df) == 3
    ml = df[(df.bookmaker == "Bet365") & (df.market == "ML")].iloc[0]
    assert ml["home"] == 2.10 and ml["draw"] == 3.40 and ml["home_team"] == "Arsenal"
    totals = df[df.market == "Totals"].iloc[0]
    assert totals["hdp"] == 2.5 and totals["over"] == 1.90 and totals["max"] == 500
    assert str(df["updated_at"].dtype).startswith("datetime64")


def test_closing_lines_and_dispatch():
    df = closing_lines_to_dataframe([EVENT_ODDS, EVENT_ODDS])
    assert len(df) == 6
    assert len(to_dataframe([EVENT_ODDS])) == 3


def test_events_to_dataframe():
    events = [
        {
            **EVENT_ODDS,
            "scores": {"home": 2, "away": 1, "periods": {"p1": {"home": 1, "away": 0}}},
        }
    ]
    events[0].pop("bookmakers")
    df = events_to_dataframe(events)
    assert (
        df.iloc[0]["home_score"] == 2
        and df.iloc[0]["league_slug"] == "england-premier-league"
    )
    assert len(to_dataframe(events)) == 1


def test_outright_odds_to_dataframe():
    df = outright_odds_to_dataframe(OUTRIGHT_ODDS)
    assert list(df.market) == ["Winner", "Make Cut"]
    assert df.iloc[0]["odds"] == 18.5 and df.iloc[0]["layOdds"] == 19.0
    assert df.iloc[1]["yes"] == 1.149
    assert len(to_dataframe(OUTRIGHT_ODDS)) == 2


def test_empty_inputs():
    assert to_dataframe([]).empty
    assert odds_to_dataframe([]).empty
