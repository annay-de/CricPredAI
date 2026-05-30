import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from simulator import load_artifacts, simulate_match, simulate_distribution

st.set_page_config(page_title="CricPredAI V3.0", page_icon="🏏", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.4rem;}
.stButton button {border-radius: 10px; font-weight: 600;}
.big-card {border: 1px solid rgba(255,255,255,.12); border-radius: 16px; padding: 16px; margin: 8px 0;}
.small-muted {opacity: .75; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="Loading trained CricPredAI artefacts...")
def cached_artifacts():
    return load_artifacts()

meta, report, models = cached_artifacts()
players = meta.get("players", [])
venues = ["Unknown"] + meta.get("venues", [])
model_names = list(models.keys())
preferred = ["calibrated_blend", "baseline_prior", "logistic_calibrated", "random_forest", "xgboost", "hist_gradient_boosting", "extra_trees"]
choices = [m for m in preferred if (m in model_names or m=="calibrated_blend")] + [m for m in model_names if m not in preferred]

st.title("CricPredAI V3.0")
st.caption("Ball-by-ball IPL decision-support simulator with playing XI selection, match conditions, model choice, scorecards, rule checks, and optional commentary.")

with st.sidebar:
    st.header("Match setup")
    team1 = st.text_input("Team A name", "Team A")
    team2 = st.text_input("Team B name", "Team B")
    venue = st.selectbox("Stadium / venue", venues, index=0)
    pitch = st.selectbox("Pitch", ["balanced", "batting-friendly", "bowling-friendly"])
    weather = st.selectbox("Weather", ["clear", "humid/dewy", "rain-threat"])
    toss_winner = st.selectbox("Toss winner", [team1, team2])
    toss_decision = st.selectbox("Toss decision", ["bat", "field"])
    model_name = st.selectbox("Model", choices, index=0)
    n_sims = st.slider("Distribution simulations", 10, 200, 60, 10)
    seed = st.number_input("Seed", min_value=0, max_value=999999, value=17, step=1)
    commentary = st.toggle("Optional commentary format", value=False)

st.subheader("Playing XI selection")
col1, col2 = st.columns(2)
with col1:
    xi1 = st.multiselect(f"{team1} playing XI", players, default=players[:11] if len(players)>=11 else players, max_selections=11)
with col2:
    xi2 = st.multiselect(f"{team2} playing XI", players, default=players[11:22] if len(players)>=22 else players[:11], max_selections=11)

if len(xi1) != 11 or len(xi2) != 11:
    st.warning("Select exactly 11 players for both teams before simulating.")

run = st.button("Simulate match", type="primary", disabled=(len(xi1)!=11 or len(xi2)!=11))

if not report.empty:
    with st.expander("Model diagnostics", expanded=False):
        st.dataframe(report.sort_values("log_loss"), use_container_width=True, hide_index=True)
        best = meta.get("best_model_by_log_loss", "not available")
        st.info(f"Best validation model by log loss in the saved report: {best}. The app uses empirical calibration/blending to keep ball-by-ball simulations realistic.")

if run:
    with st.spinner("Simulating match and validating cricket rules..."):
        res = simulate_match(team1, team2, xi1, xi2, models, meta, model_name, venue, pitch, weather, toss_winner, toss_decision, seed=int(seed), commentary=commentary)
        dist = simulate_distribution(n_sims, team1, team2, xi1, xi2, models, meta, model_name, venue, pitch, weather, toss_winner, toss_decision, seed=int(seed)+1000)

    st.success(f"Result: {res['winner']} {res['margin']}")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(res['first']['team'], f"{res['first']['runs']}/{res['first']['wickets']}", res['first']['overs'])
    c2.metric(res['second']['team'], f"{res['second']['runs']}/{res['second']['wickets']}", res['second']['overs'])
    c3.metric("First innings ended", res['first']['end_reason'])
    c4.metric("Second innings ended", res['second']['end_reason'])

    st.subheader("Score progression")
    fig = go.Figure()
    for inn, label in [(res['first'], res['first']['team']), (res['second'], res['second']['team'])]:
        b = inn['ball_by_ball'].copy()
        if len(b):
            b['x'] = np.arange(1, len(b)+1)
            fig.add_trace(go.Scatter(x=b['x'], y=b['score'], mode='lines+markers', name=label))
            wk = b[b['wicket'] == True]
            if len(wk):
                fig.add_trace(go.Scatter(x=wk['x'], y=wk['score'], mode='markers', name=f"{label} wickets", marker=dict(size=11, symbol='x')))
    fig.update_layout(xaxis_title="Delivery row, including extras", yaxis_title="Score", height=430, legend_orientation="h")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Combined scorecard")
    tab1, tab2, tab3, tab4 = st.tabs(["Batting", "Bowling", "Ball-by-ball verification", "Distribution"])
    with tab1:
        st.markdown(f"#### {res['first']['team']} batting")
        st.dataframe(res['first']['batting_card'], use_container_width=True, hide_index=True)
        st.markdown(f"#### {res['second']['team']} batting")
        st.dataframe(res['second']['batting_card'], use_container_width=True, hide_index=True)
        st.markdown("#### Fall of wickets")
        c1,c2 = st.columns(2)
        c1.dataframe(res['first']['fall_of_wickets'], use_container_width=True, hide_index=True)
        c2.dataframe(res['second']['fall_of_wickets'], use_container_width=True, hide_index=True)
    with tab2:
        st.markdown(f"#### {res['first']['team']} innings bowling card")
        st.dataframe(res['first']['bowling_card'], use_container_width=True, hide_index=True)
        st.markdown(f"#### {res['second']['team']} innings bowling card")
        st.dataframe(res['second']['bowling_card'], use_container_width=True, hide_index=True)
    with tab3:
        st.markdown("The table includes extras, legal-ball tracking, wicket probabilities, boundary probabilities, and bowler-selection reasons.")
        st.markdown("#### Rule checks")
        checks = []
        for k,v in res['first']['rules'].items(): checks.append({"innings":res['first']['team'],"rule":k,"passed":v})
        for k,v in res['second']['rules'].items(): checks.append({"innings":res['second']['team'],"rule":k,"passed":v})
        st.dataframe(pd.DataFrame(checks), hide_index=True, use_container_width=True)
        st.markdown(f"#### {res['first']['team']} ball-by-ball")
        cols = ['ball','phase','bowler','batter','outcome','runs','extras','extra_type','wicket','score','wickets','p_wicket','p_boundary','p_extra','bowler_reason']
        if commentary: cols.append('commentary')
        st.dataframe(res['first']['ball_by_ball'][cols], use_container_width=True, hide_index=True)
        st.markdown(f"#### {res['second']['team']} ball-by-ball")
        st.dataframe(res['second']['ball_by_ball'][cols], use_container_width=True, hide_index=True)
    with tab4:
        st.markdown("Multiple simulations estimate uncertainty, not a single deterministic score.")
        st.dataframe(dist.describe(include='all'), use_container_width=True)
        st.bar_chart(dist['winner'].value_counts())
        f = go.Figure()
        f.add_trace(go.Histogram(x=dist['first_runs'], name='First innings runs', opacity=0.65))
        f.add_trace(go.Histogram(x=dist['second_runs'], name='Second innings runs', opacity=0.65))
        f.update_layout(barmode='overlay', height=400, xaxis_title='Runs', yaxis_title='Frequency')
        st.plotly_chart(f, use_container_width=True)
else:
    st.info("Select two playing XIs and click Simulate match.")

