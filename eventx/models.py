from dataclasses import dataclass
from datetime import datetime


@dataclass
class HackathonEvent:
    id: str
    title: str
    platform: str
    registration_url: str
    mode: str
    location: str | None
    deadline: datetime | None
    organisation: str | None

    @property
    def dedupe_key(self) -> str:
        return f"{self.platform}:{self.id}"
