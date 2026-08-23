"""
Thin wrapper around espn_api so the rest of the codebase doesn't need
to know connection details -- just ask for a connected League object.
"""
from __future__ import annotations
from espn_api.football import League
from .config import LeagueConfig, get_espn_auth


def connect(league_cfg: LeagueConfig) -> League:
    swid, espn_s2 = get_espn_auth()
    return League(
        league_id=league_cfg.league_id,
        year=league_cfg.year,
        swid=swid,
        espn_s2=espn_s2,
    )


def connect_all(league_cfgs: list[LeagueConfig]) -> dict[str, League]:
    """Returns {league_name: League object} for every configured league."""
    return {cfg.name: connect(cfg) for cfg in league_cfgs}
