import argparse
import sys

from eventx.blob_store import require_shared_store
from eventx.dedupe import merge_duplicate_events
from eventx.fetchers import FETCHERS, fetch_all_hackathons
from eventx.filter import filter_bangalore, filter_hackathons, filter_open_events
from eventx.notifier.telegram import (
    notify_events,
    notify_health_alerts,
    notify_scan_idle,
)
from eventx.storage import (
    count_seen,
    get_due_reminders,
    get_health_alerts,
    get_new_events,
    init_db,
    mark_health_alerted,
    mark_notified,
    mark_reminder_sent,
    prune_fetch_failures,
)
from eventx.subscribers import SubscriberStore


def run(
    *,
    dry_run: bool = False,
    mark_seen: bool = False,
    max_pages: int | None = None,
) -> int:
    require_shared_store(context="HackathonX scan")
    init_db()
    # /start /stop /help are handled instantly by the Vercel webhook (app.py)
    store = SubscriberStore()
    print(f"  Subscribers: {store.count_active()} (Vercel Blob)")
    print(f"  Seen events in database: {count_seen()}")

    prune_fetch_failures({name for name, _ in FETCHERS})

    by_platform, failed = fetch_all_hackathons(max_pages=max_pages)
    all_events = []
    for platform, events in by_platform.items():
        print(f"  {platform}: {len(events)} open hackathons")
        all_events.extend(events)
    if failed:
        print(f"  failed sources: {', '.join(failed)}")

    print(f"  total: {len(all_events)} open listings")

    bangalore_events = filter_bangalore(all_events)
    print(f"  {len(bangalore_events)} match Bangalore venue filter")

    hackathons = filter_hackathons(bangalore_events)
    print(f"  {len(hackathons)} match hackathon filter")

    open_events = filter_open_events(hackathons)
    print(f"  {len(open_events)} still open (deadline not past)")

    deduped = merge_duplicate_events(open_events)
    print(f"  {len(deduped)} after cross-platform dedupe")

    new_events = get_new_events(deduped)
    print(f"  {len(new_events)} are new (not yet notified)")

    events_by_key = {e.dedupe_key: e for e in deduped}
    reminders = get_due_reminders(events_by_key)
    print(f"  {len(reminders)} deadline reminder(s) due")

    health = get_health_alerts(threshold=2)
    if health:
        print(f"  {len(health)} health alert(s) pending")

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
            print("\n--- Dry run: deadline reminders ---")
            for event, kind in reminders:
                print(f"  • [{kind}] {event.title} → {event.deadline}")
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
        mark_notified(new_events, suppress_reminders=True)
        print(f"Marked {len(new_events)} event(s) as seen (no Telegram messages).")
        print(f"  Seen events in database: {count_seen()}")
        return 0

    sent = 0

    if new_events:
        # Claim before send so a crash after Telegram cannot re-alert next run.
        mark_notified(new_events)
        sent += notify_events(new_events)
        print(f"Sent {len(new_events)} new hackathon alert(s).")

    for event, kind in reminders:
        mark_reminder_sent(event, kind)
        notify_events([event], kind=kind)
        sent += 1
    if reminders:
        print(f"Sent {len(reminders)} deadline reminder(s).")

    if not new_events and not reminders:
        notify_scan_idle()
        sent += 1
        print("Sent idle scan heartbeat (no new events).")

    if health:
        notify_health_alerts(health)
        mark_health_alerted([p for p, _, _ in health])
        sent += len(health)
        print(f"Sent {len(health)} health alert(s).")

    print(f"  Seen events in database: {count_seen()}")
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HackathonX — Bangalore hackathons, buildathons & ideathons on Telegram"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter without sending Telegram messages",
    )
    parser.add_argument(
        "--mark-seen",
        action="store_true",
        help="Mark current Bangalore hackathons as seen without sending alerts",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override UNSTOP_MAX_PAGES from .env",
    )
    args = parser.parse_args()

    try:
        print("Fetching Bangalore hackathons (HackathonX)...")
        run(
            dry_run=args.dry_run,
            mark_seen=args.mark_seen,
            max_pages=args.max_pages,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
