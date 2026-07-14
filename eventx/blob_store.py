"""Vercel Blob JSON store for shared subscriber lists (Vercel + Actions)."""

from __future__ import annotations

import json
import os
import time
from urllib.parse import quote

import httpx

BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv(
    "VERCEL_BLOB_READ_WRITE_TOKEN", ""
)
BLOB_API = (
    os.getenv("VERCEL_BLOB_API_URL")
    or os.getenv("NEXT_PUBLIC_VERCEL_BLOB_API_URL")
    or "https://vercel.com/api/blob"
).rstrip("/")
API_VERSION = os.getenv("VERCEL_BLOB_API_VERSION_OVERRIDE") or "11"


def blob_configured() -> bool:
    return bool(BLOB_READ_WRITE_TOKEN)


def shared_store_configured() -> bool:
    """Alias used by subscribers / webhooks."""
    return blob_configured()


def _store_id() -> str:
    parts = BLOB_READ_WRITE_TOKEN.split("_")
    # vercel_blob_rw_<storeId>_...
    if len(parts) > 3:
        return parts[3]
    raise RuntimeError("BLOB_READ_WRITE_TOKEN format not recognized")


def _pathname(bot: str) -> str:
    return f"eventx/{bot}-subscribers.json"


def _auth_headers(**extra: str) -> dict[str, str]:
    headers = {
        "authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
        "x-api-version": str(API_VERSION),
    }
    headers.update(extra)
    return headers


def _require_token() -> None:
    if not blob_configured():
        raise RuntimeError(
            "Set BLOB_READ_WRITE_TOKEN (Vercel Blob) for shared subscribers "
            "between Vercel webhooks and GitHub scans"
        )


def _private_url(pathname: str) -> str:
    return f"https://{_store_id()}.private.blob.vercel-storage.com/{pathname}"


def _load_active(bot: str) -> set[str]:
    _require_token()
    pathname = _pathname(bot)
    url = _private_url(pathname)
    response = httpx.get(url, headers=_auth_headers(), timeout=20.0, follow_redirects=True)
    if response.status_code == 404:
        return set()
    if response.status_code >= 400:
        # Fallback: list API then fetch by returned URL
        listed = httpx.get(
            BLOB_API,
            params={"prefix": pathname, "limit": "10"},
            headers=_auth_headers(),
            timeout=20.0,
        )
        listed.raise_for_status()
        payload = listed.json()
        blobs = payload.get("blobs") if isinstance(payload, dict) else None
        if not blobs:
            return set()
        url = blobs[0].get("url") or blobs[0].get("downloadUrl")
        if not url:
            return set()
        response = httpx.get(
            url, headers=_auth_headers(), timeout=20.0, follow_redirects=True
        )
        if response.status_code == 404:
            return set()
    response.raise_for_status()
    try:
        data = response.json()
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    active = data.get("active") or []
    if not isinstance(active, list):
        return set()
    return {str(x) for x in active if x is not None and str(x).strip()}


def _save_active(bot: str, active: set[str]) -> None:
    _require_token()
    pathname = _pathname(bot)
    body = json.dumps(
        {
            "active": sorted(active),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    response = httpx.put(
        f"{BLOB_API}?pathname={quote(pathname, safe='')}",
        headers=_auth_headers(
            **{
                "x-content-type": "application/json",
                "x-add-random-suffix": "0",
                "x-allow-overwrite": "1",
                "x-vercel-blob-access": "private",
            }
        ),
        content=body,
        timeout=30.0,
    )
    response.raise_for_status()


def add_active(bot: str, chat_id: str) -> bool:
    """Add chat_id. Returns True if it was newly added."""
    chat_id = str(chat_id)
    active = _load_active(bot)
    if chat_id in active:
        return False
    active.add(chat_id)
    _save_active(bot, active)
    return True


def remove_active(bot: str, chat_id: str) -> bool:
    chat_id = str(chat_id)
    active = _load_active(bot)
    if chat_id not in active:
        return False
    active.discard(chat_id)
    _save_active(bot, active)
    return True


def list_active(bot: str) -> list[str]:
    return sorted(_load_active(bot))


def is_active(bot: str, chat_id: str) -> bool:
    return str(chat_id) in _load_active(bot)


# Back-compat names used during Redis era (kept for fewer call-site edits)
def sadd_active(bot: str, chat_id: str) -> None:
    add_active(bot, chat_id)


def srem_active(bot: str, chat_id: str) -> bool:
    return remove_active(bot, chat_id)


def smembers_active(bot: str) -> list[str]:
    return list_active(bot)


def sismember_active(bot: str, chat_id: str) -> bool:
    return is_active(bot, chat_id)
