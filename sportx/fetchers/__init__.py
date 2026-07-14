from __future__ import annotations

from collections.abc import Callable

from sportx.fetchers.allevents import fetch_allevents_sports
from sportx.fetchers.eventbrite import fetch_eventbrite_sports
from sportx.fetchers.luma import fetch_luma_sports
from sportx.fetchers.meetup import fetch_meetup_sports
from sportx.models import SportEvent

Fetcher = Callable[[], list[SportEvent]]

FETCHERS: list[tuple[str, Fetcher]] = [
    ("allevents", fetch_allevents_sports),
    ("meetup", fetch_meetup_sports),
    ("luma", fetch_luma_sports),
    ("eventbrite", fetch_eventbrite_sports),
]


def collect_all() -> tuple[list[SportEvent], list[tuple[str, Exception | None]]]:
    """Return (events, results) where results is [(platform, error_or_None), ...]."""
    events: list[SportEvent] = []
    results: list[tuple[str, Exception | None]] = []
    for name, fetcher in FETCHERS:
        try:
            batch = fetcher()
            events.extend(batch)
            results.append((name, None))
        except Exception as exc:  # noqa: BLE001 — isolate per source
            results.append((name, exc))
    return events, results
