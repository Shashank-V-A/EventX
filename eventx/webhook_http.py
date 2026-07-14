"""HTTP helpers for Vercel Telegram webhook handlers."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler
from typing import Callable


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("content-length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _ok(handler: BaseHTTPRequestHandler, body: bytes = b"ok") -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _fail(handler: BaseHTTPRequestHandler, code: int, message: str) -> None:
    body = message.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/plain")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def require_secret(handler: BaseHTTPRequestHandler) -> bool:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected:
        return True
    got = handler.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return got == expected


def make_webhook_handler(handle_update: Callable[[dict], bool]):
    class handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            _ok(self, b"EventX Telegram webhook")

        def do_POST(self) -> None:  # noqa: N802
            if not require_secret(self):
                _fail(self, 401, "unauthorized")
                return
            try:
                update = _read_json(self)
                handle_update(update)
            except Exception as exc:
                print(f"webhook error: {exc}")
            _ok(self)

    return handler
