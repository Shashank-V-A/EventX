# EventX

**EventX** is a pair of Bangalore-focused Telegram alert bots that watch public event platforms and message subscribers when something new shows up — so people don’t miss deadlines by refreshing Unstop / Devfolio / Meetup all day.

| Bot | Telegram | What it alerts |
|-----|----------|----------------|
| **HackathonX** | [@EventXva05Bot](https://t.me/EventXva05Bot) | Hackathons, buildathons, ideathons, game jams |
| **SportX** | [@Sportx_va_bot](https://t.me/Sportx_va_bot) | Marathons, cricket, pickleball, badminton, football, and more |

Anyone can join with `/start`. `/stop` unsubscribes. `/help` explains the bot.

---

## Users (live)

Subscriber lists live in **Vercel Blob** (shared by the webhook app and GitHub Actions). Counts as of **27 Jul 2026**:

| Bot | Active subscribers |
|-----|--------------------|
| HackathonX | **~32** |
| SportX | **~10** |
| On both bots | **~9** |

Numbers change as people `/start` or `/stop`. Idle “scan finished, nothing new” heartbeats go to the **admin chat only** — subscribers only get real event alerts and deadline reminders.

---

## How it works

```
Platforms (Unstop, Devfolio, Meetup, …)
        │
        ▼
 GitHub Actions  ── every ~6 hours ──►  scrape → filter → dedupe
        │                                    │
        │                                    ▼
        │                         Telegram broadcast to all
        │                         Blob subscribers
        │
 Vercel (FastAPI)  ◄── Telegram webhooks ──  /start /stop /help  (instant)
        │
        ▼
 Vercel Blob JSON   (shared subscriber lists)
```

1. **Commands** (`/start`, `/stop`, `/help`) — handled instantly by Vercel webhooks  
2. **Scans** — GitHub Actions every ~6 hours (`eventx.yml` / `sportx.yml`)  
3. **Subscribers** — one Blob store for both bots; Actions and Vercel always see the same list  
4. **Seen DBs** — SQLite in-repo (`data/events.db`, `data/sportx_events.db`) so the same listing isn’t alerted twice  
5. **Reminders** — exclusive **48h** and **24h** windows when a deadline/start time is known  

### HackathonX filter rules

- Must be a **hackathon-style** listing (not random workshops / concerts)  
- **Bangalore-linked** venue: offline / finals in Bangalore only  
- Early rounds **may be online**; offline rounds in Pune, Delhi, Mumbai, etc. are **rejected**  
- Past deadlines are dropped; cross-platform duplicates merge into **one** message  

### SportX filter rules

- Bangalore + sports keywords  
- Past start times dropped  
- Same dedupe + reminder behavior as HackathonX  

---

## Tech stack

| Layer | Stack |
|-------|--------|
| Language | **Python 3.12** |
| HTTP / scraping | **httpx** |
| Config | **python-dotenv** |
| Webhooks API | **FastAPI** on **Vercel** (`app.py`) |
| Subscriber store | **Vercel Blob** (private JSON) |
| Scheduling | **GitHub Actions** (cron ~6h) |
| Alert delivery | **Telegram Bot API** |
| Seen / reminder state | **SQLite** (`data/*.db`, persisted by Actions) |
| Local / CI deps | `requirements.txt` |

**Repo layout (high level):**

| Path | Role |
|------|------|
| `main.py` | HackathonX scanner entry |
| `sportx_main.py` | SportX scanner entry |
| `app.py` | Vercel webhook handlers |
| `eventx/` | HackathonX fetchers, filters, storage, Telegram |
| `sportx/` | SportX fetchers, filters, storage, Telegram |
| `.github/workflows/` | `eventx.yml`, `sportx.yml` |
| `scripts/` | Webhook setup, Blob migration helpers |

---

## Sources

### HackathonX

| Source | Role |
|--------|------|
| [Unstop](https://unstop.com) | India hackathons |
| [Devfolio](https://devfolio.co) / [Devpost](https://devpost.com) / [MLH](https://mlh.io) | Campus & sponsored hacks |
| [Hack2Skill](https://hack2skill.com) / [DoraHacks](https://dorahacks.io) | More challenges |
| [Luma Bengaluru](https://luma.com/bengaluru) | City discover (hackathon titles only) |

HackerEarth is **not** scraped (persistent 403s).

### SportX

| Source | What it scans |
|--------|----------------|
| [AllEvents](https://allevents.in/bangalore/sports) | Bangalore sports tabs + keyword search |
| [Meetup](https://www.meetup.com/) | Bengaluru sports keyword searches |
| [Luma Bengaluru](https://luma.com/bengaluru) | City discover, sports titles only |
| [Eventbrite](https://www.eventbrite.com/b/india--bangalore/sports-and-fitness/) | Bangalore sports & fitness |

---

## Quick start (local)

```bash
cd EventX
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | HackathonX bot |
| `SPORTX_TELEGRAM_BOT_TOKEN` | SportX bot |
| `TELEGRAM_CHAT_ID` | Admin chat (idle / health) |
| `BLOB_READ_WRITE_TOKEN` | Shared subscribers (required in Actions + Vercel) |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook auth (required on Vercel) |
| `UNSTOP_MAX_PAGES` | Unstop crawl depth (default `10`) |

```bash
# Dry-run (no Telegram)
python main.py --dry-run
python sportx_main.py --dry-run

# Seed seen DB without alerting
python main.py --mark-seen
python sportx_main.py --mark-seen

# Live send
python main.py
python sportx_main.py
```

### Deploy webhooks

```bash
# 1) Vercel Blob store + env vars on the project
# 2) Deploy
vercel --prod

# 3) Point Telegram at Vercel
#    set VERCEL_WEBHOOK_BASE_URL=https://your-app.vercel.app
python scripts/set_telegram_webhooks.py
```

Endpoints: `/api/hackathonx`, `/api/sportx`.

---

## GitHub Actions secrets

| Secret | Used by |
|--------|---------|
| `TELEGRAM_BOT_TOKEN` | HackathonX |
| `TELEGRAM_CHAT_ID` | Admin / fallback |
| `SPORTX_TELEGRAM_BOT_TOKEN` | SportX |
| `SPORTX_TELEGRAM_CHAT_ID` | Optional SportX admin override |
| `BLOB_READ_WRITE_TOKEN` | Scans + same store as Vercel |

Workflows: **EventX Alerts** (`0 */6 * * *`) and **SportX Alerts** (`30 */6 * * *`), shared concurrency so SQLite pushes don’t collide.

---

## Product principles

- **No spam:** only new listings + one reminder per 48h/24h window  
- **Bangalore-first:** HackathonX won’t push finals in other cities  
- **Claim-before-send:** seen state is written before Telegram send to reduce duplicate alerts after crashes  
- **Admin noise stays private:** health + idle heartbeats are not broadcast to users  

Built for students and builders in Bengaluru who want Telegram, not another dashboard.
