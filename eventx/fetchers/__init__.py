from collections.abc import Callable

from eventx.fetchers.devfolio import fetch_devfolio_hackathons
from eventx.fetchers.devpost import fetch_devpost_hackathons
from eventx.fetchers.dorahacks import fetch_dorahacks_hackathons
from eventx.fetchers.hack2skill import fetch_hack2skill_hackathons
from eventx.fetchers.hackerearth import fetch_hackerearth_hackathons
from eventx.fetchers.unstop import fetch_unstop_hackathons
from eventx.models import HackathonEvent

Fetcher = Callable[[], list[HackathonEvent]]

FETCHERS: list[tuple[str, Fetcher]] = [
    ("unstop", lambda: fetch_unstop_hackathons()),
    ("devfolio", fetch_devfolio_hackathons),
    ("devpost", fetch_devpost_hackathons),
    ("hackerearth", fetch_hackerearth_hackathons),
    ("hack2skill", fetch_hack2skill_hackathons),
    ("dorahacks", fetch_dorahacks_hackathons),
]


def fetch_all_hackathons(*, max_pages: int | None = None) -> dict[str, list[HackathonEvent]]:
    results: dict[str, list[HackathonEvent]] = {}

    for name, fetcher in FETCHERS:
        try:
            if name == "unstop":
                results[name] = fetch_unstop_hackathons(max_pages=max_pages)
            else:
                results[name] = fetcher()
        except Exception as exc:
            print(f"  Warning: {name} fetch failed: {exc}")
            results[name] = []

    return results
