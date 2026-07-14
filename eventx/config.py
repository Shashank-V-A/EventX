import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "events.db"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
UNSTOP_MAX_PAGES = int(os.getenv("UNSTOP_MAX_PAGES", "5"))
INCLUDE_ONLINE = os.getenv("INCLUDE_ONLINE", "false").lower() in ("1", "true", "yes")

# Comma-separated Unstop opportunity types
_DEFAULT_UNSTOP_TYPES = "hackathons,competitions,quizzes,conferences,workshops"
UNSTOP_TYPES = [
    part.strip()
    for part in os.getenv("UNSTOP_TYPES", _DEFAULT_UNSTOP_TYPES).split(",")
    if part.strip()
]

BANGALORE_KEYWORDS = ("bangalore", "bengaluru", "blr")
