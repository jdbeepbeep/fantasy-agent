"""
Checks game-day weather for outdoor stadiums using Open-Meteo, a free
public weather API that requires no API key or signup.

Only relevant for outdoor venues -- domes and retractable-roof stadiums
(when closed, which is the default assumption) are skipped entirely.
"""
from __future__ import annotations
import requests

# (latitude, longitude, is_dome) for each team's home stadium.
# Retractable-roof stadiums (e.g. ATL, ARI, DAL, HOU, IND, LV, LAR) are
# marked as domes since they're closed in bad weather more often than not.
STADIUMS = {
    "ARI": (33.5276, -112.2626, True),
    "ATL": (33.7554, -84.4008, True),
    "BAL": (39.2780, -76.6227, False),
    "BUF": (42.7738, -78.7870, False),
    "CAR": (35.2258, -80.8528, False),
    "CHI": (41.8623, -87.6167, False),
    "CIN": (39.0954, -84.5160, False),
    "CLE": (41.5061, -81.6995, False),
    "DAL": (32.7473, -97.0945, True),
    "DEN": (39.7439, -105.0201, False),
    "DET": (42.3400, -83.0456, True),
    "GB": (44.5013, -88.0622, False),
    "HOU": (29.6847, -95.4107, True),
    "IND": (39.7601, -86.1639, True),
    "JAX": (30.3239, -81.6373, False),
    "KC": (39.0489, -94.4839, False),
    "LV": (36.0909, -115.1833, True),
    "LAC": (33.9535, -118.3392, True),
    "LAR": (33.9535, -118.3392, True),
    "MIA": (25.9580, -80.2389, False),
    "MIN": (44.9736, -93.2575, True),
    "NE": (42.0909, -71.2643, False),
    "NO": (29.9509, -90.0815, True),
    "NYG": (40.8135, -74.0745, False),
    "NYJ": (40.8135, -74.0745, False),
    "PHI": (39.9008, -75.1675, False),
    "PIT": (40.4468, -80.0158, False),
    "SF": (37.4032, -121.9698, False),
    "SEA": (47.5952, -122.3316, False),
    "TB": (27.9759, -82.5033, False),
    "TEN": (36.1665, -86.7713, False),
    "WAS": (38.9078, -76.8645, False),
}

# Rough thresholds for "this could actually affect the game"
WIND_THRESHOLD_MPH = 20
PRECIP_THRESHOLD_PCT = 60


def get_game_weather(team_abbr: str, game_date: str) -> dict | None:
    """
    Returns {'wind_mph': ..., 'precip_pct': ..., 'condition': ...} for
    an outdoor game, or None if the team's stadium is a dome, the team
    isn't recognized, or the forecast isn't available yet (Open-Meteo
    only forecasts about 16 days out).
    """
    if team_abbr not in STADIUMS:
        return None
    lat, lon, is_dome = STADIUMS[team_abbr]
    if is_dome:
        return None

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "windspeed_10m_max,precipitation_probability_max,weathercode",
                "temperature_unit": "fahrenheit",
                "windspeed_unit": "mph",
                "start_date": game_date,
                "end_date": game_date,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()["daily"]
        return {
            "wind_mph": data["windspeed_10m_max"][0],
            "precip_pct": data["precipitation_probability_max"][0],
        }
    except (requests.RequestException, KeyError, IndexError):
        # Forecast not available yet (too far out) or API hiccup --
        # fail quietly, weather is a nice-to-have, not critical
        return None


def is_notable_weather(weather: dict) -> bool:
    if weather is None:
        return False
    return (
        weather["wind_mph"] >= WIND_THRESHOLD_MPH
        or weather["precip_pct"] >= PRECIP_THRESHOLD_PCT
    )
