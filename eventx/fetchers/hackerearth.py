import re

import httpx

from eventx.fetchers._common import USER_AGENT
from eventx.models import HackathonEvent

HACKEREARTH_LIST_URL = "https://www.hackerearth.com/challenges/hackathon/"
CARD_PATTERN = re.compile(
    r'href="https://www\.hackerearth\.com/challenges/hackathon/(?P<slug>[a-z0-9-]+)/"[^>]*>.*?'
    r'<span class="challenge-list-title challenge-card-wrapper">(?P<title>[^<]+)</span>',
    re.S,
)


def fetch_hackerearth_hackathons() -> list[HackathonEvent]:
    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(HACKEREARTH_LIST_URL)
        response.raise_for_status()
        html = response.text

    events: list[HackathonEvent] = []
    seen_slugs: set[str] = set()

    for match in CARD_PATTERN.finditer(html):
        slug = match.group("slug")
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        title = match.group("title").strip()
        events.append(
            HackathonEvent(
                id=slug,
                title=title,
                platform="hackerearth",
                registration_url=f"https://www.hackerearth.com/challenges/hackathon/{slug}/",
                mode="online",
                location="Online",
                deadline=None,
                organisation="HackerEarth",
            )
        )

    return events
