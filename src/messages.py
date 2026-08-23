"""
Formats monitoring findings into short, text-message-friendly strings.
"""
from __future__ import annotations


def format_injury_alert(league_name: str, player, is_mine: bool, team_label: str) -> str:
    whose = "Your" if is_mine else f"{team_label}'s (opponent)"
    return (
        f"[{league_name}] {whose} starter {player.name} ({player.position}) "
        f"is {player.injuryStatus}."
    )


def format_suggestion(league_name: str, suggestion: dict) -> str:
    injured = suggestion["injured"]
    if suggestion["type"] == "lineup_swap":
        r = suggestion["replacement"]
        return (
            f"[{league_name}] {injured.name} ({injured.injuryStatus}) -- "
            f"suggested: start {r.name} instead (proj {r.projected_total_points:.1f}). "
            f"Already on your bench, no waiver needed."
        )
    else:  # waiver_claim
        add = suggestion["add"]
        drop = suggestion["drop"]
        return (
            f"[{league_name}] {injured.name} ({injured.injuryStatus}) -- "
            f"suggested: ADD {add.name} (proj {add.projected_total_points:.1f}), "
            f"DROP {drop.name} (proj {drop.projected_total_points:.1f}). "
            f"Confirm in ESPN app."
        )


def issue_key(league_name: str, player_id: int, status: str) -> str:
    """A stable identifier used to avoid re-alerting on the same status."""
    return f"{league_name}:{player_id}:{status}"
