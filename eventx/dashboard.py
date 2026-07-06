from datetime import datetime

from eventx.fetchers import fetch_all_hackathons
from eventx.filter import filter_bangalore
from eventx.models import HackathonEvent

PLATFORM_LABELS = {
    "unstop": "Unstop",
    "devfolio": "Devfolio",
    "devpost": "Devpost",
    "hackerearth": "HackerEarth",
    "hack2skill": "Hack2Skill",
    "dorahacks": "DoraHacks",
}

PLATFORM_ORDER = (
    "unstop",
    "devfolio",
    "devpost",
    "hackerearth",
    "hack2skill",
    "dorahacks",
)


def collect_bangalore_events(*, max_pages: int | None = None) -> dict[str, list[HackathonEvent]]:
    by_platform = fetch_all_hackathons(max_pages=max_pages)
    grouped: dict[str, list[HackathonEvent]] = {}

    for platform in PLATFORM_ORDER:
        events = filter_bangalore(by_platform.get(platform, []))
        events.sort(
            key=lambda e: (
                e.deadline is None,
                e.deadline or datetime.max,
            )
        )
        if events:
            grouped[platform] = events

    return grouped


def _format_deadline(event: HackathonEvent) -> str:
    if not event.deadline:
        return "Not specified"
    return event.deadline.strftime("%d %b %Y")


def render_dashboard_html(grouped: dict[str, list[HackathonEvent]]) -> str:
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    total = sum(len(events) for events in grouped.values())

    sections = []
    for platform in PLATFORM_ORDER:
        events = grouped.get(platform, [])
        if not events:
            continue

        label = PLATFORM_LABELS.get(platform, platform.title())
        cards = []
        for event in events:
            location = event.location or "Not specified"
            org = event.organisation or "—"
            cards.append(
                f"""
                <article class="card">
                  <h3>{_escape(event.title)}</h3>
                  <dl>
                    <div><dt>Location</dt><dd>{_escape(location)}</dd></div>
                    <div><dt>Mode</dt><dd>{_escape(event.mode)}</dd></div>
                    <div><dt>Host</dt><dd>{_escape(org)}</dd></div>
                    <div><dt>Deadline</dt><dd>{_escape(_format_deadline(event))}</dd></div>
                  </dl>
                  <a class="btn" href="{_escape(event.registration_url)}" target="_blank" rel="noopener noreferrer">
                    Register →
                  </a>
                </article>
                """
            )

        sections.append(
            f"""
            <section class="platform" id="{platform}">
              <div class="platform-header">
                <h2>{_escape(label)}</h2>
                <span class="count">{len(events)}</span>
              </div>
              <div class="grid">{"".join(cards)}</div>
            </section>
            """
        )

    nav_links = "".join(
        f'<a href="#{p}">{PLATFORM_LABELS.get(p, p.title())} ({len(grouped[p])})</a>'
        for p in PLATFORM_ORDER
        if p in grouped
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>EventX — Bangalore Hackathons</title>
  <style>
    :root {{
      --bg: #0f1419;
      --surface: #1a2332;
      --border: #2d3a4f;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
    }}
    header {{
      padding: 2rem 1.5rem 1rem;
      max-width: 1100px;
      margin: 0 auto;
    }}
    header h1 {{ font-size: 1.75rem; font-weight: 700; }}
    header p {{ color: var(--muted); margin-top: 0.35rem; }}
    .stats {{
      display: flex;
      gap: 1rem;
      margin-top: 1rem;
      flex-wrap: wrap;
    }}
    .stat {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.6rem 1rem;
      font-size: 0.9rem;
    }}
    .stat strong {{ color: var(--accent); }}
    nav {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 0 1.5rem 1rem;
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }}
    nav a {{
      color: var(--muted);
      text-decoration: none;
      font-size: 0.85rem;
      padding: 0.35rem 0.75rem;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--surface);
    }}
    nav a:hover {{ color: var(--text); border-color: var(--accent); }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 0 1.5rem 3rem;
    }}
    .platform {{ margin-top: 2rem; }}
    .platform-header {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid var(--border);
    }}
    .platform-header h2 {{ font-size: 1.25rem; }}
    .count {{
      background: var(--accent);
      color: white;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.15rem 0.55rem;
      border-radius: 999px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .card h3 {{ font-size: 1rem; line-height: 1.35; }}
    dl {{ display: grid; gap: 0.4rem; font-size: 0.85rem; }}
    dl div {{ display: grid; grid-template-columns: 5.5rem 1fr; gap: 0.5rem; }}
    dt {{ color: var(--muted); }}
    .btn {{
      margin-top: auto;
      display: inline-block;
      text-align: center;
      background: var(--accent);
      color: white;
      text-decoration: none;
      padding: 0.6rem 1rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .btn:hover {{ background: var(--accent-hover); }}
    .empty {{
      text-align: center;
      padding: 4rem 1rem;
      color: var(--muted);
    }}
    footer {{
      text-align: center;
      padding: 2rem;
      color: var(--muted);
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>EventX</h1>
    <p>Bangalore hackathons across all platforms</p>
    <div class="stats">
      <div class="stat"><strong>{total}</strong> hackathons</div>
      <div class="stat"><strong>{len(grouped)}</strong> platforms</div>
      <div class="stat">Updated {generated_at}</div>
    </div>
  </header>
  {"<nav>" + nav_links + "</nav>" if nav_links else ""}
  <main>
    {"".join(sections) if sections else '<p class="empty">No Bangalore hackathons found right now.</p>'}
  </main>
  <footer>EventX · Auto-refreshed every 6 hours</footer>
</body>
</html>"""


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
