# EventX

Two Bangalore Telegram alert bots in one repo:

| Bot | Entry | Workflow | DB |
|-----|--------|----------|-----|
| **HackathonX** | `python main.py` | EventX Alerts | `data/events.db` |
| **SportX** | `python sportx_main.py` | SportX Alerts | `data/sportx_events.db` |

## HackathonX

Bangalore **hackathon** alerts — software, hardware, buildathons, ideathons, video hacks, game jams.

**Sources:** Unstop · Devfolio · Devpost · MLH · HackerEarth · Hack2Skill · DoraHacks · [Luma Bengaluru](https://luma.com/bengaluru)

## SportX

Bangalore **sports** alerts — marathons, cricket, pickleball, badminton, football, tennis, cycling, and more.

**Sources:**

| Source | What it scans |
|--------|----------------|
| [AllEvents](https://allevents.in/bangalore/sports) | Bangalore sports tabs + keyword search (pickleball, marathon, cricket, …) |
| [Meetup](https://www.meetup.com/) | Bengaluru sports keyword searches |
| [Luma Bengaluru](https://luma.com/bengaluru) | City discover feed, sports titles only |
| [Eventbrite](https://www.eventbrite.com/b/india--bangalore/sports-and-fitness/) | Bangalore sports & fitness (when listed) |

Then SportX keeps only sports-looking titles and alerts on Telegram.

## Public subscriptions (open)

Anyone can use the bots:

1. Open the bot on Telegram → tap **Start** (`/start`)
2. They receive **real event alerts** (and deadline reminders)
3. `/stop` unsubscribes

| Bot | Username |
|-----|----------|
| HackathonX | [@EventXva05Bot](https://t.me/EventXva05Bot) |
| SportX | [@Sportx_va_bot](https://t.me/Sportx_va_bot) |

**Idle “scan done — no new events” messages stay admin-only** (your chat id).

**Commands are instant via Vercel webhooks** (`/api/hackathonx`, `/api/sportx`).  
Scans stay on GitHub Actions (~6 hours). Both read the same **Upstash Redis** subscriber sets.

| Env | Where |
|-----|--------|
| `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` | Vercel + GitHub Actions secrets |
| Bot tokens + `TELEGRAM_CHAT_ID` | Vercel + GitHub Actions secrets |
| `TELEGRAM_WEBHOOK_SECRET` | Vercel + local `.env` (for `setWebhook`) |

```bash
# 1) Deploy webhooks
vercel --prod

# 2) Point Telegram at Vercel (after setting VERCEL_WEBHOOK_BASE_URL)
python scripts/set_telegram_webhooks.py

# Optional: copy existing local SQLite subscribers into Redis
python scripts/migrate_subscribers_to_redis.py
```

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
TELEGRAM_BOT_TOKEN=...              # HackathonX
SPORTX_TELEGRAM_BOT_TOKEN=...       # SportX (@Sportx_va_bot)
TELEGRAM_CHAT_ID=...                # shared chat is fine
UNSTOP_MAX_PAGES=10
UNSTOP_TYPES=hackathons
INCLUDE_ONLINE=false
```

Run:

```bash
# Hackathons
python main.py --dry-run
python main.py --mark-seen
python main.py

# Sports
python sportx_main.py --dry-run
python sportx_main.py --mark-seen
python sportx_main.py
```

## What you get

Every ~6 hours via GitHub Actions (separate workflows):

1. Scans the right platforms for that bot
2. Keeps Bangalore / Bengaluru listings
3. Applies hackathon **or** sports filters
4. Dedupes → **one** Telegram message per listing
5. Reminds at **48h** / **24h** when a date is known
6. Health warning if a source fails twice in a row (admin only)
7. Broadcasts new events to **all** `/start` subscribers

## GitHub Actions

Repo secrets:

| Secret | Used by |
|--------|---------|
| `TELEGRAM_BOT_TOKEN` | HackathonX |
| `TELEGRAM_CHAT_ID` | Both (fallback for SportX) |
| `SPORTX_TELEGRAM_BOT_TOKEN` | SportX |
| `SPORTX_TELEGRAM_CHAT_ID` | Optional SportX override |
| `UPSTASH_REDIS_REST_URL` | Scans + Vercel webhooks |
| `UPSTASH_REDIS_REST_TOKEN` | Scans + Vercel webhooks |

Then run **EventX Alerts** and/or **SportX Alerts**.

## HackathonX sources

| Source | Role |
|--------|------|
| Unstop | India hackathons |
| Devfolio / Devpost / MLH | Campus & sponsored hacks |
| HackerEarth / Hack2Skill / DoraHacks | More challenges |
| Luma | [luma.com/bengaluru](https://luma.com/bengaluru) discover feed (hackathons only; extra URLs via `LUMA_EVENT_URLS`) |
