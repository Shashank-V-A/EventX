from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_team_size(min_size: int | None, max_size: int | None) -> str | None:
    if min_size is None and max_size is None:
        return None
    if min_size and max_size:
        if min_size == max_size:
            return "Individual" if min_size == 1 else f"{min_size} members"
        return f"{min_size}-{max_size} members"
    if max_size:
        return f"Up to {max_size} members"
    return f"From {min_size} members"


def format_unstop_prizes(prizes: list[dict] | None) -> str | None:
    if not prizes:
        return None
    parts: list[str] = []
    total_cash = 0
    for prize in prizes[:4]:
        rank = prize.get("rank") or "Prize"
        cash = prize.get("cash")
        others = (prize.get("others") or "").strip()
        if cash:
            try:
                total_cash += int(cash)
            except (TypeError, ValueError):
                pass
            parts.append(f"{rank}: ₹{cash}")
        elif others:
            parts.append(f"{rank}: {others[:80]}")
    if total_cash:
        return f"₹{total_cash:,} total" + (f" · {parts[0]}" if parts else "")
    if parts:
        return " · ".join(parts[:2])
    return None


def format_unstop_eligibility(raw: str | dict | None) -> str | None:
    if not raw:
        return None
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw[:120]
    if not isinstance(data, dict):
        return None

    sector = data.get("sector") or []
    labels = []
    if "students" in sector:
        labels.append("Students")
    if "professionals" in sector:
        labels.append("Professionals")
    if data.get("others") == ["all"] or "all" in (data.get("experience") or []):
        labels.append("Open")
    return ", ".join(labels[:3]) if labels else None


def strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", "", value)
    return unescape(text).strip() or None
