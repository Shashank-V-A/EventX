from collections.abc import Callable

from eventx.fetchers.devfolio import fetch_devfolio_hackathons
from eventx.fetchers.devpost import fetch_devpost_hackathons
from eventx.fetchers.dorahacks import fetch_dorahacks_hackathons
from eventx.fetchers.hack2skill import fetch_hack2skill_hackathons
from eventx.fetchers.hackerearth import fetch_hackerearth_hackathons
from eventx.fetchers.luma import fetch_luma_hackathons
from eventx.fetchers.mlh import fetch_mlh_hackathons
from eventx.fetchers.unstop import fetch_unstop_hackathons
from eventx.models import HackathonEvent
from eventx.storage import record_fetch_failure, record_fetch_success

Fetcher = Callable[[], list[HackathonEvent]]

# HackathonX — hackathon sources only (no meetups / concerts / workshops)
FETCHERS: list[tuple[str, Fetcher]] = [
    ("unstop", lambda: fetch_unstop_hackathons()),
    ("devfolio", fetch_devfolio_hackathons),
    ("devpost", fetch_devpost_hackathons),
    ("hackerearth", fetch_hackerearth_hackathons),
    ("hack2skill", fetch_hack2skill_hackathons),
    ("dorahacks", fetch_dorahacks_hackathons),
    ("mlh", fetch_mlh_hackathons),
    ("luma", fetch_luma_hackathons),  # only if LUMA_EVENT_URLS points at hackathons
]


def fetch_all_hackathons(
    *, max_pages: int | None = None
) -> tuple[dict[str, list[HackathonEvent]], list[str]]:
    """
    Returns (results_by_platform, failed_platforms).
    Failed platforms are recorded for health checks.
    """
    results: dict[str, list[HackathonEvent]] = {}
    failed: list[str] = []

    for name, fetcher in FETCHERS:
        try:
            if name == "unstop":
                results[name] = fetch_unstop_hackathons(max_pages=max_pages)
            else:
                results[name] = fetcher()
            record_fetch_success(name)
        except Exception as exc:
            print(f"  Warning: {name} fetch failed: {exc}")
            results[name] = []
            failed.append(name)
            record_fetch_failure(name, str(exc))

    return results, failed
