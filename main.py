import argparse
import sys

from eventx.fetchers.unstop import fetch_unstop_hackathons
from eventx.filter import filter_bangalore
from eventx.notifier.telegram import notify_events
from eventx.storage import get_new_events, init_db, mark_notified


def run(*, dry_run: bool = False, max_pages: int | None = None) -> int:
    init_db()

    print("Fetching hackathons from Unstop...")
    all_events = fetch_unstop_hackathons(max_pages=max_pages)
    print(f"  Found {len(all_events)} open hackathons")

    bangalore_events = filter_bangalore(all_events)
    print(f"  {len(bangalore_events)} match Bangalore filter")

    new_events = get_new_events(bangalore_events)
    print(f"  {len(new_events)} are new (not yet notified)")

    if not new_events:
        print("Nothing new to send.")
        return 0

    if dry_run:
        print("\n--- Dry run: would send these alerts ---")
        for event in new_events:
            print(f"  • {event.title}")
            print(f"    {event.registration_url}")
        return 0

    sent = notify_events(new_events)
    mark_notified(new_events)
    print(f"Sent {sent} Telegram alert(s).")
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EventX — get Bangalore hackathon alerts on Telegram"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter without sending Telegram messages",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override UNSTOP_MAX_PAGES from .env",
    )
    args = parser.parse_args()

    try:
        run(dry_run=args.dry_run, max_pages=args.max_pages)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
