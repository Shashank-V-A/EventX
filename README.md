# EventX

Get Bangalore hackathon registration links delivered to your Telegram — starting with Unstop.

## Setup

### 1. Install dependencies

```bash
cd EventX
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 3. Get your chat ID

1. Message your new bot (send anything, e.g. `hi`)
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` — that number is your chat ID

### 4. Configure environment

```bash
copy .env.example .env
```

Edit `.env`:

```
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
UNSTOP_MAX_PAGES=10
INCLUDE_ONLINE=false
```

### 5. Run

Dry run (no messages sent):

```bash
python main.py --dry-run
```

Send alerts:

```bash
python main.py
```

## Schedule it (automatic every 6 hours)

### Option A — Windows Task Scheduler (local, already set up)

Runs on your PC every 6 hours using your local `.env` and `data/events.db`.

```powershell
# Install / update the scheduled task
powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1

# Run immediately (test)
Start-ScheduledTask -TaskName "EventX Hackathon Alerts"

# View logs
type logs\eventx.log

# Remove the task
Unregister-ScheduledTask -TaskName "EventX Hackathon Alerts" -Confirm:$false
```

Your PC needs to be on (or waking) for this to run.

### Option B — GitHub Actions (cloud, 24/7)

Works even when your PC is off. Workflow file: `.github/workflows/eventx.yml`

1. Create a **private** repo on GitHub and push this project
2. Go to **Settings → Secrets and variables → Actions → New repository secret**
   - `TELEGRAM_BOT_TOKEN` — your bot token
   - `TELEGRAM_CHAT_ID` — your chat ID
3. Open **Actions** tab → enable workflows → run **EventX Alerts** manually once to test

GitHub Actions free tier allows scheduled workflows on private repos.

**Tip:** Use only one scheduler (Windows *or* GitHub), or both will share dedup only within their own environment and may send duplicate alerts.

## How it works

1. Fetches open hackathons from Unstop's public API
2. Filters for Bangalore / Bengaluru (city, address, org name, or URL)
3. Skips events you've already been notified about (SQLite)
4. Sends a Telegram message with the registration link

## Project structure

```
EventX/
├── main.py                 # Entry point
├── eventx/
│   ├── fetchers/unstop.py  # Unstop API client
│   ├── filter.py           # Bangalore location filter
│   ├── notifier/telegram.py
│   ├── storage.py          # SQLite deduplication
│   └── models.py
└── data/events.db          # Created on first run
```

## Next steps

- Add HackerEarth, Luma, LabLab AI fetchers
- Add filters for online / AI hackathons only
- Simple web dashboard to browse seen events
