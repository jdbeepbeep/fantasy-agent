"""
Run this a few times a day (manually for now, GitHub Actions later) to
check both leagues for starter injuries -- yours and your current
opponent's -- and draft waiver suggestions when there's an obvious one.

Usage: python3 monitor.py
"""
import json
import os

from src.config import get_leagues, get_espn_auth
from src.connectors import connect
from src.draft_data import find_my_team
from src.monitoring import (
    get_current_matchup,
    get_my_lineup_and_opponent,
    check_lineup_injuries,
    suggest_replacement,
)
from src.messages import format_injury_alert, format_suggestion, issue_key
from src.notifier import send_text

STATE_FILE = "data/state.json"


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

        # --- My starters ---
        for player in check_lineup_injuries(my_lineup):
            key = issue_key(league_cfg.name, player.playerId, player.injuryStatus)
            if key in seen:
                continue
            seen.add(key)
            new_alerts.append(format_injury_alert(league_cfg.name, player, is_mine=True, team_label=""))

            if player.injuryStatus in ("OUT", "DOUBTFUL"):
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

    if new_alerts:
        message = "\n".join(new_alerts)
        print("Sending alert:\n" + message)
        send_text(message)
    else:
        print("No new injury news since last check.")

    save_state(seen)


if __name__ == "__main__":
    main()
