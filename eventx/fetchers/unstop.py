import httpx

from eventx.category import with_category
from eventx.config import UNSTOP_MAX_PAGES, UNSTOP_TYPES
from eventx.fetchers._common import (
    USER_AGENT,
    format_team_size,
    format_unstop_eligibility,
    format_unstop_prizes,
    parse_datetime,
)
from eventx.models import HackathonEvent

UNSTOP_SEARCH_URL = "https://unstop.com/api/public/opportunity/search-result"

TYPE_TO_CATEGORY = {
    "hackathons": "hackathon",
    "competitions": "competition",
    "quizzes": "competition",
    "conferences": "conference",
    "workshops": "workshop",
}


def _extract_location(item: dict) -> str | None:
    address = item.get("address_with_country_logo") or {}
    city = address.get("city")
    state = address.get("state")
    full_address = address.get("address")
    parts = [p for p in (city, state, full_address) if p]
    return ", ".join(parts) if parts else None


def _normalize_item(item: dict, opportunity_type: str) -> HackathonEvent:
    regn = item.get("regnRequirements") or {}
    organisation = (item.get("organisation") or {}).get("name")
    category = TYPE_TO_CATEGORY.get(opportunity_type, "event")

    event = HackathonEvent(
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
        category=category,
    )
    return with_category(event, hints=opportunity_type)


def fetch_unstop_hackathons(max_pages: int | None = None) -> list[HackathonEvent]:
    """Fetch configured Unstop opportunity types (hackathons, workshops, etc.)."""
    pages = max_pages if max_pages is not None else UNSTOP_MAX_PAGES
    events: list[HackathonEvent] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for opportunity_type in UNSTOP_TYPES:
            for page in range(1, pages + 1):
                response = client.get(
                    UNSTOP_SEARCH_URL,
                    params={
                        "opportunity": opportunity_type,
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
                    item_id = str(item.get("id"))
                    if item_id in seen_ids:
                        continue
                    if item.get("regn_open") != 1:
                        continue
                    seen_ids.add(item_id)
                    events.append(_normalize_item(item, opportunity_type))

                current_page = payload.get("data", {}).get("current_page", page)
                last_page = payload.get("data", {}).get("last_page", page)
                if current_page >= last_page:
                    break

    return events
