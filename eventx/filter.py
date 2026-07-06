import re

from eventx.config import BANGALORE_KEYWORDS, INCLUDE_ONLINE
from eventx.models import HackathonEvent

# Highway names that mention Bengaluru but are not in Bangalore
HIGHWAY_FALSE_POSITIVES = (
    re.compile(r"bengaluru\s*[-–]\s*chennai", re.I),
    re.compile(r"bangalore\s*[-–]\s*chennai", re.I),
)

# If these appear in location, require Karnataka unless title/URL already matched
CONTRADICTORY_REGIONS = (
    "tamil nadu",
    "chennai",
    "poonamallee",
    "hyderabad",
    "telangana",
    "pune",
    "maharashtra",
    "mumbai",
    "delhi",
    "noida",
    "gurgaon",
    "gurugram",
    "kolkata",
    "west bengal",
    "kochi",
    "kerala",
    "jaipur",
    "rajasthan",
    "ahmedabad",
    "gujarat",
    "lucknow",
    "uttar pradesh",
    "bhubaneswar",
    "odisha",
    "chandigarh",
    "goa",
)


def _contains_keyword(text: str) -> bool:
    return any(keyword in text for keyword in BANGALORE_KEYWORDS)


def _strong_match(event: HackathonEvent) -> bool:
    strong_text = " ".join(
        [
            event.title or "",
            event.registration_url or "",
            event.organisation or "",
        ]
    ).lower()
    return _contains_keyword(strong_text)


def _location_match(location: str) -> bool:
    loc = location.lower()
    if not _contains_keyword(loc):
        return False

    for pattern in HIGHWAY_FALSE_POSITIVES:
        if pattern.search(loc):
            return False

    if any(region in loc for region in CONTRADICTORY_REGIONS):
        return "karnataka" in loc

    return True


def is_bangalore_match(event: HackathonEvent) -> bool:
    if _strong_match(event):
        return True

    location = event.location or ""
    if location and _location_match(location):
        return True

    if INCLUDE_ONLINE and event.mode == "online" and _contains_keyword(
        (event.title or "") + " " + (event.registration_url or "")
    ):
        return True

    return False


def filter_bangalore(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_bangalore_match(e)]
