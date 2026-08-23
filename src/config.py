"""
Loads settings from the .env file so nothing sensitive is hardcoded.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LeagueConfig:
    name: str
    league_id: int
    year: int


def get_espn_auth() -> tuple[str, str]:
    """Returns (swid, espn_s2) shared across both leagues."""
    swid = os.environ["ESPN_SWID"]
    espn_s2 = os.environ["ESPN_S2"]
    return swid, espn_s2


def get_leagues() -> list[LeagueConfig]:
    return [
        LeagueConfig(
            name=os.environ.get("LEAGUE_1_NAME", "League 1"),
            league_id=int(os.environ["LEAGUE_1_ID"]),
            year=int(os.environ["LEAGUE_1_YEAR"]),
        ),
        LeagueConfig(
            name=os.environ.get("LEAGUE_2_NAME", "League 2"),
            league_id=int(os.environ["LEAGUE_2_ID"]),
            year=int(os.environ["LEAGUE_2_YEAR"]),
        ),
    ]
