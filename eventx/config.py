import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "events.db"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
UNSTOP_MAX_PAGES = int(os.getenv("UNSTOP_MAX_PAGES", "10"))

# HackathonX: Unstop hackathons only (no workshops/conferences/quizzes)
_DEFAULT_UNSTOP_TYPES = "hackathons"
UNSTOP_TYPES = [
    part.strip()
    for part in os.getenv("UNSTOP_TYPES", _DEFAULT_UNSTOP_TYPES).split(",")
    if part.strip()
]

BANGALORE_KEYWORDS = ("bangalore", "bengaluru", "blr")

# Required signals that something is a hackathon-style event
HACKATHON_KEYWORDS = (
    "hackathon",
    "buildathon",
    "ideathon",
    "codeathon",
    "hackfest",
    "makeathon",
    "datathon",
    "designathon",
    "game jam",
    "gamejam",
    "video hack",
    "hardware hack",
    "software hack",
    "mlh",
)
