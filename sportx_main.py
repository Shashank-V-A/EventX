from __future__ import annotations

import argparse
import sys

from eventx.blob_store import require_shared_store
from sportx.dedupe import merge_duplicate_events
from sportx.fetchers import collect_all
from sportx.filter import filter_events
from sportx.models import SportEvent
from sportx.notifier.telegram import (
    notify_events,
    notify_health_alerts,
    notify_scan_idle,
)
from sportx.storage import EventStore
from sportx.subscribers import SubscriberStore


def _enrich_reminders_from_live(
    reminders: list[tuple[SportEvent, str, str]],
    live: list[SportEvent],
) -> list[tuple[SportEvent, str, str]]:
    """Prefer freshly fetched listing details when reminding about an event."""
    by_fp = {e.fingerprint: e for e in live}
    by_url = {e.registration_url.rstrip("/"): e for e in live if e.registration_url}
    enriched: list[tuple[SportEvent, str, str]] = []
    for event, kind, fingerprint in reminders:
        live_event = by_fp.get(fingerprint) or by_url.get(event.registration_url.rstrip("/"))
        if live_event:
            # Keep reminder timing; use live metadata
            live_event.deadline = event.deadline or live_event.deadline
            enriched.append((live_event, kind, fingerprint))
        else:
            enriched.append((event, kind, fingerprint))
    return enriched


def run(*, dry_run: bool = False, mark_seen: bool = False) -> int:
    require_shared_store(context="SportX scan")
    store = EventStore()
    # /start /stop /help are handled instantly by the Vercel webhook (app.py)
    subs = SubscriberStore()
    print(f"  Subscribers: {subs.count_active()} (Vercel Blob)")
    print("Fetching Bangalore sports events (SportX)...")

    raw, results = collect_all()
    health: list[tuple[str, int, str]] = []

    for platform, err in results:
        if err is None:
            count = sum(1 for e in raw if platform in e.platforms or e.platform == platform)
            print(f"  {platform}: ok ({count} raw listings)")
            store.record_fetch_result(platform, ok=True)
        else:
            print(f"  {platform}: FAILED — {err}")
            consecutive, should_alert = store.record_fetch_result(
                platform, ok=False, error=str(err)
            )
            if should_alert:
                health.append((platform, consecutive, str(err)))

    filtered = filter_events(raw)
    print(f"  {len(filtered)} match Bangalore + sports filters")

    deduped = merge_duplicate_events(filtered)
    print(f"  {len(deduped)} after cross-platform dedupe")

    # Keep stored details fresh for future reminders
    store.refresh_seen_metadata(deduped)

    new_events = [e for e in deduped if not store.has_seen(e)]
    print(f"  {len(new_events)} are new (not yet notified)")

    live_fps = {e.fingerprint for e in deduped}
    live_urls = {e.registration_url.rstrip("/") for e in deduped if e.registration_url}
    reminders = _enrich_reminders_from_live(store.events_needing_reminders(), deduped)
    # Only remind for listings still present in this scan's filtered set.
    reminders = [
        (e, k, fp)
        for e, k, fp in reminders
        if fp in live_fps or e.registration_url.rstrip("/") in live_urls
    ]
    print(f"  {len(reminders)} reminder(s) due")

    if dry_run:
        if new_events:
            print("\n--- Dry run: would send these alerts ---")
            for event in new_events:
                platforms = ",".join(event.platforms)
                line = f"  • [{platforms}] {event.category}: {event.title}"
                try:
                    print(line)
                    if event.organisation:
                        print(f"    host: {event.organisation}")
                    if event.image_url:
                        print(f"    image: {event.image_url}")
                    if event.description:
                        print(f"    desc: {event.description[:120]}")
                    print(f"    {event.registration_url}")
                except UnicodeEncodeError:
                    print(line.encode("ascii", "replace").decode())
                    print(f"    {event.registration_url}")
        if reminders:
            print("\n--- Dry run: reminders ---")
            for event, kind, _fp in reminders:
                print(f"  • [{kind}] {event.title} | {event.organisation or '-'} | img={bool(event.image_url)}")
        if health:
            print("\n--- Dry run: health alerts ---")
            for platform, failures, error in health:
                print(f"  • {platform} failed {failures}x: {error[:120]}")
        if not new_events and not reminders and not health:
            print("Nothing new to send (would send idle heartbeat).")
        elif not new_events and not reminders:
            print("\n--- Dry run: would send idle heartbeat (no new events) ---")
        return 0

    if mark_seen:
        store.mark_many_seen(deduped)
        print(f"Marked {len(deduped)} event(s) as seen (no Telegram messages).")
        return 0

    sent = 0
    if new_events:
        # Claim before send so a crash after Telegram cannot re-alert next run.
        store.mark_many_seen(new_events)
        sent += notify_events(new_events)
        print(f"Sent {len(new_events)} new sports alert(s).")

    for event, kind, fingerprint in reminders:
        # Claim before send so a partial failure can't double-notify next run.
        store.mark_reminder(fingerprint, kind, also=event.dedupe_key)
        notify_events([event], kind=kind)
        sent += 1
    if reminders:
        print(f"Sent {len(reminders)} reminder(s).")

    if health:
        notify_health_alerts(health)
        store.mark_health_alerted([p for p, _, _ in health])
        sent += len(health)
        print(f"Sent {len(health)} health alert(s).")

    if not new_events and not reminders:
        notify_scan_idle()
        sent += 1
        print("Sent idle scan heartbeat (no new events).")

    return sent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SportX — Bangalore marathons & sports events on Telegram"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter without sending Telegram messages",
    )
    parser.add_argument(
        "--mark-seen",
        action="store_true",
        help="Mark current events as seen without sending alerts",
    )
    args = parser.parse_args()

    try:
        run(dry_run=args.dry_run, mark_seen=args.mark_seen)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
