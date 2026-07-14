from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SportEvent:
    id: str
    title: str
    platform: str
    registration_url: str
    mode: str
    location: str | None
    deadline: datetime | None
    organisation: str | None
    category: str = "sports"
    platforms: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.platforms:
            self.platforms = [self.platform]

    @property
    def dedupe_key(self) -> str:
        return f"{self.platform}:{self.id}"

    @property
    def fingerprint(self) -> str:
        from sportx.dedupe import event_fingerprint

        return event_fingerprint(self)
