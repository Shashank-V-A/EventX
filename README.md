# EventX

Get Bangalore hackathon registration links delivered to your Telegram — with rich details, deadline reminders, and no duplicate spam.

**Platforms:** Unstop, Devfolio, Devpost, HackerEarth, Hack2Skill, DoraHacks, MLH (+ optional Luma URLs)

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
# Optional: watch specific public Luma events
# LUMA_EVENT_URLS=https://lu.ma/your-bangalore-event
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

## Schedule it (GitHub Actions — every 6 hours)

EventX runs automatically via [GitHub Actions](https://github.com/Shashank-V-A/EventX/actions) — no need to keep your PC on.

### One-time setup

1. **Add repository secrets** at  
   [github.com/Shashank-V-A/EventX/settings/secrets/actions](https://github.com/Shashank-V-A/EventX/settings/secrets/actions)

   | Secret name | Value |
   |-------------|-------|
   | `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
   | `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

2. **Enable workflows** — open the [Actions tab](https://github.com/Shashank-V-A/EventX/actions), click **I understand my workflows, go ahead and enable them** if prompted.

3. **Test manually** — select **EventX Alerts** → **Run workflow** → **Run workflow**.

Each hackathon is notified **only once**. Seen events are saved in `data/events.db` and committed back to the repo after every run.

## Features

- **Richer alerts** — prize pool, team size, and eligibility when platforms expose them
- **Cross-platform dedupe** — same event on Unstop + Devfolio → one Telegram message
- **Deadline reminders** — extra ping at ~48h and ~24h before registration closes
- **Health checks** — Telegram warning if a platform fails 2 runs in a row
- **MLH** — student hackathons including Bengaluru venues
- **Luma workaround** — watch specific public event URLs via `LUMA_EVENT_URLS`

## How it works

1. Fetches open hackathons from all configured sources
2. Filters for Bangalore / Bengaluru
3. Merges duplicates across platforms
4. Sends new alerts + due deadline reminders
5. Alerts you if a source keeps failing

### Platform notes

| Platform | Method | Notes |
|----------|--------|-------|
| Unstop | Public API | Best India coverage; prizes/team/eligibility |
| Devfolio | Public API | Strong city + team size fields |
| Devpost | Public API | Prize totals when listed |
| HackerEarth | HTML listing | Mostly online |
| Hack2Skill | Public API | Indian events |
| DoraHacks | Public API | Prize when listed |
| MLH | Season page JSON | Bengaluru student hacks |
| Luma | Curated URLs | No global discover API |
| LabLab.ai | — | Blocked by Cloudflare |

## Project structure

```
EventX/
├── main.py
├── eventx/
│   ├── fetchers/          # one module per platform
│   ├── dedupe.py          # cross-platform merge
│   ├── filter.py
│   ├── notifier/telegram.py
│   ├── storage.py         # seen events + reminders + health
│   └── models.py
└── data/events.db
```
