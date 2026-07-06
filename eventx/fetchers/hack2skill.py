from datetime import datetime

import httpx

from eventx.fetchers._common import USER_AGENT, parse_datetime
from eventx.models import HackathonEvent

HACK2SKILL_API = "https://hack2skill.com/api/v1/innovator/public/event/public-list"


def _date_range() -> tuple[str, str]:
    now = datetime.now()
    end = now.replace(year=now.year + 3)
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    return now.strftime(fmt)[:-3] + "Z", end.strftime(fmt)[:-3] + "Z"


def _normalize_item(item: dict) -> HackathonEvent | None:
    event_id = item.get("_id")
    event_url = item.get("eventUrl")
    if not event_id or not event_url:
        return None

    mode = (item.get("mode") or "VIRTUAL").lower()
    if mode == "virtual":
        location = "Online"
    elif mode == "hybrid":
        location = "Hybrid"
    else:
        location = "Offline"

    deadline = parse_datetime(item.get("registrationEnd") or item.get("submissionEnd"))

    return HackathonEvent(
        id=event_id,
        title=item.get("title", "Untitled"),
        platform="hack2skill",
        registration_url=f"https://hack2skill.com/event/{event_url}",
        mode=mode,
        location=location,
        deadline=deadline,
        organisation=None,
    )


def fetch_hack2skill_hackathons() -> list[HackathonEvent]:
    events: list[HackathonEvent] = []
    start, end = _date_range()
    page = 1

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        while True:
            response = client.get(
                HACK2SKILL_API,
                params={
                    "page": page,
                    "records": 50,
                    "search": "",
                    "start": start,
                    "end": end,
                },
            )
            response.raise_for_status()
            batch = response.json().get("data", [])
            if not batch:
                break

            for item in batch:
                event = _normalize_item(item)
                if event:
                    events.append(event)

            page += 1

    return events
