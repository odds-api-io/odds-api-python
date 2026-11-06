"""Typed shapes of the main API responses.

These are ``TypedDict`` classes: responses stay plain dicts at runtime, the
types only help your editor and type checker. Every key is optional
(``total=False``) because the API leaves out fields it has no value for.
Prices are decimal odds sent as strings, for example ``"2.10"``.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

EventStatus = Literal["pending", "live", "settled", "cancelled"]
"""Event status. ``/events`` accepts one or a comma-separated list."""

SettlementStatus = Literal["pending", "live", "awaiting_result", "settled", "cancelled"]
GradeResult = Literal[
    "won", "lost", "void", "half_won", "half_lost", "pending", "ungradeable"
]
BookmakerStatus = Literal["ok", "degraded", "down"]
OutrightMarketName = Literal[
    "Winner",
    "Top 5",
    "Top 5 (Incl. Ties)",
    "Top 10",
    "Top 10 (Incl. Ties)",
    "Top 20",
    "Top 20 (Incl. Ties)",
    "Make Cut",
]


class NamedSlug(TypedDict, total=False):
    name: str
    slug: str


class Sport(NamedSlug):
    pass


class League(TypedDict, total=False):
    name: str
    slug: str
    eventsCount: int


class Bookmaker(TypedDict, total=False):
    name: str
    active: bool
    createdAt: str
    status: BookmakerStatus
    reason: Optional[Literal["maintenance", "unavailable"]]


class MarketInfo(TypedDict, total=False):
    """One market from ``/markets``. Pass ``name`` to the ``markets`` filter."""

    name: str
    shape: Literal["moneyline", "line", "outcomes", "yesno", "labelled"]
    period: str
    prematch: bool
    live: bool


class MarketsResponse(TypedDict, total=False):
    sport: Sport
    markets: List[MarketInfo]


class PeriodScore(TypedDict, total=False):
    home: int
    away: int
    wickets: Dict[str, int]
    overs: Dict[str, float]


class Scores(TypedDict, total=False):
    """Headline score plus ``periods``.

    Period keys: ``p1``..``pN`` (that period only), ``ft`` (end of regulation),
    ``ot`` (after overtime), ``ap`` (after a penalty shootout), plus
    ``currentgame``, ``mapN``/``mapN_score`` and ``inningN`` where they apply.
    The older keys ``period1``, ``overtime``, ``penalties`` and ``fulltime``
    stop on 12 November 2026; do not read them.
    """

    home: int
    away: int
    periods: Dict[str, PeriodScore]


class Clock(TypedDict, total=False):
    minute: int
    playedSeconds: int
    period: int
    running: bool
    statusDetail: str
    serve: str
    injuryTime: int
    periodStartedAt: int


class Event(TypedDict, total=False):
    id: int
    home: str
    away: str
    homeId: int
    awayId: int
    date: str
    status: EventStatus
    sport: Sport
    league: NamedSlug
    scores: Scores
    clock: Clock
    esports: Dict[str, Any]
    bookmakerIds: Dict[str, str]


class MarketOdds(TypedDict, total=False):
    """One market from a bookmaker, for example ``ML``, ``Spread`` or ``Totals``.

    Each entry in ``odds`` is one line: ``hdp`` for lines, ``label`` for
    player props and labelled markets, then prices keyed by side (``home``,
    ``draw``, ``away``, ``over``, ``under``, ``yes``, ``no``, ...) and an
    optional stake limit ``max``.
    """

    name: str
    updatedAt: str
    odds: List[Dict[str, Any]]


class EventOdds(Event, total=False):
    urls: Dict[str, str]
    bookmakers: Dict[str, List[MarketOdds]]


class OddsMovementPoint(TypedDict, total=False):
    home: float
    draw: float
    away: float
    hdp: float
    max: float
    timestamp: int


class OddsMovements(TypedDict, total=False):
    eventid: str
    bookmaker: str
    opening: OddsMovementPoint
    latest: OddsMovementPoint
    movements: List[OddsMovementPoint]


class SummaryOutcome(TypedDict, total=False):
    best: float
    bestBookmakers: List[str]
    average: float
    median: float
    worst: float
    fair: float
    excluded: int


class SummaryLine(TypedDict, total=False):
    hdp: float
    main: bool
    books: int
    fairBooks: int
    payout: Dict[str, float]
    outcomes: Dict[str, SummaryOutcome]
    exchanges: Dict[str, Dict[str, Any]]


class SummaryMarket(TypedDict, total=False):
    name: str
    lines: List[SummaryLine]


class OddsSummary(TypedDict, total=False):
    eventId: str
    home: str
    away: str
    date: str
    status: str
    computedAt: str
    demo: bool
    message: str
    markets: List[SummaryMarket]


class ValueBet(TypedDict, total=False):
    id: str
    eventId: int
    bookmaker: str
    market: Dict[str, Any]
    betSide: str
    expectedValue: float
    expectedValueUpdatedAt: str
    firstSeenAt: str
    bookmakerOddsUpdatedAt: str
    bookmakerOdds: Dict[str, Any]
    event: Dict[str, Any]


class ArbitrageLeg(TypedDict, total=False):
    side: str
    bookmaker: str
    odds: str
    netOdds: str
    maxStake: float
    oddsUpdatedAt: str
    href: str


class OptimalStake(TypedDict, total=False):
    side: str
    bookmaker: str
    stake: float
    potentialReturn: float


class ArbitrageBet(TypedDict, total=False):
    """A price gap across bookmakers. ``profitMargin`` is a percentage at the quoted prices."""

    id: str
    eventId: int
    market: Dict[str, Any]
    profitMargin: float
    impliedProbability: float
    totalStake: float
    legs: List[ArbitrageLeg]
    optimalStakes: List[OptimalStake]
    updatedAt: str
    firstSeenAt: str
    event: Dict[str, Any]


DropValues = TypedDict(
    "DropValues",
    {
        "sinceOpening": float,
        "12h": Optional[float],
        "24h": Optional[float],
        "48h": Optional[float],
    },
    total=False,
)


class DroppingOddsPrices(TypedDict, total=False):
    opening: float
    current: float
    drop: DropValues


class DroppingOdds(TypedDict, total=False):
    eventId: int
    event: Dict[str, Any]
    market: Dict[str, Any]
    betSide: str
    odds: DroppingOddsPrices
    lastMovedAt: int
    updatedAt: int


class Participant(TypedDict, total=False):
    id: int
    name: str
    sport: str
    game: str
    shortCode: str


class Mapping(TypedDict, total=False):
    eventId: int
    home: str
    away: str
    date: str
    sport: NamedSlug
    league: NamedSlug
    bookmaker: str
    market: str
    hdp: float
    side: str
    label: str
    nativeEventId: str
    marketId: str
    outcomeId: str
    outcomeLabel: str
    extra: Dict[str, Any]
    active: bool
    firstSeenAt: str
    lastCheckedAt: str


class MappingsPage(TypedDict, total=False):
    data: List[Mapping]
    nextCursor: Optional[str]


class Settlement(TypedDict, total=False):
    eventId: int
    sport: str
    status: SettlementStatus
    final: bool
    settledAt: str
    scores: Scores


class SettlementsResponse(TypedDict, total=False):
    settlements: List[Settlement]
    notFound: List[str]


class GradeSelection(TypedDict, total=False):
    """One bet to grade. ``eventId``, ``market`` and ``side`` (or ``label``) are needed."""

    ref: str
    eventId: Union[int, str]
    market: str
    side: str
    hdp: float
    label: str
    tieRule: Literal["lose", "void"]


class GradeBasis(TypedDict, total=False):
    scope: str
    home: int
    away: int


class Grade(TypedDict, total=False):
    ref: str
    eventId: int
    result: GradeResult
    reason: Optional[str]
    final: bool
    basis: GradeBasis


class GradesResponse(TypedDict, total=False):
    grades: List[Grade]


class Outright(TypedDict, total=False):
    """A tournament from ``/outrights`` (golf today)."""

    id: int
    name: str
    date: str
    status: EventStatus
    sport: Sport
    league: NamedSlug
    bookmakerCount: int


class OutrightRunner(TypedDict, total=False):
    """A golfer's price. Winner and Top N use ``odds``/``layOdds``; Make Cut uses ``yes``/``no``."""

    label: str
    participantId: int
    odds: str
    layOdds: str
    yes: str
    no: str
    layYes: str
    layNo: str


class OutrightMarket(TypedDict, total=False):
    name: Union[OutrightMarketName, str]
    updatedAt: str
    odds: List[OutrightRunner]


class OutrightOdds(Outright, total=False):
    bookmakers: Dict[str, List[OutrightMarket]]


class OutrightResultRow(TypedDict, total=False):
    label: str
    participantId: int
    position: Optional[int]
    tied: bool
    madeCut: Optional[bool]
    status: Literal["finished", "cut", "withdrawn", "disqualified"]


class OutrightResults(TypedDict, total=False):
    id: int
    name: str
    status: EventStatus
    results: List[OutrightResultRow]
    winners: Dict[str, List[int]]
