"""
Run this a few times a day (GitHub Actions handles this automatically)
to check both leagues for: starter injuries (yours and your current
opponent's), obvious waiver suggestions, and lineup optimization --
comparing your currently-set lineup against the highest-projected one
your roster could field, plus the same check on your opponent's lineup
for informational awareness.

Usage: python3 monitor.py
"""
import json
import os
from datetime import date, timedelta

from src.config import get_leagues, get_espn_auth
from src.connectors import connect
from src.draft_data import find_my_team
from src.monitoring import (
    get_current_matchup,
    get_my_lineup_and_opponent,
    check_lineup_injuries,
    suggest_replacement,
)
from src.lineup import get_starting_slots, compute_optimal_lineup, get_current_starters, suggest_lineup_changes, MEANINGFUL_MARGIN
from src.messages import format_injury_alert, format_suggestion, format_lineup_suggestions, issue_key
from src.notifier import send_text
from src.research import get_injury_context, get_close_call_analysis
from src.weather import get_game_weather, is_notable_weather

STATE_FILE = "data/state.json"
SKILL_POSITIONS = {"QB", "RB", "WR", "TE", "K"}


def next_sunday_iso() -> str:
    """
    Approximates game day as the upcoming Sunday, since most games are
    played then. Thu/Mon games will be off by a day or two -- close
    enough for a multi-day-out weather forecast to still be useful.
    """
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7  # Sunday = 6
    return (today + timedelta(days=days_ahead)).isoformat()


def load_state() -> set:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE) as f:
        return set(json.load(f))


def save_state(seen: set) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def main():
    seen = load_state()
    new_alerts = []
    swid, _ = get_espn_auth()

    for league_cfg in get_leagues():
        league = connect(league_cfg)
        my_team = find_my_team(league, swid)
        if my_team is None:
            print(f"Could not find your team in {league_cfg.name}, skipping.")
            continue

        matchup = get_current_matchup(league, my_team)
        if matchup is None:
            print(f"{league_cfg.name}: no matchup yet (draft hasn't happened, or you're on a bye). Skipping.")
            continue

        my_lineup, opponent_team, opp_lineup = get_my_lineup_and_opponent(matchup, my_team)
        week = league.current_week
        slot_counts = get_starting_slots(league)

        # --- My starters ---
        for player in check_lineup_injuries(my_lineup):
            key = issue_key(league_cfg.name, player.playerId, player.injuryStatus)
            if key in seen:
                continue
            seen.add(key)
            new_alerts.append(format_injury_alert(league_cfg.name, player, is_mine=True, team_label=""))

            if player.injuryStatus in ("OUT", "DOUBTFUL"):
                context = get_injury_context(player.name, player.proTeam, player.injuryStatus)
                if context:
                    new_alerts.append(f"  Latest: {context}")

                suggestion = suggest_replacement(league, player, my_team.roster)
                if suggestion["obvious"]:
                    new_alerts.append(format_suggestion(league_cfg.name, suggestion))

        # --- Opponent's starters (informational only, no suggestions) ---
        for player in check_lineup_injuries(opp_lineup):
            key = issue_key(league_cfg.name, player.playerId, player.injuryStatus)
            if key in seen:
                continue
            seen.add(key)
            new_alerts.append(
                format_injury_alert(league_cfg.name, player, is_mine=False, team_label=opponent_team.team_name)
            )

        # --- My lineup optimization ---
        my_optimal = compute_optimal_lineup(my_lineup, slot_counts, week)
        my_current = get_current_starters(my_lineup)
        my_swaps = suggest_lineup_changes(my_optimal, my_current, week)
        if my_swaps:
            # Dedup key based on WHICH swaps, so we only re-alert if the
            # recommendation actually changes (new injury, updated projection)
            swap_key = tuple(sorted(f"{s['start'].playerId}>{s['sit'].playerId}" for s in my_swaps))
            key = issue_key(league_cfg.name, hash(swap_key) % 10_000_000, f"lineup_w{week}")
            if key not in seen:
                seen.add(key)
                new_alerts.append(format_lineup_suggestions(league_cfg.name, my_swaps, is_mine=True))

        # --- Opponent's lineup (informational -- can't act on it, just awareness) ---
        opp_optimal = compute_optimal_lineup(opp_lineup, slot_counts, week)
        opp_current = get_current_starters(opp_lineup)
        opp_swaps = suggest_lineup_changes(opp_optimal, opp_current, week)
        if opp_swaps:
            swap_key = tuple(sorted(f"{s['start'].playerId}>{s['sit'].playerId}" for s in opp_swaps))
            key = issue_key(league_cfg.name, hash(swap_key) % 10_000_000, f"opp_lineup_w{week}")
            if key not in seen:
                seen.add(key)
                new_alerts.append(format_lineup_suggestions(league_cfg.name, opp_swaps, is_mine=False))

        # --- Close lineup calls (below the auto-suggest threshold, but
        # close enough that a second opinion from current expert
        # analysis could help) -- only the single closest call, to
        # keep web-search API usage reasonable ---
        near_misses = suggest_lineup_changes(my_optimal, my_current, week, margin=0.1)
        genuinely_close = [s for s in near_misses if s["gain"] < MEANINGFUL_MARGIN]
        if genuinely_close:
            closest = min(genuinely_close, key=lambda s: s["gain"])
            key = issue_key(league_cfg.name, hash(f"{closest['start'].playerId}v{closest['sit'].playerId}") % 10_000_000, f"closecall_w{week}")
            if key not in seen:
                seen.add(key)
                analysis = get_close_call_analysis(
                    closest["start"].name, closest["sit"].name, closest["start"].position, week
                )
                if analysis:
                    new_alerts.append(
                        f"[{league_cfg.name}] Close call: {closest['start'].name} vs {closest['sit'].name}. {analysis}"
                    )

        # --- Weather check for my currently-started skill players ---
        game_date = next_sunday_iso()
        checked_teams = set()
        for player in my_current:
            if player.position not in SKILL_POSITIONS or player.proTeam in checked_teams:
                continue
            checked_teams.add(player.proTeam)
            weather = get_game_weather(player.proTeam, game_date)
            if is_notable_weather(weather):
                key = issue_key(league_cfg.name, hash(player.proTeam) % 10_000_000, f"weather_w{week}")
                if key not in seen:
                    seen.add(key)
                    new_alerts.append(
                        f"[{league_cfg.name}] Weather alert for {player.proTeam} game: "
                        f"{weather['wind_mph']:.0f} mph wind, {weather['precip_pct']:.0f}% precip chance. "
                        f"May affect {player.name} and others on that team."
                    )

    if new_alerts:
        message = "\n".join(new_alerts)
        print("Sending alert:\n" + message)
        send_text(message)
    else:
        print("No new injury news since last check.")

    save_state(seen)


if __name__ == "__main__":
    main()
