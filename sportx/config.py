import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
# Separate from HackathonX data/events.db
DB_PATH = DATA_DIR / "sportx_events.db"

# Prefer SportX-specific secrets so HackathonX's TELEGRAM_BOT_TOKEN is not reused
TELEGRAM_BOT_TOKEN = os.getenv("SPORTX_TELEGRAM_BOT_TOKEN") or os.getenv(
    "TELEGRAM_BOT_TOKEN", ""
)
TELEGRAM_CHAT_ID = os.getenv("SPORTX_TELEGRAM_CHAT_ID") or os.getenv(
    "TELEGRAM_CHAT_ID", ""
)

BANGALORE_KEYWORDS = ("bangalore", "bengaluru", "blr")

# Sport / activity signals for filtering broad listings
SPORT_KEYWORDS = (
    "marathon",
    "half marathon",
    "10k",
    "5k",
    "fun run",
    "running",
    "trail run",
    "cycling",
    "bike ride",
    "cricket",
    "pickleball",
    "badminton",
    "tennis",
    "table tennis",
    "tt ",
    "football",
    "soccer",
    "basketball",
    "volleyball",
    "swimming",
    "triathlon",
    "yoga",
    "fitness",
    "gym",
    "padel",
    "squash",
    "hockey",
    "kabaddi",
    "athletics",
    "sports",
    "tournament",
    "league match",
    "open play",
    "racquet",
    "skating",
    "climbing",
    "boxing",
    "mma",
    "golf",
)

# Prefer not alerting on travel / entertainment even if on a sports page
NON_SPORT_BLOCKERS = (
    "concert",
    "music festival",
    "standup",
    "comedy",
    "hackathon",
    "workshop series",
    "backpacking",
    "trekking tour",
    "weekend tour",
    "trip to",
    "trip by",
    "sightseeing",
    "getaway",
    "resort stay",
    "pole dance",
    "boardgame",
    "board game",
    "boardgaming",
)
