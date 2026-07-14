# EventX

Bangalore event radar for Telegram — hackathons, workshops, meetups, seminars, marathons, concerts, competitions, and more.

**Sources:** Unstop · Devfolio · Devpost · Meetup · AllEvents · MLH · HackerEarth · Hack2Skill · DoraHacks · optional Luma URLs

## Setup

### 1. Install dependencies

```bash
cd EventX
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the bot token

### 3. Get your chat ID

1. Message your bot (`hi`)
2. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Copy `"chat":{"id": ...}`

### 4. Configure `.env`

```bash
copy .env.example .env
```

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
UNSTOP_MAX_PAGES=5
UNSTOP_TYPES=hackathons,competitions,quizzes,conferences,workshops
INCLUDE_ONLINE=false
# Optional curated Luma links:
# LUMA_EVENT_URLS=https://lu.ma/some-bangalore-event
```

### 5. Run

```bash
python main.py --dry-run
python main.py
```

## What you get

Every ~6 hours (GitHub Actions), EventX:

1. Scans tech + city event platforms
2. Keeps Bangalore / Bengaluru listings
3. Dedupes the same event across platforms
4. Sends **one** Telegram alert per new event (with type: meetup, hackathon, music, etc.)
5. Reminds you at **48h** and **24h** before the date/deadline
6. Warns you if a source fails twice in a row

## GitHub Actions

1. Add secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. Run **EventX Alerts** from the Actions tab

Seen events persist in `data/events.db` (committed after each run).

## Sources

| Source | What it usually catches |
|--------|-------------------------|
| Unstop | Hackathons, competitions, quizzes, workshops, conferences |
| Devfolio / Devpost / MLH | Hackathons & buildathons |
| Meetup | Tech talks, workshops, community meetups |
| AllEvents | City events — music, sports, festivals, local happenings |
| HackerEarth / Hack2Skill / DoraHacks | More hackathons & challenges |
| Luma | Only URLs you add in `LUMA_EVENT_URLS` |

## Project layout

```
EventX/
├── main.py
└── eventx/
    ├── fetchers/     # one module per source
    ├── category.py   # hackathon / meetup / marathon / ...
    ├── dedupe.py
    ├── filter.py
    ├── notifier/
    └── storage.py
```
