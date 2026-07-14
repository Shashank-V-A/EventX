"""Upstash Redis REST helpers for shared subscriber lists (Vercel + Actions)."""

from __future__ import annotations

import os

import httpx

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")


def redis_configured() -> bool:
    return bool(UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN)


def redis_command(*parts: str | int) -> object:
    if not redis_configured():
        raise RuntimeError(
            "Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN "
            "(shared store for Vercel webhooks + GitHub scans)"
        )
    response = httpx.post(
        UPSTASH_REDIS_REST_URL,
        headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
        json=list(parts),
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Upstash error: {payload['error']}")
    return payload.get("result") if isinstance(payload, dict) else payload


def active_key(bot: str) -> str:
    return f"eventx:{bot}:active"


def sadd_active(bot: str, chat_id: str) -> None:
    redis_command("SADD", active_key(bot), str(chat_id))


def srem_active(bot: str, chat_id: str) -> bool:
    removed = redis_command("SREM", active_key(bot), str(chat_id))
    return int(removed or 0) > 0


def smembers_active(bot: str) -> list[str]:
    members = redis_command("SMEMBERS", active_key(bot)) or []
    if not isinstance(members, list):
        return []
    ids = [str(m) for m in members]
    ids.sort()
    return ids


def sismember_active(bot: str, chat_id: str) -> bool:
    return bool(int(redis_command("SISMEMBER", active_key(bot), str(chat_id)) or 0))
