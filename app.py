from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulator import (
    available_profiles,
    load_artifacts,
    simulate_distribution,
    simulate_match,
)

st.set_page_config(
    page_title="CricPred | IPL Simulation Lab",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="collapsed",
)

COLORS = {
    "ink": "#101D2F",
    "muted": "#667386",
    "paper": "#F4F1E8",
    "panel": "#FBF9F3",
    "line": "#D8D2C4",
    "blue": "#174A7E",
    "navy": "#0F2742",
    "copper": "#B45F3D",
    "gold": "#B88A2A",
}

st.markdown(
    f"""
    <style>
    :root {{
        --ink: {COLORS["ink"]};
        --muted: {COLORS["muted"]};
        --paper: {COLORS["paper"]};
        --panel: {COLORS["panel"]};
        --line: {COLORS["line"]};
        --blue: {COLORS["blue"]};
        --navy: {COLORS["navy"]};
        --copper: {COLORS["copper"]};
    }}
    .stApp {{
        background: var(--paper);
        color: var(--ink);
    }}
    header[data-testid="stHeader"],
    [data-testid="stToolbar"] {{
        display: none;
    }}
    [data-testid="stMainBlockContainer"] {{
        max-width: 1260px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }}
    h1, h2, h3 {{
        color: var(--ink);
        letter-spacing: -0.025em;
    }}
    h1 {{
        font-size: clamp(2.2rem, 5vw, 4.6rem);
        line-height: 0.98;
    }}
    .site-head {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        border-bottom: 1px solid var(--line);
        padding: 0.35rem 0 1rem;
        margin-bottom: 0.8rem;
    }}
    .brand {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }}
    .brand-mark {{
        width: 2.35rem;
        height: 2.35rem;
        display: grid;
        place-items: center;
        background: var(--ink);
        color: var(--paper);
        font: 700 0.78rem/1 system-ui, sans-serif;
        letter-spacing: 0.08em;
    }}
    .brand-name {{
        font: 700 1rem/1.1 system-ui, sans-serif;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}
    .brand-sub {{
        color: var(--muted);
        font-size: 0.76rem;
        margin-top: 0.18rem;
    }}
    .coverage {{
        color: var(--muted);
        font-size: 0.78rem;
        text-align: right;
        letter-spacing: 0.02em;
    }}
    .hero {{
        padding: 3.4rem 0 2.7rem;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.7rem;
    }}
    .eyebrow {{
        color: var(--blue);
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }}
    .hero h1 {{
        max-width: 900px;
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        font-weight: 500;
    }}
    .hero-copy {{
        color: var(--muted);
        max-width: 720px;
        margin-top: 1.2rem;
        font-size: 1.03rem;
        line-height: 1.65;
    }}
    .section-head {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid var(--line);
        padding-bottom: 0.7rem;
        margin: 0.5rem 0 1.1rem;
    }}
    .section-head h2 {{
        margin: 0;
        font: 600 1.45rem/1.2 Georgia, "Times New Roman", serif;
    }}
    .section-note {{
        color: var(--muted);
        font-size: 0.8rem;
        text-align: right;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--panel);
        border-color: var(--line);
        border-radius: 2px;
    }}
    div[data-testid="stRadio"] > div {{
        gap: 0.35rem;
    }}
    div[data-testid="stRadio"] label {{
        border: 1px solid var(--line);
        background: var(--panel);
        padding: 0.42rem 0.78rem;
        min-height: 2.35rem;
    }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        border-color: var(--navy);
        background: var(--navy);
        color: white;
    }}
    div[data-testid="stRadio"] label:has(input:checked) p,
    div[data-testid="stRadio"] label:has(input:checked) span {{
        color: white !important;
    }}
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {{
        border-radius: 2px;
        min-height: 2.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }}
    div[data-testid="stButton"] button[kind="primary"] {{
        background: var(--blue);
        border-color: var(--blue);
    }}
    div[data-testid="stMetric"] {{
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 0.9rem 1rem;
    }}
    div[data-testid="stMetricLabel"] {{
        color: var(--muted);
    }}
    .profile-note {{
        border-left: 3px solid var(--blue);
        padding: 0.15rem 0 0.15rem 0.85rem;
        color: var(--muted);
        font-size: 0.85rem;
        line-height: 1.5;
        margin: 0.15rem 0 1rem;
    }}
    .lineup-meta {{
        color: var(--muted);
        font-size: 0.78rem;
        margin-top: -0.45rem;
        margin-bottom: 0.7rem;
    }}
    .result-banner {{
        border-top: 5px solid #4F86BB;
        background: var(--navy);
        color: white;
        padding: 1.65rem 1.8rem;
        margin-bottom: 1rem;
    }}
    .result-kicker {{
        color: #B9D3EC;
        font-size: 0.72rem;
        letter-spacing: 0.13em;
        text-transform: uppercase;
    }}
    .result-title {{
        font: 500 clamp(1.9rem, 4vw, 3.4rem)/1.1 Georgia, "Times New Roman", serif;
        margin-top: 0.35rem;
    }}
    .score-box {{
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 1.15rem 1.2rem;
        min-height: 8.2rem;
    }}
    .score-team {{
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}
    .score-value {{
        color: var(--ink);
        font: 500 2.45rem/1.1 Georgia, "Times New Roman", serif;
        margin-top: 0.35rem;
    }}
    .score-detail {{
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }}
    .innings-heading {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        border-top: 4px solid var(--navy);
        border-bottom: 1px solid var(--line);
        padding: 0.85rem 0 0.7rem;
        margin: 0.35rem 0 0.9rem;
    }}
    .innings-heading h3 {{
        margin: 0;
        font: 600 1.35rem/1.2 Georgia, "Times New Roman", serif;
    }}
    .innings-score {{
        color: var(--blue);
        font-weight: 750;
        white-space: nowrap;
    }}
    .innings-divider {{
        height: 1px;
        background: var(--line);
        margin: 1.8rem 0;
    }}
    .model-card {{
        background: var(--panel);
        border-top: 4px solid var(--navy);
        padding: 1.2rem;
        min-height: 13rem;
    }}
    .model-card h3 {{
        font: 600 1.25rem/1.2 Georgia, "Times New Roman", serif;
        margin: 0.25rem 0 0.65rem;
    }}
    .model-card p {{
        color: var(--muted);
        line-height: 1.55;
        font-size: 0.88rem;
    }}
    .fact-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem 1rem;
        margin-top: 0.8rem;
        font-size: 0.82rem;
    }}
    .fact-grid span:nth-child(odd) {{
        color: var(--muted);
    }}
    .fact-grid span:nth-child(even) {{
        text-align: right;
        font-weight: 700;
    }}
    .support-row {{
        display: grid;
        grid-template-columns: 11rem 1fr;
        gap: 1rem;
        padding: 0.85rem 0;
        border-bottom: 1px solid var(--line);
    }}
    .support-row strong {{
        font-size: 0.84rem;
    }}
    .support-row span {{
        color: var(--muted);
        font-size: 0.84rem;
        line-height: 1.5;
    }}
    .footer {{
        border-top: 1px solid var(--line);
        margin-top: 3rem;
        padding-top: 1.15rem;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        color: var(--muted);
        font-size: 0.78rem;
    }}
    .footer a {{
        color: var(--ink);
        text-decoration: none;
        border-bottom: 1px solid var(--line);
    }}
    [data-testid="stDataFrame"] {{
        border: 1px solid var(--line);
    }}
    @media (max-width: 760px) {{
        .coverage {{ display: none; }}
        .hero {{ padding-top: 2rem; }}
        .section-head {{ display: block; }}
        .section-note {{
            margin-top: 0.35rem;
            text-align: left;
        }}
        div[data-testid="stRadio"] > div {{
            flex-wrap: nowrap;
            gap: 0.25rem;
        }}
        div[data-testid="stRadio"] label {{
            padding: 0.35rem 0.5rem;
        }}
        div[data-testid="stRadio"] label p {{
            font-size: 0.8rem;
        }}
        .support-row {{ grid-template-columns: 1fr; gap: 0.25rem; }}
        .footer {{ display: block; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


PROFILE_LABELS = {
    "modern": "Modern form",
    "lifetime": "Lifetime / legends",
}

PROFILE_DESCRIPTIONS = {
    "modern": (
        "Recent IPL evidence carries more weight through a five-year half-life. "
        "Best for current squads and present-day scoring conditions."
    ),
    "lifetime": (
        "Every IPL delivery carries equal weight. Best for legends, all-time XIs, "
        "and cross-era matchups."
    ),
}

MODEL_LABELS = {
    "xgboost": "XGBoost",
    "calibrated_blend": "Calibrated ensemble",
    "sgd_logistic": "Logistic model",
    "baseline_prior": "Empirical baseline",
}

MODERN_XI_A = [
    "RD Rickelton",
    "RG Sharma",
    "SA Yadav",
    "Tilak Varma",
    "Naman Dhir",
    "HH Pandya",
    "MJ Santner",
    "SN Thakur",
    "TA Boult",
    "JJ Bumrah",
    "AM Ghazanfar",
]

MODERN_XI_B = [
    "Shubman Gill",
    "B Sai Sudharsan",
    "JC Buttler",
    "Washington Sundar",
    "M Shahrukh Khan",
    "R Tewatia",
    "Rashid Khan",
    "JO Holder",
    "K Rabada",
    "Mohammed Siraj",
    "M Prasidh Krishna",
]

LEGENDS_XI_A = [
    "SR Tendulkar",
    "V Sehwag",
    "CH Gayle",
    "AB de Villiers",
    "MS Dhoni",
    "Yuvraj Singh",
    "JH Kallis",
    "Harbhajan Singh",
    "SK Warne",
    "SL Malinga",
    "Z Khan",
]

LEGENDS_XI_B = [
    "AC Gilchrist",
    "BB McCullum",
    "DA Warner",
    "V Kohli",
    "RG Sharma",
    "SK Raina",
    "SR Watson",
    "SP Narine",
    "Rashid Khan",
    "JJ Bumrah",
    "DW Steyn",
]


@st.cache_resource(show_spinner=False)
def cached_artifacts(profile: str):
    return load_artifacts(profile)


def valid_preset(candidates: list[str], players: list[str]) -> list[str]:
    result = [player for player in candidates if player in players]
    return result if len(result) == 11 else []


def profile_presets(profile: str, players: list[str]) -> tuple[list[str], list[str]]:
    if profile == "lifetime":
        first = valid_preset(LEGENDS_XI_A, players)
        second = valid_preset(LEGENDS_XI_B, players)
    else:
        first = valid_preset(MODERN_XI_A, players)
        second = valid_preset(MODERN_XI_B, players)
    if first and second:
        return first, second
    return players[:11], players[11:22]


def model_choices(meta: dict, models: dict) -> list[str]:
    choices = []
    for name in ["xgboost", "calibrated_blend", "sgd_logistic", "baseline_prior"]:
        if (
            name in models
            or name == "baseline_prior"
            or name in meta.get("model_calibration", {})
        ):
            choices.append(name)
    return choices


def lineup_summary(xi: list[str], meta: dict) -> str:
    roles = meta.get("roles", {})
    counts = {"batter": 0, "all-rounder": 0, "bowler": 0}
    for player in xi:
        role = roles.get(player, {}).get("role", "batter")
        counts[role] = counts.get(role, 0) + 1
    bowling_options = sum(
        roles.get(player, {}).get("role") in {"bowler", "all-rounder"}
        for player in xi
    )
    return (
        f"{len(xi)}/11 selected | {counts['batter']} batters | "
        f"{counts['all-rounder']} all-rounders | {counts['bowler']} bowlers | "
        f"{bowling_options} primary bowling options"
    )


def section_header(title: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <h2>{escape(title)}</h2>
            <div class="section-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_box(innings: dict) -> str:
    return f"""
    <div class="score-box">
        <div class="score-team">{escape(innings["team"])}</div>
        <div class="score-value">{innings["runs"]}/{innings["wickets"]}</div>
        <div class="score-detail">{escape(innings["overs"])} overs | {escape(innings["end_reason"])}</div>
    </div>
    """


def score_progression_figure(result: dict) -> go.Figure:
    figure = go.Figure()
    palette = [COLORS["blue"], COLORS["copper"]]
    for index, innings in enumerate([result["first"], result["second"]]):
        deliveries = innings["ball_by_ball"].copy()
        if deliveries.empty:
            continue
        deliveries["overs_axis"] = (
            deliveries["over"] + deliveries["legal_ball_in_over"].clip(lower=0) / 6
        )
        figure.add_trace(
            go.Scatter(
                x=deliveries["overs_axis"],
                y=deliveries["score"],
                mode="lines",
                name=innings["team"],
                line={"color": palette[index], "width": 3},
                hovertemplate="%{x:.1f} ov<br>%{y} runs<extra></extra>",
            )
        )
        wickets = deliveries[deliveries["wicket"].eq(True)]
        if not wickets.empty:
            figure.add_trace(
                go.Scatter(
                    x=wickets["overs_axis"],
                    y=wickets["score"],
                    mode="markers",
                    name=f"{innings['team']} wickets",
                    marker={
                        "color": palette[index],
                        "size": 9,
                        "symbol": "x",
                        "line": {"width": 2},
                    },
                    hovertemplate="%{x:.1f} ov<br>%{y} runs<extra>Wicket</extra>",
                )
            )
    figure.update_layout(
        height=430,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLORS["panel"],
        font={"color": COLORS["ink"], "family": "Arial, sans-serif"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={
            "title": "Overs",
            "range": [0, 20],
            "gridcolor": COLORS["line"],
            "zeroline": False,
        },
        yaxis={"title": "Runs", "gridcolor": COLORS["line"], "zeroline": False},
        hoverlabel={"bgcolor": COLORS["ink"], "font_color": "white"},
    )
    return figure


def probability_figure(distribution: pd.DataFrame, result: dict) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Histogram(
            x=distribution["first_runs"],
            name=result["first"]["team"],
            marker_color=COLORS["blue"],
            opacity=0.78,
        )
    )
    figure.add_trace(
        go.Histogram(
            x=distribution["second_runs"],
            name=result["second"]["team"],
            marker_color=COLORS["copper"],
            opacity=0.68,
        )
    )
    figure.update_layout(
        barmode="overlay",
        height=390,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=COLORS["panel"],
        font={"color": COLORS["ink"], "family": "Arial, sans-serif"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={"title": "Runs", "gridcolor": COLORS["line"], "zeroline": False},
        yaxis={"title": "Simulations", "gridcolor": COLORS["line"], "zeroline": False},
    )
    return figure


def render_header() -> None:
    st.markdown(
        """
        <div class="site-head">
            <div class="brand">
                <div class="brand-mark">CP</div>
                <div>
                    <div class="brand-name">CricPred</div>
                    <div class="brand-sub">IPL simulation laboratory</div>
                </div>
            </div>
            <div class="coverage">
                IPL ball-by-ball archive<br>
                18 Apr 2008 - 1 May 2026
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_match_lab() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Pre-match decision support</div>
            <h1>Build two XIs. Test the matchup, not the mythology.</h1>
            <div class="hero-copy">
                A ball-by-ball IPL simulator trained on 288,051 deliveries.
                Select a data profile, set the batting order through the toss,
                and compare one match with a repeated-match distribution.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_header("Model basis", "Choose how historical evidence should be weighted")
    profile = st.radio(
        "Data profile",
        available_profiles(),
        format_func=lambda value: PROFILE_LABELS.get(value, value.title()),
        horizontal=True,
        label_visibility="collapsed",
        key="profile_selector",
    )
    meta, report, models = cached_artifacts(profile)
    players = meta.get("players", [])
    default_xi_a, default_xi_b = profile_presets(profile, players)
    st.markdown(
        f'<div class="profile-note">{escape(PROFILE_DESCRIPTIONS[profile])}</div>',
        unsafe_allow_html=True,
    )

    controls = st.columns([1.2, 1, 1.25])
    with controls[0]:
        model_name = st.selectbox(
            "Simulation model",
            model_choices(meta, models),
            format_func=lambda value: MODEL_LABELS.get(value, value),
            index=0,
            key=f"model_{profile}",
        )
    with controls[1]:
        venues = meta.get("venues", [])
        venue_index = venues.index("Eden Gardens") if "Eden Gardens" in venues else 0
        venue = st.selectbox(
            "Venue",
            venues,
            index=venue_index,
            key=f"venue_{profile}",
        )
    with controls[2]:
        st.text_input(
            "Data coverage",
            value=f"{meta['n_matches']:,} matches | through {meta['data_end_date']}",
            disabled=True,
        )

    section_header("Playing XIs", "Selection order is the batting order")
    names = st.columns(2)
    with names[0]:
        default_name_a = "Mumbai 2026" if profile == "modern" else "Legends XI"
        team_a = st.text_input("Team A", default_name_a, key=f"team_a_{profile}").strip()
    with names[1]:
        default_name_b = "Gujarat 2026" if profile == "modern" else "All-time XI"
        team_b = st.text_input("Team B", default_name_b, key=f"team_b_{profile}").strip()

    lineups = st.columns(2)
    with lineups[0]:
        xi_a = st.multiselect(
            f"{team_a or 'Team A'} XI",
            players,
            default=default_xi_a,
            max_selections=11,
            key=f"xi_a_{profile}",
        )
        st.markdown(
            f'<div class="lineup-meta">{escape(lineup_summary(xi_a, meta))}</div>',
            unsafe_allow_html=True,
        )
    with lineups[1]:
        xi_b = st.multiselect(
            f"{team_b or 'Team B'} XI",
            players,
            default=default_xi_b,
            max_selections=11,
            key=f"xi_b_{profile}",
        )
        st.markdown(
            f'<div class="lineup-meta">{escape(lineup_summary(xi_b, meta))}</div>',
            unsafe_allow_html=True,
        )

    section_header("Match order", "Toss data determines who bats first")
    match_controls = st.columns([1, 1, 1])
    with match_controls[0]:
        toss_winner = st.selectbox(
            "Toss winner",
            [team_a or "Team A", team_b or "Team B"],
            key=f"toss_winner_{profile}",
        )
    with match_controls[1]:
        toss_decision = st.selectbox(
            "Toss decision",
            ["bat", "field"],
            format_func=lambda value: "Bat first" if value == "bat" else "Field first",
            key=f"toss_decision_{profile}",
        )
    with match_controls[2]:
        simulations = st.slider(
            "Repeated simulations",
            min_value=10,
            max_value=100,
            value=25,
            step=5,
            key=f"simulations_{profile}",
        )

    with st.expander("Reproducibility"):
        seed = st.number_input(
            "Random seed",
            min_value=0,
            max_value=999999,
            value=17,
            step=1,
            key=f"seed_{profile}",
            help="Use the same seed to reproduce the same simulated match and distribution.",
        )

    overlap = sorted(set(xi_a) & set(xi_b))
    problems = []
    if len(xi_a) != 11 or len(xi_b) != 11:
        problems.append("Select exactly 11 players for each team.")
    if overlap:
        problems.append(f"A player cannot represent both teams: {', '.join(overlap)}.")
    if not team_a or not team_b or team_a == team_b:
        problems.append("Use two distinct team names.")
    if problems:
        st.warning(" ".join(problems))

    if st.button(
        "Run match simulation",
        type="primary",
        width="stretch",
        disabled=bool(problems),
    ):
        with st.spinner(
            f"Running one scorecard and {simulations} repeated matches using "
            f"{PROFILE_LABELS[profile].lower()}..."
        ):
            result = simulate_match(
                team_a,
                team_b,
                xi_a,
                xi_b,
                models,
                meta,
                model_name,
                venue,
                "data-driven",
                "data-driven",
                toss_winner,
                toss_decision,
                seed=int(seed),
                commentary=False,
            )
            distribution = simulate_distribution(
                simulations,
                team_a,
                team_b,
                xi_a,
                xi_b,
                models,
                meta,
                model_name,
                venue,
                "data-driven",
                "data-driven",
                toss_winner,
                toss_decision,
                seed=int(seed) + 1000,
            )
        st.session_state["latest_run"] = {
            "result": result,
            "distribution": distribution,
            "config": {
                "profile": profile,
                "model": model_name,
                "venue": venue,
                "simulations": simulations,
                "seed": int(seed),
                "toss_winner": toss_winner,
                "toss_decision": toss_decision,
            },
        }
        st.session_state["pending_nav"] = "Results"
        st.rerun()

    if not report.empty:
        best = report.sort_values("log_loss").iloc[0]
        st.caption(
            f"Current profile validation: {MODEL_LABELS.get(str(best['model']), best['model'])} "
            f"log loss {best['log_loss']:.4f}."
        )


def render_results() -> None:
    run = st.session_state.get("latest_run")
    if not run:
        st.markdown(
            """
            <div class="hero">
                <div class="eyebrow">Results</div>
                <h1>No simulation has been run yet.</h1>
                <div class="hero-copy">
                    Build two playing XIs in Match Lab, choose the evidence profile,
                    and run the matchup. The scorecard and repeated-match distribution
                    will remain available here while you explore the site.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    result = run["result"]
    distribution = run["distribution"]
    config = run["config"]
    profile_label = PROFILE_LABELS.get(config["profile"], config["profile"])
    model_label = MODEL_LABELS.get(config["model"], config["model"])
    st.markdown(
        f"""
        <div class="result-banner">
            <div class="result-kicker">{escape(profile_label)} | {escape(model_label)} | {escape(config["venue"])}</div>
            <div class="result-title">{escape(result["winner"])} {escape(result["margin"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scores = st.columns(2)
    with scores[0]:
        st.markdown(score_box(result["first"]), unsafe_allow_html=True)
    with scores[1]:
        st.markdown(score_box(result["second"]), unsafe_allow_html=True)

    winner_rates = distribution["winner"].value_counts(normalize=True)
    metrics = st.columns(4)
    metrics[0].metric(
        f"{result['first']['team']} win probability",
        f"{100 * winner_rates.get(result['first']['team'], 0):.0f}%",
    )
    metrics[1].metric(
        f"{result['second']['team']} win probability",
        f"{100 * winner_rates.get(result['second']['team'], 0):.0f}%",
    )
    metrics[2].metric(
        "Average first innings",
        f"{distribution['first_runs'].mean():.0f}",
    )
    metrics[3].metric(
        "Average chase",
        f"{distribution['second_runs'].mean():.0f}",
    )

    section_header("Score progression", "Wicket markers are shown as crosses")
    st.plotly_chart(
        score_progression_figure(result),
        width="stretch",
        config={"displayModeBar": False},
    )

    scorecard_tab, probability_tab, delivery_tab = st.tabs(
        ["Full scorecard", "Probability", "Delivery log"]
    )
    with scorecard_tab:
        for index, innings in enumerate([result["first"], result["second"]]):
            st.markdown(
                f"""
                <div class="innings-heading">
                    <h3>{index + 1}. {escape(innings["team"])}</h3>
                    <div class="innings-score">
                        {innings["runs"]}/{innings["wickets"]} in {escape(innings["overs"])} overs
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("#### Batting")
            st.dataframe(
                innings["batting_card"],
                width="stretch",
                hide_index=True,
            )
            st.markdown("#### Bowling")
            st.dataframe(
                innings["bowling_card"],
                width="stretch",
                hide_index=True,
            )
            if not innings["fall_of_wickets"].empty:
                st.markdown("#### Fall of wickets")
                st.dataframe(
                    innings["fall_of_wickets"],
                    width="stretch",
                    hide_index=True,
                )
            if index == 0:
                st.markdown('<div class="innings-divider"></div>', unsafe_allow_html=True)

    with probability_tab:
        st.plotly_chart(
            probability_figure(distribution, result),
            width="stretch",
            config={"displayModeBar": False},
        )
        probability_table = (
            distribution["winner"]
            .value_counts()
            .rename_axis("Outcome")
            .reset_index(name="Simulations")
        )
        probability_table["Probability"] = (
            probability_table["Simulations"] / len(distribution)
        )
        st.dataframe(
            probability_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Probability": st.column_config.ProgressColumn(
                    "Probability",
                    format="%.1%%",
                    min_value=0,
                    max_value=1,
                )
            },
        )

    with delivery_tab:
        innings_choice = st.radio(
            "Innings",
            [result["first"]["team"], result["second"]["team"]],
            horizontal=True,
            key="delivery_innings",
        )
        innings = (
            result["first"]
            if innings_choice == result["first"]["team"]
            else result["second"]
        )
        rule_columns = st.columns(3)
        rule_labels = {
            "no_bowler_over_4": "Four-over limit",
            "legal_balls_max_120": "120 legal balls",
            "wickets_max_10": "Ten-wicket limit",
        }
        for column, (rule, passed) in zip(
            rule_columns, innings["rules"].items(), strict=True
        ):
            column.metric(rule_labels.get(rule, rule), "Passed" if passed else "Failed")
        log_columns = [
            "ball",
            "phase",
            "bowler",
            "batter",
            "outcome",
            "runs",
            "extras",
            "wicket",
            "score",
            "wickets",
            "p_wicket",
            "p_boundary",
            "p_extra",
        ]
        st.dataframe(
            innings["ball_by_ball"][log_columns],
            width="stretch",
            hide_index=True,
        )
        csv_bytes = innings["ball_by_ball"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download delivery log",
            data=csv_bytes,
            file_name=f"{innings['team'].replace(' ', '_').lower()}_deliveries.csv",
            mime="text/csv",
        )


def render_model_notes() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Model notes</div>
            <h1>Two histories, one simulation engine.</h1>
            <div class="hero-copy">
                Modern mode emphasizes current IPL form. Lifetime mode keeps the
                full career record intact for legends and cross-era comparisons.
                Both use the same leakage-safe delivery state and chase features.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    profile_columns = st.columns(2)
    profile_data = {}
    for column, profile in zip(profile_columns, ["modern", "lifetime"], strict=True):
        meta, report, _ = cached_artifacts(profile)
        best = report.sort_values("log_loss").iloc[0]
        profile_data[profile] = (meta, report)
        with column:
            st.markdown(
                f"""
                <div class="model-card">
                    <div class="eyebrow">{escape(PROFILE_LABELS[profile])}</div>
                    <h3>{escape(meta["profile_description"])}</h3>
                    <p>{escape(PROFILE_DESCRIPTIONS[profile])}</p>
                    <div class="fact-grid">
                        <span>Best model</span><span>{escape(MODEL_LABELS.get(str(best["model"]), str(best["model"])))}</span>
                        <span>Test log loss</span><span>{best["log_loss"]:.4f}</span>
                        <span>Matches</span><span>{meta["n_matches"]:,}</span>
                        <span>Venues</span><span>{len(meta["venues"])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    section_header("Validation report", "Lower log loss is better")
    reports = []
    for profile, (_, report) in profile_data.items():
        frame = report.copy()
        frame.insert(0, "Profile", PROFILE_LABELS[profile])
        frame["model"] = frame["model"].map(
            lambda value: MODEL_LABELS.get(str(value), str(value))
        )
        reports.append(frame)
    combined_report = pd.concat(reports, ignore_index=True)
    st.dataframe(
        combined_report.rename(
            columns={
                "model": "Model",
                "log_loss": "Log loss",
                "accuracy": "Accuracy",
                "balanced_accuracy": "Balanced accuracy",
                "macro_f1": "Macro F1",
            }
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "Log loss": st.column_config.NumberColumn(format="%.4f"),
            "Accuracy": st.column_config.NumberColumn(format="%.3f"),
            "Balanced accuracy": st.column_config.NumberColumn(format="%.3f"),
            "Macro F1": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    section_header("Inputs that change the simulation", "Only supported controls are exposed")
    supported = [
        (
            "Playing XI",
            "Player and bowler histories alter delivery probabilities, batting order, and bowling selection.",
        ),
        (
            "Evidence profile",
            "Modern form applies recency weighting; lifetime mode uses the complete equal-weight record.",
        ),
        (
            "Venue",
            "Canonical venue-phase distributions and the trained venue feature influence outcomes.",
        ),
        (
            "Toss and batting order",
            "The toss determines innings order, and the model sees the recorded toss decision.",
        ),
        (
            "Match state",
            "Score, wickets, balls remaining, target, required rate, batter state, and phase update every delivery.",
        ),
        (
            "Model",
            "XGBoost, logistic, calibrated ensemble, and the empirical baseline use distinct probability paths.",
        ),
    ]
    for name, description in supported:
        st.markdown(
            f'<div class="support-row"><strong>{escape(name)}</strong><span>{escape(description)}</span></div>',
            unsafe_allow_html=True,
        )

    section_header("Intentionally excluded", "No unsupported theatre")
    excluded = [
        (
            "Weather",
            "The source dataset has no reliable delivery-level weather observations, so weather is not modeled.",
        ),
        (
            "Pitch labels",
            "There is no defensible batting-friendly or bowling-friendly label in the training data.",
        ),
        (
            "Manual probability boosts",
            "The interface does not apply hand-written boundary, wicket, dew, or rain multipliers.",
        ),
    ]
    for name, description in excluded:
        st.markdown(
            f'<div class="support-row"><strong>{escape(name)}</strong><span>{escape(description)}</span></div>',
            unsafe_allow_html=True,
        )

    modern_meta = profile_data["modern"][0]
    st.caption(
        f"Training archive: {modern_meta['n_rows']:,} deliveries across "
        f"{modern_meta['n_matches']:,} IPL matches, "
        f"{modern_meta['data_start_date']} to {modern_meta['data_end_date']}. "
        "Venue names are canonicalized before training and inference."
    )


render_header()

if "pending_nav" in st.session_state:
    st.session_state["primary_nav"] = st.session_state.pop("pending_nav")

navigation = st.radio(
    "Primary navigation",
    ["Match Lab", "Results", "Model Notes"],
    horizontal=True,
    label_visibility="collapsed",
    key="primary_nav",
)

if navigation == "Match Lab":
    render_match_lab()
elif navigation == "Results":
    render_results()
else:
    render_model_notes()

st.markdown(
    """
    <div class="footer">
        <div>CricPred | IPL simulation laboratory</div>
        <div>
            Built by Annay De |
            <a href="https://www.linkedin.com/in/annayde/" target="_blank" rel="noopener noreferrer">LinkedIn</a> |
            <a href="https://x.com/AnnayDe_" target="_blank" rel="noopener noreferrer">X</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
