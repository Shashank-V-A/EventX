"""Vercel ASGI entry — Telegram webhooks for HackathonX + SportX."""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, Request, Response

from eventx.subscribers import handle_update as handle_hackathonx
from sportx.subscribers import handle_update as handle_sportx

app = FastAPI(title="EventX Telegram webhooks")


def _check_secret(secret_header: str | None) -> None:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    # On Vercel, refuse unauthenticated webhooks so anyone cannot forge /start.
    if not expected:
        if os.getenv("VERCEL"):
            raise HTTPException(
                status_code=500,
                detail="TELEGRAM_WEBHOOK_SECRET is not configured",
            )
        return
    if secret_header != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "eventx-webhooks", "status": "ok"}


@app.get("/api/hackathonx")
@app.get("/api/sportx")
def webhook_ping() -> Response:
    return Response(content="EventX Telegram webhook", media_type="text/plain")


@app.post("/api/hackathonx")
async def hackathonx_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    _check_secret(x_telegram_bot_api_secret_token)
    try:
        update = await request.json()
        if isinstance(update, dict):
            handle_hackathonx(update)
    except Exception as exc:
        print(f"hackathonx webhook error: {exc}")
    return Response(content="ok", media_type="text/plain")


@app.post("/api/sportx")
async def sportx_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    _check_secret(x_telegram_bot_api_secret_token)
    try:
        update = await request.json()
        if isinstance(update, dict):
            handle_sportx(update)
    except Exception as exc:
        print(f"sportx webhook error: {exc}")
    return Response(content="ok", media_type="text/plain")
