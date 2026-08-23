"""
Live draft dashboard. Run with: streamlit run draft_dashboard.py

Shows best-available players, your current roster, and a Claude-powered
advice panel -- meant to be open in a browser tab alongside ESPN's
draft room during your live draft.
"""
import streamlit as st
from src.config import get_leagues, get_espn_auth
from src.connectors import connect
from src.draft_data import (
    find_my_team,
    get_best_available,
    filter_by_position,
    get_my_roster_so_far,
    summarize_roster_needs,
)
from src.draft_advisor import get_draft_advice

st.set_page_config(page_title="Fantasy Draft Dashboard", layout="wide")
st.title("🏈 Draft Dashboard")

leagues_cfg = get_leagues()
league_names = [cfg.name for cfg in leagues_cfg]
selected_name = st.sidebar.selectbox("Which league are you drafting?", league_names)
selected_cfg = next(cfg for cfg in leagues_cfg if cfg.name == selected_name)

if st.sidebar.button("🔄 Refresh draft data"):
    st.cache_resource.clear()
    st.cache_data.clear()


@st.cache_resource
def get_league(league_id, year):
    return connect(selected_cfg)


@st.cache_data(ttl=90)
def cached_best_available(_league, league_id, size=200):
    # league_id is only here so Streamlit's cache key changes when you
    # switch leagues -- _league itself is unhashable so it's ignored for caching
    return get_best_available(_league, size=size)


@st.cache_data(ttl=30)
def cached_my_roster(_league, _my_team, league_id, team_id):
    return get_my_roster_so_far(_league, _my_team)


league = get_league(selected_cfg.league_id, selected_cfg.year)
swid, _ = get_espn_auth()
my_team = find_my_team(league, swid)

if my_team is None:
    st.error(
        "Couldn't auto-detect your team in this league. Double check your "
        "SWID in .env matches the ESPN account you use for this league."
    )
    st.stop()

st.sidebar.success(f"Your team: {my_team.team_name}")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Best Available Players")
    position_filter = st.radio(
        "Position", ["ALL", "QB", "RB", "WR", "TE", "K", "D/ST"], horizontal=True
    )
    best_available = cached_best_available(league, selected_cfg.league_id)
    filtered = filter_by_position(best_available, position_filter)

    st.dataframe(
        [
            {
                "Player": p.name,
                "Pos": p.position,
                "Team": p.proTeam,
                "Proj. Pts": round(p.projected_total_points, 1),
                "% Owned": round(p.percent_owned, 1),
                "Injury": p.injuryStatus if p.injuryStatus != "ACTIVE" else "",
            }
            for p in filtered[:50]
        ],
        use_container_width=True,
        height=600,
    )

with col_right:
    st.subheader("Your Roster So Far")
    my_roster = cached_my_roster(league, my_team, selected_cfg.league_id, my_team.team_id)
    if my_roster:
        for p in my_roster:
            st.write(f"**{p.name}** ({p.position})")
        st.caption("Position counts: " + str(summarize_roster_needs(my_roster)))
    else:
        st.caption("No picks yet.")

    st.divider()
    st.subheader("Ask for advice")
    question = st.text_input(
        "e.g. 'RB or WR here?' or 'Is it too early for a QB?'"
    )
    if st.button("Ask Claude") and question:
        with st.spinner("Thinking..."):
            advice = get_draft_advice(
                question=question,
                best_available=best_available,
                my_roster=my_roster,
                scoring_type=league.settings.scoring_type,
            )
        st.info(advice)
