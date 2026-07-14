from __future__ import annotations

import argparse
import sys

from sportx.dedupe import merge_duplicate_events
from sportx.fetchers import collect_all
from sportx.filter import filter_events
from sportx.notifier.telegram import notify_events, notify_health_alerts
from sportx.storage import EventStore


def run(*, dry_run: bool = False, mark_seen: bool = False) -> int:
    store = EventStore()
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
            consecutive = store.record_fetch_result(platform, ok=False, error=str(err))
            if consecutive >= 2:
                health.append((platform, consecutive, str(err)))

    filtered = filter_events(raw)
    print(f"  {len(filtered)} match Bangalore + sports filters")

    deduped = merge_duplicate_events(filtered)
    print(f"  {len(deduped)} after cross-platform dedupe")

    new_events = [e for e in deduped if not store.has_seen(e)]
    print(f"  {len(new_events)} are new (not yet notified)")

    reminders = store.events_needing_reminders()
    print(f"  {len(reminders)} reminder(s) due")

    if dry_run:
        if new_events:
            print("\n--- Dry run: would send these alerts ---")
            for event in new_events:
                platforms = ",".join(event.platforms)
                line = f"  • [{platforms}] {event.category}: {event.title}"
                try:
                    print(line)
                    print(f"    {event.registration_url}")
                except UnicodeEncodeError:
                    print(line.encode("ascii", "replace").decode())
                    print(f"    {event.registration_url}")
        if reminders:
            print("\n--- Dry run: reminders ---")
            for event, kind, _fp in reminders:
                print(f"  • [{kind}] {event.title}")
        if health:
            print("\n--- Dry run: health alerts ---")
            for platform, failures, error in health:
                print(f"  • {platform} failed {failures}x: {error[:120]}")
        if not new_events and not reminders and not health:
            print("Nothing new to send.")
        return 0

    if mark_seen:
        store.mark_many_seen(new_events)
        print(f"Marked {len(new_events)} event(s) as seen (no Telegram messages).")
        return 0

    sent = 0
    if new_events:
        sent += notify_events(new_events)
        store.mark_many_seen(new_events)
        print(f"Sent {len(new_events)} new sports alert(s).")

    for event, kind, fingerprint in reminders:
        notify_events([event], kind=kind)
        store.mark_reminder(fingerprint, kind)
        sent += 1
    if reminders:
        print(f"Sent {len(reminders)} reminder(s).")

    if health:
        notify_health_alerts(health)
        sent += len(health)
        print(f"Sent {len(health)} health alert(s).")

    if sent == 0:
        print("Nothing new to send.")
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
