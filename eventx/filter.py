from eventx.config import BANGALORE_KEYWORDS, INCLUDE_ONLINE
from eventx.models import HackathonEvent


def _text_blob(event: HackathonEvent) -> str:
    parts = [
        event.title or "",
        event.location or "",
        event.organisation or "",
        event.registration_url or "",
    ]
    return " ".join(parts).lower()


def is_bangalore_match(event: HackathonEvent) -> bool:
    blob = _text_blob(event)

    if any(keyword in blob for keyword in BANGALORE_KEYWORDS):
        return True

    if event.mode == "online" and not INCLUDE_ONLINE:
        return False

    return False


def filter_bangalore(events: list[HackathonEvent]) -> list[HackathonEvent]:
    return [e for e in events if is_bangalore_match(e)]
