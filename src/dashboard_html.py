"""
Generates a static HTML page summarizing both leagues' current state --
matchup, lineup optimization, injuries, weather -- styled to match the
draft dashboard. Regenerated fresh every monitor.py run and published
via GitHub Pages, so it's always a snapshot of "right now," not a log.
"""
from __future__ import annotations
from datetime import datetime, timezone

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');
:root { --red: #AA0000; --gold: #B3995D; --bg: #0A0A0A; --card: #160A0A; --text: #F5F1E8; }
* { box-sizing: border-box; }
body {
    background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif;
    max-width: 900px; margin: 0 auto; padding: 2rem 1.5rem;
}
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.04em; color: var(--red); }
h1 { font-size: 2.8rem; text-shadow: 0 0 18px rgba(170,0,0,0.4); margin-bottom: 0.2rem; }
.subtitle { color: var(--gold); margin-top: 0; margin-bottom: 0.5rem; }
.updated { color: #999; font-size: 0.85rem; margin-bottom: 2rem; }
hr {
    border: none; height: 3px; margin: 2rem 0;
    background: repeating-linear-gradient(90deg, var(--gold) 0px, var(--gold) 14px, transparent 14px, transparent 24px);
}
.league-card { background: var(--card); border: 1px solid var(--red); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
.matchup { color: var(--gold); font-size: 1.1rem; margin-bottom: 1rem; }
table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #333; font-size: 0.9rem; }
th { color: var(--gold); font-weight: 600; }
.tag { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.tag-out { background: var(--red); color: var(--text); }
.tag-questionable { background: var(--gold); color: var(--bg); }
.swap-suggestion { background: #1A1A00; border-left: 3px solid var(--gold); padding: 0.6rem 1rem; margin: 0.5rem 0; font-size: 0.9rem; }
.empty-state { color: #999; font-style: italic; }
.weather-flag { background: #001A2A; border-left: 3px solid #4499CC; padding: 0.6rem 1rem; margin: 0.5rem 0; font-size: 0.9rem; }
</style>
"""


def _injury_tag(status: str) -> str:
    if status in ("OUT", "DOUBTFUL", "INJURY_RESERVE"):
        return f'<span class="tag tag-out">{status}</span>'
    if status == "QUESTIONABLE":
        return f'<span class="tag tag-questionable">{status}</span>'
    return ""


def _lineup_table(players: list) -> str:
    rows = "".join(
        f"<tr><td>{p.slot_position}</td><td>{p.name}</td><td>{p.position}</td>"
        f"<td>{_injury_tag(getattr(p, 'injuryStatus', 'ACTIVE'))}</td></tr>"
        for p in players
    )
    return f"<table><tr><th>Slot</th><th>Player</th><th>Pos</th><th>Status</th></tr>{rows}</table>"


def build_league_section(section: dict) -> str:
    """
    section keys: name, has_matchup (bool), and if True: week, opponent_name,
    my_current (list), my_swaps (list), opp_swaps (list), weather_flags (list of str)
    """
    if not section["has_matchup"]:
        return f"""
        <div class="league-card">
            <h2>{section['name']}</h2>
            <p class="empty-state">No matchup yet -- draft hasn't happened, or you're on a bye.</p>
        </div>"""

    swap_html = ""
    for s in section.get("my_swaps", []):
        swap_html += (
            f'<div class="swap-suggestion">Start <b>{s["start"].name}</b> over '
            f'{s["sit"].name} (+{s["gain"]:.1f} proj pts)</div>'
        )
    if not swap_html:
        swap_html = '<p class="empty-state">Lineup looks optimal.</p>'

    weather_html = "".join(f'<div class="weather-flag">{w}</div>' for w in section.get("weather_flags", []))

    return f"""
    <div class="league-card">
        <h2>{section['name']}</h2>
        <p class="matchup">Week {section['week']} vs {section['opponent_name']}</p>
        <h3>Confirmed Casualties (Your Lineup)</h3>
        {_lineup_table(section['my_current'])}
        <h3>Suggested Moves</h3>
        {swap_html}
        {weather_html}
    </div>"""


def build_dashboard_html(league_sections: list) -> str:
    updated = datetime.now(timezone.utc).strftime("%b %d, %Y at %I:%M %p UTC")
    sections_html = "".join(build_league_section(s) for s in league_sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jamie's Casualty List</title>
{STYLE}
</head>
<body>
<h1>🏈 JAMIE'S CASUALTY LIST</h1>
<p class="subtitle">Unbothered &amp; Unbeaten.</p>
<p class="updated">Last updated: {updated}</p>
<hr>
{sections_html}
</body>
</html>"""
