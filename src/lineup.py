"""
Computes the highest-projected starting lineup a roster could field,
compares it to what's actually set, and flags meaningful differences.

This is READ-ONLY -- espn-api doesn't support actually setting lineups,
so this only recommends via text. You still make the swap in the app.
"""
from __future__ import annotations
from espn_api.football.team import Team

# Slot names that aren't "starting" positions -- skip these when building
# the set of slots that need to be filled.
NON_STARTING_SLOTS = {"BE", "IR"}

# Which real positions are eligible for which flex-style slot. A player's
# `eligibleSlots` list (from espn-api) already encodes this per-player,
# so we mostly lean on that rather than hardcoding -- this is a fallback
# label map only.
FLEX_LIKE_SLOTS = {"RB/WR", "WR/TE", "RB/WR/TE", "OP"}

# Suggestions below this many projected points aren't worth a text --
# keeps alerts to genuinely meaningful swaps, not 0.3-point noise.
MEANINGFUL_MARGIN = 2.0


def weekly_points(player, week: int, projected: bool = True) -> float:
    """
    Player.projected_total_points is ESPN's SEASON total, not this
    week's number -- using it directly would give wrong lineup advice.
    This pulls the specific week's projection instead, falling back to
    the season figure only if week-specific data isn't available yet
    (e.g. very early preseason).
    """
    key = "projected_points" if projected else "points"
    week_stats = getattr(player, "stats", {}).get(week, {})
    if key in week_stats:
        return week_stats[key]
    return player.projected_total_points if projected else player.total_points


def get_starting_slots(league) -> dict:
    """
    Returns {slot_name: count} for actual starting slots only
    (bench/IR excluded), e.g. {'QB': 1, 'RB': 2, 'WR': 2, 'FLEX': 1, ...}
    """
    counts = league.settings.position_slot_counts
    return {slot: n for slot, n in counts.items() if slot not in NON_STARTING_SLOTS and n > 0}


def compute_optimal_lineup(roster: list, slot_counts: dict, week: int) -> dict:
    """
    Greedy assignment: sort all rostered players by THIS WEEK's projected
    points (highest first), and slot each one into the best still-open
    slot they're eligible for. This isn't a provably perfect bipartite
    match in every edge case, but it's the standard, reliable heuristic
    for fantasy lineup optimization and matches how most tools do it.

    `roster` should be a full team lineup list (starters + bench) from
    league.box_scores(), not team.roster -- the box score version is
    correctly scoped to this week's stats.

    Returns {slot_name: BoxPlayer} for every filled slot.
    """
    open_slots = {slot: count for slot, count in slot_counts.items()}
    lineup = {}

    # Exclude anyone already ruled OUT -- no point "optimally" starting
    # someone who won't play. (Questionable/Doubtful are left in --
    # that's a judgment call for the user, not an automatic exclusion.)
    available = [p for p in roster if getattr(p, "injuryStatus", "ACTIVE") != "OUT"]
    available.sort(key=lambda p: weekly_points(p, week), reverse=True)

    for player in available:
        eligible = set(getattr(player, "eligibleSlots", [player.position]))
        # Try the player's exact position slot first, then any flex slot
        # they qualify for, in the order those slots appear in settings.
        candidate_slots = [s for s in open_slots if s in eligible and open_slots[s] > 0]
        if not candidate_slots:
            continue
        # Prefer a non-flex, position-specific slot over a flex slot,
        # so flex spots stay open for players who need them more.
        candidate_slots.sort(key=lambda s: s in FLEX_LIKE_SLOTS or s == "FLEX")
        chosen = candidate_slots[0]
        slot_key = f"{chosen}_{sum(1 for k in lineup if k.startswith(chosen))}"
        lineup[slot_key] = player
        open_slots[chosen] -= 1

    return lineup


def get_current_starters(lineup: list) -> list:
    """Filters a BoxScore lineup down to just the currently-started players."""
    return [p for p in lineup if p.slot_position not in NON_STARTING_SLOTS]


def suggest_lineup_changes(optimal_lineup: dict, current_starters: list, week: int, margin: float = MEANINGFUL_MARGIN) -> list:
    """
    Compares the optimal lineup against what's currently started.
    Returns a list of {start, sit, gain} dicts for swaps worth making
    (gain >= margin projected points, this week specifically). Pass a
    lower margin to also surface genuinely-close calls worth a second
    opinion, even if not clear-cut enough for an automatic suggestion.
    """
    optimal_ids = {p.playerId for p in optimal_lineup.values()}
    current_ids = {p.playerId for p in current_starters}

    should_be_in = [p for p in optimal_lineup.values() if p.playerId not in current_ids]
    should_be_out = [p for p in current_starters if p.playerId not in optimal_ids]

    should_be_in.sort(key=lambda p: weekly_points(p, week), reverse=True)
    should_be_out.sort(key=lambda p: weekly_points(p, week))

    suggestions = []
    for bench_player, bench_starter in zip(should_be_in, should_be_out):
        gain = weekly_points(bench_player, week) - weekly_points(bench_starter, week)
        if gain >= margin:
            suggestions.append({
                "start": bench_player,
                "sit": bench_starter,
                "gain": gain,
            })
    return suggestions
