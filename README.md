# HackathonX (EventX)

Bangalore **hackathon** alerts on Telegram — software, hardware, buildathons, ideathons, video hacks, game jams, and similar.

Other event types (meetups, concerts, workshops) belong in separate bots.

**Sources:** Unstop · Devfolio · Devpost · MLH · HackerEarth · Hack2Skill · DoraHacks · optional Luma URLs

## Setup

```bash
cd EventX
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Configure `.env`:

```
TELEGRAM_BOT_TOKEN=...   # HackathonX bot token
TELEGRAM_CHAT_ID=...
UNSTOP_MAX_PAGES=10
UNSTOP_TYPES=hackathons
INCLUDE_ONLINE=false
```

Run:

```bash
python main.py --dry-run
python main.py
```

## What you get

Every ~6 hours via GitHub Actions:

1. Scans hackathon platforms
2. Keeps Bangalore / Bengaluru listings
3. Keeps only hackathon-style events (buildathon, ideathon, hardware, etc.)
4. Dedupes across platforms → **one** Telegram message
5. Reminds at **48h** / **24h** before registration closes
6. Health warning if a source fails twice in a row

Alerts are branded **HackathonX** and include subtype when detected (e.g. Buildathon, Hardware Hackathon).

## GitHub Actions

Add secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then run **EventX Alerts**.

## Sources

| Source | Role |
|--------|------|
| Unstop | India hackathons |
| Devfolio / Devpost / MLH | Campus & sponsored hacks |
| HackerEarth / Hack2Skill / DoraHacks | More challenges |
| Luma | Optional curated URLs only (`LUMA_EVENT_URLS`) |
