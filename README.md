# EventX

Get Bangalore hackathon registration links delivered to your Telegram.

**Platforms:** Unstop, Devfolio, Devpost, HackerEarth, Hack2Skill, DoraHacks

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

## Schedule it (GitHub Actions — every 6 hours)

EventX runs automatically via [GitHub Actions](https://github.com/Shashank-V-A/EventX/actions) — no need to keep your PC on.

### One-time setup

1. **Add repository secrets** at  
   [github.com/Shashank-V-A/EventX/settings/secrets/actions](https://github.com/Shashank-V-A/EventX/settings/secrets/actions)

   | Secret name | Value |
   |-------------|-------|
   | `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
   | `TELEGRAM_CHAT_ID` | Your Telegram chat ID (`8637683031` if you used the same bot) |

2. **Enable workflows** — open the [Actions tab](https://github.com/Shashank-V-A/EventX/actions), click **I understand my workflows, go ahead and enable them** if prompted.

3. **Test manually** — select **EventX Alerts** → **Run workflow** → **Run workflow**.

After that, it runs every 6 hours on GitHub's servers. Seen events are stored in Actions cache so you won't get duplicate alerts.

> **Note:** If you already ran EventX locally first, the initial GitHub run may resend alerts for hackathons you've already seen (GitHub starts with an empty cache). After that first run, only new hackathons are sent.

### Local run (optional)

You can still run manually on your machine for testing:

```bash
python main.py --dry-run
python main.py
```

## How it works

1. Fetches open hackathons from Unstop, Devfolio, Devpost, HackerEarth, Hack2Skill, and DoraHacks
2. Filters for Bangalore / Bengaluru (city, address, org name, or URL)
3. Skips events you've already been notified about (SQLite)
4. Sends a Telegram message with the registration link

### Platform notes

| Platform | Method | Bangalore coverage |
|----------|--------|-------------------|
| Unstop | Public API | Best for India/college hackathons |
| Devfolio | Public API | Good — includes city in location |
| Devpost | Public API | Global; filters on displayed location |
| HackerEarth | HTML listing | Mostly online; catches Bangalore in title/URL |
| Hack2Skill | Public API | Indian events; filters on title/URL |
| DoraHacks | Public API | Global; filters on venue/title |
| LabLab.ai | — | Blocked by Cloudflare (not supported yet) |
| Luma | — | No public discovery API (not supported yet) |

## Project structure

```
EventX/
├── main.py                 # Entry point
├── eventx/
│   ├── fetchers/
│   │   ├── unstop.py
│   │   ├── devfolio.py
│   │   ├── devpost.py
│   │   ├── hackerearth.py
│   │   ├── hack2skill.py
│   │   └── dorahacks.py
│   ├── filter.py
│   ├── notifier/telegram.py
│   ├── storage.py          # SQLite deduplication
│   └── models.py
└── data/events.db          # Created on first run
```

## Next steps

- Add LabLab.ai / Luma when reliable access is available
- Add filters for online / AI hackathons only
