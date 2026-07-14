"""Point Telegram bots at the Vercel webhook URLs (instant /start /stop /help)."""

from __future__ import annotations

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


def set_webhook(token: str, url: str, secret: str, name: str) -> None:
    payload = {
        "url": url,
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    }
    if secret:
        payload["secret_token"] = secret
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json=payload,
        timeout=30.0,
    )
    data = response.json()
    if not data.get("ok"):
        raise SystemExit(f"{name} setWebhook failed: {data}")
    print(f"{name}: webhook set → {url}")


def delete_webhook(token: str, name: str) -> None:
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/deleteWebhook",
        json={"drop_pending_updates": False},
        timeout=30.0,
    )
    data = response.json()
    if not data.get("ok"):
        raise SystemExit(f"{name} deleteWebhook failed: {data}")
    print(f"{name}: webhook deleted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Telegram webhooks")
    parser.add_argument(
        "--base-url",
        default=os.getenv("VERCEL_WEBHOOK_BASE_URL", ""),
        help="https://your-app.vercel.app (no trailing slash)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Remove webhooks (fall back to getUpdates)",
    )
    args = parser.parse_args()

    hx = os.getenv("TELEGRAM_BOT_TOKEN", "")
    sx = os.getenv("SPORTX_TELEGRAM_BOT_TOKEN", "")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    if args.delete:
        if hx:
            delete_webhook(hx, "HackathonX")
        if sx:
            delete_webhook(sx, "SportX")
        return

    base = args.base_url.rstrip("/")
    if not base.startswith("https://"):
        print(
            "Pass --base-url https://YOUR_DEPLOYMENT.vercel.app "
            "or set VERCEL_WEBHOOK_BASE_URL",
            file=sys.stderr,
        )
        sys.exit(1)

    if not secret:
        print(
            "Warning: TELEGRAM_WEBHOOK_SECRET is empty — "
            "set it on Vercel and here for webhook auth.",
            file=sys.stderr,
        )

    if hx:
        set_webhook(hx, f"{base}/api/hackathonx", secret, "HackathonX")
    else:
        print("Skip HackathonX (no TELEGRAM_BOT_TOKEN)")
    if sx:
        set_webhook(sx, f"{base}/api/sportx", secret, "SportX")
    else:
        print("Skip SportX (no SPORTX_TELEGRAM_BOT_TOKEN)")


if __name__ == "__main__":
    main()
