"""
Season-long monitoring: checks your current matchup for injuries on your
roster and your opponent's, and drafts a waiver suggestion when a starter
is ruled out and there's a clearly-better replacement available.
"""
from __future__ import annotations
from espn_api.football import League
from espn_api.football.team import Team
from src.draft_data import get_best_available

# Statuses worth alerting on. QUESTIONABLE is informational only --
# never triggers an auto-suggested move, just a heads up.
URGENT_STATUSES = {"OUT", "DOUBTFUL", "INJURY_RESERVE"}
INFO_STATUSES = {"QUESTIONABLE"}

# A waiver suggestion only fires if the top available option beats your
# best bench alternative at that position by at least this many projected
# points -- otherwise it's ambiguous and we just flag the injury instead.
OBVIOUS_MARGIN = 3.0


def get_current_matchup(league: League, my_team: Team):
    """
    Returns the BoxScore for my_team's current-week matchup, or None if
    there's no matchup yet (bye week, or season/draft hasn't started).
    """
    week = league.current_week
    try:
        matchups = league.box_scores(week=week)
    except KeyError:
        # ESPN has no roster/matchup data yet -- typically means the
        # draft hasn't happened for this league yet.
        return None
    for matchup in matchups:
        if matchup.home_team == my_team or matchup.away_team == my_team:
            return matchup
    return None


def get_my_lineup_and_opponent(matchup, my_team: Team):
    """Returns (my_lineup, opponent_team, opponent_lineup) for a BoxScore."""
    if matchup.home_team == my_team:
        return matchup.home_lineup, matchup.away_team, matchup.away_lineup
    return matchup.away_lineup, matchup.home_team, matchup.home_lineup


def check_lineup_injuries(lineup: list, starters_only: bool = True) -> list:
    """
    Returns players in this lineup with an urgent or informational
    injury status. Bench/IR slots are skipped when starters_only=True,
    since a bench injury doesn't need same-day action.
    """
    flagged = []
    for player in lineup:
        if starters_only and player.slot_position in ("BE", "IR"):
            continue
        status = getattr(player, "injuryStatus", "ACTIVE")
        if status in URGENT_STATUSES or status in INFO_STATUSES:
            flagged.append(player)
    return flagged


def suggest_replacement(league: League, injured_player, my_roster: list) -> dict:
    """
    For an OUT/DOUBTFUL starter, looks for:
      1) A same-position bench player already on your roster (no waiver needed)
      2) The best available free agent at that position

    Returns a dict describing the suggestion, or {"obvious": False, ...}
    if there's no clearly-better option (ambiguous -- just flag, don't suggest).
    """
    position = injured_player.position

    bench_options = [
        p for p in my_roster
        if p.position == position
        and p.slot_position == "BE"
        and getattr(p, "injuryStatus", "ACTIVE") not in URGENT_STATUSES
    ]
    bench_options.sort(key=lambda p: p.projected_total_points, reverse=True)

    best_available = get_best_available(league, size=100)
    waiver_options = [p for p in best_available if p.position == position]

    best_bench = bench_options[0] if bench_options else None
    best_waiver = waiver_options[0] if waiver_options else None

    # Case 1: a bench player covers it -- just a lineup swap, no waiver claim needed
    if best_bench and (
        not best_waiver
        or best_bench.projected_total_points >= best_waiver.projected_total_points - OBVIOUS_MARGIN
    ):
        return {
            "obvious": True,
            "type": "lineup_swap",
            "injured": injured_player,
            "replacement": best_bench,
        }

    # Case 2: a waiver pickup is the clearly better option
    if best_waiver:
        drop_candidates = sorted(
            [p for p in my_roster if p.slot_position == "BE"],
            key=lambda p: p.projected_total_points,
        )
        margin_ok = (
            not best_bench
            or best_waiver.projected_total_points - best_bench.projected_total_points >= OBVIOUS_MARGIN
        )
        if margin_ok and drop_candidates:
            return {
                "obvious": True,
                "type": "waiver_claim",
                "injured": injured_player,
                "add": best_waiver,
                "drop": drop_candidates[0],
            }

    # Ambiguous -- don't guess, just flag the injury
    return {"obvious": False, "injured": injured_player}
