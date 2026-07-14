import httpx

from eventx.config import UNSTOP_MAX_PAGES
from eventx.fetchers._common import (
    USER_AGENT,
    format_team_size,
    format_unstop_eligibility,
    format_unstop_prizes,
    parse_datetime,
)
from eventx.models import HackathonEvent

UNSTOP_SEARCH_URL = "https://unstop.com/api/public/opportunity/search-result"


def _extract_location(item: dict) -> str | None:
    address = item.get("address_with_country_logo") or {}
    city = address.get("city")
    state = address.get("state")
    full_address = address.get("address")
    parts = [p for p in (city, state, full_address) if p]
    return ", ".join(parts) if parts else None


def _normalize_item(item: dict) -> HackathonEvent:
    regn = item.get("regnRequirements") or {}
    organisation = (item.get("organisation") or {}).get("name")

    return HackathonEvent(
        id=str(item["id"]),
        title=item.get("title", "Untitled"),
        platform="unstop",
        registration_url=item.get("seo_url")
        or f"https://unstop.com/{item.get('public_url', '')}",
        mode=item.get("region", "unknown"),
        location=_extract_location(item),
        deadline=parse_datetime(regn.get("end_regn_dt")),
        organisation=organisation,
        prize_pool=format_unstop_prizes(item.get("prizes")),
        team_size=format_team_size(regn.get("min_team_size"), regn.get("max_team_size")),
        eligibility=format_unstop_eligibility(regn.get("eligibility")),
    )


def fetch_unstop_hackathons(max_pages: int | None = None) -> list[HackathonEvent]:
    pages = max_pages if max_pages is not None else UNSTOP_MAX_PAGES
    events: list[HackathonEvent] = []

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for page in range(1, pages + 1):
            response = client.get(
                UNSTOP_SEARCH_URL,
                params={
                    "opportunity": "hackathons",
                    "page": page,
                    "per_page": 50,
                },
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("data", {}).get("data", [])

            if not items:
                break

            for item in items:
                if item.get("type") != "hackathons":
                    continue
                if item.get("regn_open") != 1:
                    continue
                events.append(_normalize_item(item))

            current_page = payload.get("data", {}).get("current_page", page)
            last_page = payload.get("data", {}).get("last_page", page)
            if current_page >= last_page:
                break

    return events
