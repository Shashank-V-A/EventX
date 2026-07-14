"""Poll both bots for /start /stop /help without running a full scan."""

from __future__ import annotations

import sys


def main() -> None:
    hx = sx = 0
    try:
        from eventx.subscribers import SubscriberStore as HxStore
        from eventx.subscribers import process_commands as hx_process

        store = HxStore()
        hx = hx_process(store=store)
        print(f"HackathonX: handled {hx} command(s), subscribers={store.count_active()}")
    except Exception as exc:
        print(f"HackathonX sync failed: {exc}", file=sys.stderr)

    try:
        from sportx.subscribers import SubscriberStore as SxStore
        from sportx.subscribers import process_commands as sx_process

        store = SxStore()
        sx = sx_process(store=store)
        print(f"SportX: handled {sx} command(s), subscribers={store.count_active()}")
    except Exception as exc:
        print(f"SportX sync failed: {exc}", file=sys.stderr)

    if hx == 0 and sx == 0:
        print("No new subscriber commands.")


if __name__ == "__main__":
    main()
