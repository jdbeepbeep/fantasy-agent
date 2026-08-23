"""
Run this first, before anything else: python test_connection.py

Confirms your credentials and league IDs actually work by connecting
to both leagues and printing basic info. If this succeeds, everything
downstream (rosters, matchups, waivers) will work too.
"""
from src.config import get_leagues
from src.connectors import connect_all


def main():
    leagues_cfg = get_leagues()
    print(f"Attempting to connect to {len(leagues_cfg)} league(s)...\n")

    leagues = connect_all(leagues_cfg)

    for name, league in leagues.items():
        print(f"--- {name} ---")
        print(f"  League name (per ESPN): {league.settings.name}")
        print(f"  Scoring type: {league.settings.scoring_type}")
        print(f"  Teams: {len(league.teams)}")
        for team in league.teams:
            owner_names = [
                o.get("firstName", "") + " " + o.get("lastName", "")
                for o in team.owners
            ] or ["Unknown"]
            print(f"    - {team.team_name} (owner: {', '.join(owner_names)})")
        print()

    print("Connection test passed. Both leagues are reachable.")


if __name__ == "__main__":
    main()
