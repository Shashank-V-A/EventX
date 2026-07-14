"""Vercel function: HackathonX Telegram webhook → /api/hackathonx"""

from eventx.subscribers import handle_update
from eventx.webhook_http import make_webhook_handler

handler = make_webhook_handler(handle_update)
