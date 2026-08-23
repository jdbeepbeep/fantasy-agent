"""
Wraps a call to the Claude API to give pick advice during the draft.
Keeps the prompt logic in one place so it's easy to tune later.
"""
from __future__ import annotations
import os
from anthropic import Anthropic


def get_draft_advice(
    question: str,
    best_available: list,
    my_roster: list,
    scoring_type: str,
    top_n: int = 30,
) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    top_players_text = "\n".join(
        f"- {p.name} ({p.position}, {p.proTeam}) — proj. {p.projected_total_points:.1f} pts, "
        f"{p.percent_owned:.0f}% owned"
        for p in best_available[:top_n]
    )

    roster_text = "\n".join(
        f"- {p.name} ({p.position})" for p in my_roster
    ) or "(no picks yet)"

    prompt = f"""You are helping with a live fantasy football draft, {scoring_type} scoring.

My roster so far:
{roster_text}

Top {top_n} best available players by projected points:
{top_players_text}

My question: {question}

Give a direct, specific recommendation with brief reasoning. If recommending
a player, name them explicitly. Keep it concise -- this is a live draft,
I need to decide quickly."""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
