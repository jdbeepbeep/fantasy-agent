"""
Wraps a call to the Claude API to give pick advice during the draft.
Keeps the prompt logic in one place so it's easy to tune later.
"""
from __future__ import annotations
import os
from anthropic import Anthropic
from src.consensus import get_consensus_rank


def get_draft_advice(
    question: str,
    best_available: list,
    my_roster: list,
    scoring_type: str,
    top_n: int = 30,
    consensus_rankings: dict | None = None,
) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def player_line(p):
        line = (
            f"- {p.name} ({p.position}, {p.proTeam}) — proj. {p.projected_total_points:.1f} pts, "
            f"{p.percent_owned:.0f}% owned"
        )
        if consensus_rankings:
            rank = get_consensus_rank(p.name, consensus_rankings)
            if rank is not None:
                line += f", expert consensus rank #{rank}"
        return line

    top_players_text = "\n".join(player_line(p) for p in best_available[:top_n])

    roster_text = "\n".join(
        f"- {p.name} ({p.position})" for p in my_roster
    ) or "(no picks yet)"

    consensus_note = (
        "\n\nWhere available, expert consensus rank is included alongside ESPN's "
        "own projection -- weigh both, and note if they disagree meaningfully."
        if consensus_rankings else ""
    )

    prompt = f"""You are a confident, trash-talking fantasy football analyst
helping with a live draft, {scoring_type} scoring. Be cocky and a little
savage in tone -- but the actual advice underneath must be genuinely sharp
and correct. Don't sacrifice real analysis for the bit.

My roster so far:
{roster_text}

Top {top_n} best available players by projected points:
{top_players_text}

My question: {question}

Give a direct, specific recommendation with brief reasoning, in that voice.
If recommending a player, name them explicitly. Keep it concise -- this is
a live draft, I need to decide quickly.{consensus_note}"""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
