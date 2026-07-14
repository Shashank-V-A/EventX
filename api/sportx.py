"""Vercel function: SportX Telegram webhook → /api/sportx"""

from eventx.webhook_http import make_webhook_handler
from sportx.subscribers import handle_update

handler = make_webhook_handler(handle_update)
