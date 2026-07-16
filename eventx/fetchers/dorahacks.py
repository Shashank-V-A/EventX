from datetime import datetime, timezone

import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT
from eventx.models import HackathonEvent

DORAHACKS_API = "https://dorahacks.io/api/hackathon/"
_MAX_PAGES = 20


def _normalize_item(item: dict) -> HackathonEvent | None:
    uname = item.get("uname")
    title = item.get("title")
    if not uname or not title:
        return None

    end_time = item.get("end_time")
    deadline = (
        datetime.fromtimestamp(end_time, tz=timezone.utc) if end_time else None
    )

    venue = item.get("venue_name")
    participation = item.get("participation_form", "")
    mode = "online" if participation == "Virtual" else "offline"
    location = venue or ("Online" if mode == "online" else None)

    amount = item.get("bonus_price")
    token = item.get("token") or "USD"
    prize_pool = f"{amount} {token}" if amount else None

    return with_category(
        HackathonEvent(
            id=uname,
            title=title,
            platform="dorahacks",
            registration_url=f"https://dorahacks.io/hackathon/{uname}/detail",
            mode=mode,
            location=location,
            deadline=deadline,
            organisation=item.get("organizer_name"),
            prize_pool=prize_pool,
            team_size=None,
            eligibility=None,
            category="hackathon",
        )
    )


def fetch_dorahacks_hackathons() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for status in ("upcoming", "ongoing"):
            url: str | None = DORAHACKS_API
            params: dict | None = {"page": 1, "page_size": 50, "status": status}
            pages = 0
            seen_urls: set[str] = set()

            while url and pages < _MAX_PAGES:
                if url in seen_urls:
                    break
                seen_urls.add(url)
                pages += 1

                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

                for item in payload.get("results", []):
                    event = _normalize_item(item)
                    if event:
                        events.append(event)

                url = payload.get("next")
                params = None

    return events
