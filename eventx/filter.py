import re

from eventx.config import BANGALORE_KEYWORDS, HACKATHON_KEYWORDS, INCLUDE_ONLINE
from eventx.models import HackathonEvent

# Highway names that mention Bengaluru but are not in Bangalore
HIGHWAY_FALSE_POSITIVES = (
    re.compile(r"bengaluru\s*[-–]\s*chennai", re.I),
    re.compile(r"bangalore\s*[-–]\s*chennai", re.I),
)

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

# Platforms whose listings are already hackathon feeds
_HACKATHON_NATIVE_PLATFORMS = frozenset(
    {
        "unstop",
        "devfolio",
        "devpost",
        "hackerearth",
        "hack2skill",
        "dorahacks",
        "mlh",
    }
)

_NON_HACKATHON_BLOCKERS = (
    "workshop series",
    "masterclass",
    "concert",
    "standup",
    "comedy show",
    "music festival",
    "meetup group",
)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _strong_match(event: HackathonEvent) -> bool:
    strong_text = " ".join(
        [
            event.title or "",
            event.registration_url or "",
            event.organisation or "",
        ]
    ).lower()
    return _contains_keyword(strong_text, BANGALORE_KEYWORDS)


def _location_match(location: str) -> bool:
    loc = location.lower()
    if not _contains_keyword(loc, BANGALORE_KEYWORDS):
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
        (event.title or "") + " " + (event.registration_url or ""),
        BANGALORE_KEYWORDS,
    ):
        return True

    return False


def is_hackathon_match(event: HackathonEvent) -> bool:
    """HackathonX: only software/hardware/buildathon/ideathon/etc. style events."""
    title_blob = " ".join(
        [
            event.title or "",
            event.registration_url or "",
        ]
    ).lower()

    if any(blocker in title_blob for blocker in _NON_HACKATHON_BLOCKERS):
        return False

    # Luma city feeds mix meetups/talks/hackathons — require title/url keywords only
    if event.platform == "luma":
        return _contains_keyword(title_blob, HACKATHON_KEYWORDS)

    # Ignore generic inferred category "hackathon" (not a real signal)
    category = (event.category or "").lower()
    if category == "hackathon":
        category = ""

    blob = " ".join(
        [
            title_blob,
            category,
            event.platform or "",
        ]
    ).lower()

    if _contains_keyword(blob, HACKATHON_KEYWORDS):
        return True

    # Native hackathon feeds (Unstop /hackathons, Devfolio, MLH, …)
    if event.platform in _HACKATHON_NATIVE_PLATFORMS:
        return True

    return False


def filter_bangalore(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_bangalore_match(e)]


def filter_hackathons(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_hackathon_match(e)]
