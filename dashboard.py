import argparse
import http.server
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path

from eventx.dashboard import collect_bangalore_events, render_dashboard_html

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "docs" / "index.html"
DEFAULT_PORT = 8080
MAX_PORT_TRIES = 20


def generate_dashboard(*, output: Path, max_pages: int | None) -> int:
    print("Fetching Bangalore hackathons from all platforms...")
    grouped = collect_bangalore_events(max_pages=max_pages)

    for platform, events in grouped.items():
        print(f"  {platform}: {len(events)}")

    total = sum(len(v) for v in grouped.values())
    print(f"  total: {total} Bangalore hackathons")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_dashboard_html(grouped), encoding="utf-8")
    print(f"Dashboard written to {output}")
    return total


def _find_free_port(start: int) -> int:
    for offset in range(MAX_PORT_TRIES):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
            except OSError:
                continue
            return port
    raise OSError(f"No free port found in range {start}-{start + MAX_PORT_TRIES - 1}")


def serve_dashboard(directory: Path, port: int) -> None:
    handler = http.server.SimpleHTTPRequestHandler

    class DashboardHandler(handler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    chosen_port = _find_free_port(port)
    if chosen_port != port:
        print(f"Port {port} is busy, using {chosen_port} instead.")

    with ReusableTCPServer(("", chosen_port), DashboardHandler) as httpd:
        url = f"http://127.0.0.1:{chosen_port}/"
        print(f"Serving dashboard at {url}")
        print("Press Ctrl+C to stop.")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="EventX dashboard — view Bangalore hackathons")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write index.html (default: docs/index.html)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Generate dashboard and serve it locally",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Port for local server (default: 8080)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override UNSTOP_MAX_PAGES when fetching",
    )
    args = parser.parse_args()

    try:
        generate_dashboard(output=args.output, max_pages=args.max_pages)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.serve:
        serve_dashboard(args.output.parent, args.port)


if __name__ == "__main__":
    main()
