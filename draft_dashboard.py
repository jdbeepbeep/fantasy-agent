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
from src.consensus import fetch_consensus_rankings, get_consensus_rank

st.set_page_config(page_title="Jamie's Casualty List", layout="wide", page_icon="🏈")

# Streamlit's built-in theme only tints a couple of widgets -- doesn't
# actually color the page. Forcing 49ers red/gold directly via CSS instead.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');

h1, h2, h3 {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.04em;
    color: #AA0000 !important;
}
h1 { text-shadow: 0 0 18px rgba(170, 0, 0, 0.4); }

hr {
    border: none; height: 3px; margin: 1.5rem 0;
    background: repeating-linear-gradient(
        90deg, #B3995D 0px, #B3995D 14px, transparent 14px, transparent 24px
    );
}

.stButton>button {
    background-color: #AA0000 !important;
    color: #F5F1E8 !important;
    border: 1px solid #B3995D !important;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #B3995D !important;
    color: #0A0A0A !important;
    border: 1px solid #AA0000 !important;
}

[data-testid="stSidebar"] {
    border-right: 2px solid #AA0000;
}
</style>
""", unsafe_allow_html=True)

st.title("🏈 JAMIE'S CASUALTY LIST")
st.caption("Unbothered & Unbeaten.")

leagues_cfg = get_leagues()
league_names = [cfg.name for cfg in leagues_cfg]
selected_name = st.sidebar.selectbox("Select case file", league_names)
selected_cfg = next(cfg for cfg in leagues_cfg if cfg.name == selected_name)

if st.sidebar.button("🔄 Check the morgue"):
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
        "Can't find your squad in this league. Check that your SWID in .env "
        "matches the ESPN account you use here."
    )
    st.stop()

st.sidebar.success(f"Your squad: {my_team.team_name}")
st.sidebar.caption("Est. time of death: TBD")

st.sidebar.divider()
if "consensus_rankings" not in st.session_state:
    st.session_state.consensus_rankings = None

if st.sidebar.button("⚰️ Read the Death Report"):
    with st.spinner("Getting a second opinion on the body (genuinely takes ~5 min, sit tight)..."):
        try:
            st.session_state.consensus_rankings = fetch_consensus_rankings(league.settings.scoring_type)
        except Exception as e:
            st.sidebar.error(f"The coroner's out to lunch: {e}")
            st.session_state.consensus_rankings = None
    if st.session_state.consensus_rankings:
        st.sidebar.success(f"{len(st.session_state.consensus_rankings)} bodies identified.")
    elif st.session_state.consensus_rankings is not None:
        st.sidebar.error("Couldn't read the report. Falling back to ESPN's numbers.")

consensus_rankings = st.session_state.consensus_rankings

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("STILL BREATHING")
    sort_options = ["ESPN Projected Points"]
    if consensus_rankings:
        sort_options.insert(0, "Expert Consensus Rank")
    sort_by = st.radio("Sort by", sort_options, horizontal=True)
    position_filter = st.radio(
        "Position", ["ALL", "QB", "RB", "WR", "TE", "K", "D/ST"], horizontal=True
    )
    best_available = cached_best_available(league, selected_cfg.league_id)
    filtered = filter_by_position(best_available, position_filter)

    if sort_by == "Expert Consensus Rank" and consensus_rankings:
        # Ranked players first (lowest rank number = best), unranked
        # players (not in the top-N consensus list) pushed to the end,
        # sorted among themselves by ESPN's own projection as a fallback.
        def sort_key(p):
            rank = get_consensus_rank(p.name, consensus_rankings)
            return (0, rank) if rank is not None else (1, -p.projected_total_points)
        filtered = sorted(filtered, key=sort_key)
    else:
        filtered = sorted(filtered, key=lambda p: p.projected_total_points, reverse=True)

    rows = []
    for p in filtered[:50]:
        row = {
            "Player": p.name,
            "Pos": p.position,
            "Team": p.proTeam,
            "Proj. Pts": round(p.projected_total_points, 1),
            "% Owned": round(p.percent_owned, 1),
            "Injury": p.injuryStatus if p.injuryStatus != "ACTIVE" else "",
        }
        if consensus_rankings:
            rank = get_consensus_rank(p.name, consensus_rankings)
            row["Consensus Rank"] = rank if rank is not None else "-"
        rows.append(row)

    st.dataframe(rows, use_container_width=True, height=600)
    if not consensus_rankings:
        st.caption("Hit '⚰️ Read the Death Report' in the sidebar for a second opinion.")

with col_right:
    st.subheader("CONFIRMED CASUALTIES")
    my_roster = cached_my_roster(league, my_team, selected_cfg.league_id, my_team.team_id)
    if my_roster:
        for p in my_roster:
            st.write(f"**{p.name}** ({p.position})")
        st.caption("Position counts: " + str(summarize_roster_needs(my_roster)))
    else:
        st.caption("No bodies yet. Give it time.")

    st.divider()
    st.subheader("ASK THE MEDICAL EXAMINER")
    question = st.text_input(
        "e.g. 'RB or WR here?' or 'Is it too early for a QB?'"
    )
    if st.button("Get the diagnosis") and question:
        with st.spinner("Preparing the verdict..."):
            advice = get_draft_advice(
                question=question,
                best_available=best_available,
                my_roster=my_roster,
                scoring_type=league.settings.scoring_type,
                consensus_rankings=consensus_rankings,
            )
        st.info(advice)
