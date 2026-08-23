"""
Core data functions for the draft dashboard. Kept separate from the
Streamlit UI so the logic is easy to test and reuse later for the
season-long monitoring tool.
"""
from __future__ import annotations
from espn_api.football import League
from espn_api.football.team import Team
from espn_api.football.player import Player


def find_my_team(league: League, swid: str) -> Team | None:
    """
    Auto-detects which team belongs to you by matching your SWID
    against ESPN's owner records for each team.
    """
    normalized_swid = swid.strip().upper()
    for team in league.teams:
        for owner in team.owners:
            if owner.get("id", "").strip().upper() == normalized_swid:
                return team
    return None


def get_best_available(league: League, size: int = 200) -> list[Player]:
    """
    Returns undrafted players sorted by projected fantasy points,
    highest first. Pre-draft, this is effectively the entire draft pool.
    """
    players = league.free_agents(size=size)
    return sorted(players, key=lambda p: p.projected_total_points, reverse=True)


def filter_by_position(players: list[Player], position: str) -> list[Player]:
    """position: 'ALL', 'QB', 'RB', 'WR', 'TE', 'K', 'D/ST'"""
    if position == "ALL":
        return players
    return [p for p in players if p.position == position]


def get_draft_picks(league: League) -> list:
    """
    Returns picks made so far, in order. Empty list before the draft
    starts or if called before refresh_draft().
    """
    league.refresh_draft()
    return league.draft


def get_my_roster_so_far(league: League, my_team: Team) -> list:
    """
    During a live draft, a team's roster fills in pick by pick.
    This re-fetches so the roster panel stays current.
    """
    league.refresh_draft()
    for team in league.teams:
        if team.team_id == my_team.team_id:
            return team.roster
    return []


def summarize_roster_needs(roster: list) -> dict:
    """
    Simple count of how many players you have at each position so far,
    used to flag thin spots in the dashboard.
    """
    counts: dict[str, int] = {}
    for player in roster:
        counts[player.position] = counts.get(player.position, 0) + 1
    return counts
