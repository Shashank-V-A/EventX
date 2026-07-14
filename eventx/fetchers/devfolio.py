import httpx

from eventx.category import with_category
from eventx.fetchers._common import USER_AGENT, format_team_size, parse_datetime
from eventx.models import HackathonEvent

DEVFOLIO_API = "https://api.devfolio.co/api/hackathons"


def _normalize_item(item: dict) -> HackathonEvent | None:
    slug = item.get("slug")
    if not slug:
        return None

    location = item.get("location") or ("Online" if item.get("is_online") else None)
    mode = "online" if item.get("is_online") else "offline"

    return with_category(
        HackathonEvent(
            id=slug,
            title=item.get("name", "Untitled"),
            platform="devfolio",
            registration_url=f"https://{slug}.devfolio.co/application",
            mode=mode,
            location=location,
            deadline=parse_datetime(item.get("ends_at") or item.get("reg_ends_at")),
            organisation=item.get("organizer_name"),
            team_size=format_team_size(item.get("team_min"), item.get("team_size")),
            eligibility="Open to all" if item.get("is_online") is not None else None,
            category="hackathon",
        )
    )


def fetch_devfolio_hackathons() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []
    page = 1

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        while True:
            response = client.get(
                DEVFOLIO_API,
                params={"filter": "application_open", "page": page},
            )
            response.raise_for_status()
            batch = response.json().get("result", [])
            if not batch:
                break

            for item in batch:
                event = _normalize_item(item)
                if event:
                    events.append(event)

            page += 1

    return events
