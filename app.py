from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from replay import build_payload, build_replay_html
from simulator import (
    available_profiles,
    load_artifacts,
    representative_seed,
    simulate_distribution,
    simulate_match,
)
from particles import particles_html
from scout import (
    ScoutError,
    career_summary,
    fetch_t20_career,
    load_roster,
    merge_into_meta,
    profile_from_career,
    profile_from_statsguru,
    save_roster,
    search_players,
)
from theme import APP_CSS, PALETTE

st.set_page_config(
    page_title="CricPredAI — IPL Simulation Desk",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(APP_CSS, unsafe_allow_html=True)

MONO_FONT = "JetBrains Mono, ui-monospace, monospace"

PROFILE_LABELS = {
    "modern": "Modern form",
    "lifetime": "Lifetime / legends",
    "world": "World / all leagues",
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
    "world": (
        "Delivery-level evidence from every ingested league — IPL, PSL, BBL, CPL, "
        "T20 internationals and more — with equal weight. Train it with "
        "cricsheet_ingest.py; the Scout uses it automatically once present."
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


# ---------------------------------------------------------------------------
# small render helpers
# ---------------------------------------------------------------------------

def section(number: str, title: str, note: str = "") -> None:
    note_html = f'<div class="note">{escape(note)}</div>' if note else ""
    st.markdown(
        f'<div class="sect"><span class="no">{escape(number)}</span>'
        f"<h2>{escape(title)}</h2>{note_html}</div>",
        unsafe_allow_html=True,
    )


def render_sheet(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No rows to display.")
        return
    st.markdown(
        '<div class="sheetwrap">'
        + frame.to_html(index=False, escape=True, classes="sheet", border=0)
        + "</div>",
        unsafe_allow_html=True,
    )


def chart_layout(figure: go.Figure, height: int = 420) -> go.Figure:
    figure.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 24, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": PALETTE["muted"], "family": MONO_FONT, "size": 10},
        legend={
            "orientation": "h",
            "y": 1.1,
            "x": 0,
            "font": {"color": PALETTE["ink"]},
        },
        hoverlabel={
            "bgcolor": "#000000",
            "bordercolor": PALETTE["line"],
            "font": {"color": PALETTE["ink"], "family": MONO_FONT},
        },
    )
    figure.update_xaxes(
        gridcolor=PALETTE["line2"],
        zeroline=False,
        linecolor=PALETTE["line"],
        tickcolor=PALETTE["line"],
    )
    figure.update_yaxes(
        gridcolor=PALETTE["line2"],
        zeroline=False,
        linecolor=PALETTE["line"],
        tickcolor=PALETTE["line"],
    )
    return figure


# ---------------------------------------------------------------------------
# team-building state helpers
# ---------------------------------------------------------------------------

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


def ordered_lineup_editor(
    label: str,
    players: list[str],
    defaults: list[str],
    key: str,
) -> list[str]:
    default_players = (defaults + [""] * 11)[:11]
    lineup = st.data_editor(
        pd.DataFrame(
            {
                "No.": [str(position) for position in range(1, 12)],
                "Player": default_players,
            }
        ),
        key=key,
        width="stretch",
        height=425,
        hide_index=True,
        num_rows="fixed",
        disabled=["No."],
        column_config={
            "No.": st.column_config.TextColumn(width="small"),
            "Player": st.column_config.SelectboxColumn(
                label,
                options=players,
                required=True,
                width="large",
            ),
        },
    )
    return [
        str(player).strip()
        for player in lineup["Player"].tolist()
        if pd.notna(player) and str(player).strip()
    ]


def recommended_bowlers(xi: list[str], meta: dict) -> list[str]:
    roles = meta.get("roles", {})
    ranked = sorted(
        dict.fromkeys(xi),
        key=lambda player: (
            roles.get(player, {}).get("role") in {"bowler", "all-rounder"},
            float(roles.get(player, {}).get("effective_bowl_balls", 0.0)),
            float(roles.get(player, {}).get("bowling_score", 0.0)),
        ),
        reverse=True,
    )
    primary = [
        player
        for player in ranked
        if roles.get(player, {}).get("role") in {"bowler", "all-rounder"}
    ]
    selected = primary[:6]
    for player in ranked:
        if player not in selected:
            selected.append(player)
        if len(selected) >= min(6, len(xi)):
            break
    return selected


def saved_team_store(profile: str) -> dict:
    root = st.session_state.setdefault("saved_teams", {})
    return root.setdefault(profile, {})


def lineup_default(profile: str, side: str, fallback: list[str]) -> list[str]:
    return st.session_state.get(f"lineup_default_{side}_{profile}", fallback)


def team_name_default(profile: str, side: str, fallback: str) -> str:
    return st.session_state.get(f"team_name_default_{side}_{profile}", fallback)


def team_name_key(profile: str, side: str) -> str:
    version = st.session_state.get(f"team_name_version_{side}_{profile}", 0)
    return f"team_{side}_{profile}_{version}"


def bowling_default(
    profile: str,
    side: str,
    xi: list[str],
    fallback: list[str],
) -> list[str]:
    saved = st.session_state.get(f"bowling_default_{side}_{profile}", fallback)
    filtered = [player for player in saved if player in xi]
    return filtered if filtered else fallback


def editor_key(profile: str, side: str) -> str:
    version = st.session_state.get(f"lineup_version_{side}_{profile}", 0)
    return f"xi_{side}_order_{profile}_{version}"


def bowler_key(profile: str, side: str) -> str:
    version = st.session_state.get(f"bowling_version_{side}_{profile}", 0)
    return f"bowling_{side}_{profile}_{version}"


def load_saved_team(profile: str, side: str, team_name: str) -> None:
    team = saved_team_store(profile).get(team_name)
    if not team:
        return
    st.session_state[f"team_name_default_{side}_{profile}"] = team_name
    st.session_state[f"lineup_default_{side}_{profile}"] = team["xi"]
    st.session_state[f"bowling_default_{side}_{profile}"] = team["bowlers"]
    for slot in ["team_name_version", "lineup_version", "bowling_version"]:
        st.session_state[f"{slot}_{side}_{profile}"] = (
            st.session_state.get(f"{slot}_{side}_{profile}", 0) + 1
        )
    st.rerun()


def save_team(profile: str, team_name: str, xi: list[str], bowlers: list[str]) -> None:
    if not team_name or len(xi) != 11:
        return
    saved_team_store(profile)[team_name] = {
        "xi": list(xi),
        "bowlers": [player for player in bowlers if player in xi],
    }


def lineup_summary(
    xi: list[str],
    meta: dict,
    bowling_options: list[str] | None = None,
) -> str:
    roles = meta.get("roles", {})
    counts = {"batter": 0, "all-rounder": 0, "bowler": 0}
    for player in xi:
        role = roles.get(player, {}).get("role", "batter")
        counts[role] = counts.get(role, 0) + 1
    bowling_count = (
        len(bowling_options)
        if bowling_options is not None
        else sum(
            roles.get(player, {}).get("role") in {"bowler", "all-rounder"}
            for player in xi
        )
    )
    return (
        f"<b>{len(xi)}/11</b> picked · {counts['batter']} bat · "
        f"{counts['all-rounder']} all-round · {counts['bowler']} bowl · "
        f"<b>{bowling_count}</b> bowling options"
    )


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.96
    proportion = successes / total
    denominator = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / denominator
    half_width = (
        z
        * np.sqrt(
            proportion * (1 - proportion) / total
            + z**2 / (4 * total**2)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------

def manhattan_figure(result: dict) -> go.Figure:
    figure = go.Figure()
    palette = [PALETTE["blue"], PALETTE["mist"]]
    offsets = [-0.19, 0.19]
    for index, innings in enumerate([result["first"], result["second"]]):
        overs = innings.get("over_summary", pd.DataFrame())
        if overs is None or overs.empty:
            continue
        x = overs["over"] + offsets[index]
        figure.add_trace(
            go.Bar(
                x=x,
                y=overs["runs"],
                width=0.36,
                name=innings["team"],
                marker={"color": palette[index], "line": {"width": 0}},
                customdata=np.column_stack(
                    [overs["bowler"], overs["wickets"], overs["score"]]
                ),
                hovertemplate=(
                    "Over %{x:.0f} — %{y} runs<br>"
                    "%{customdata[0]}<br>"
                    "wickets: %{customdata[1]} · score %{customdata[2]}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
        wicket_overs = overs[overs["wickets"] > 0]
        if not wicket_overs.empty:
            figure.add_trace(
                go.Scatter(
                    x=wicket_overs["over"] + offsets[index],
                    y=wicket_overs["runs"] + 1.5,
                    mode="markers",
                    marker={"color": PALETTE["red"], "size": 7, "symbol": "circle"},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    figure.update_layout(barmode="overlay", bargap=0)
    figure.update_xaxes(title="Over", dtick=2)
    figure.update_yaxes(title="Runs off the over")
    return chart_layout(figure, height=330)


def probability_figure(distribution: pd.DataFrame, result: dict) -> go.Figure:
    figure = go.Figure()
    palette = {
        result["first"]["team"]: PALETTE["blue"],
        result["second"]["team"]: PALETTE["mist"],
        "Tie": PALETTE["muted"],
    }
    for winner, group in distribution.groupby("winner", sort=False):
        figure.add_trace(
            go.Scatter(
                x=group["first_runs"],
                y=group["second_runs"],
                mode="markers",
                name=str(winner),
                marker={
                    "color": palette.get(str(winner), PALETTE["muted"]),
                    "size": 8,
                    "opacity": 0.85,
                    "symbol": "circle",
                    "line": {"color": "rgba(0,0,0,0.7)", "width": 1},
                },
                customdata=np.column_stack([group["sim"], group["seed"]]),
                hovertemplate=(
                    "Simulation %{customdata[0]} · seed %{customdata[1]}<br>"
                    f"{result['first']['team']}: %{{x}}<br>"
                    f"{result['second']['team']}: %{{y}}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
    score_min = int(
        min(distribution["first_runs"].min(), distribution["second_runs"].min())
    )
    score_max = int(
        max(distribution["first_runs"].max(), distribution["second_runs"].max())
    )
    padding = max(5, int((score_max - score_min) * 0.06))
    lower = max(0, score_min - padding)
    upper = score_max + padding
    figure.add_trace(
        go.Scatter(
            x=[lower, upper],
            y=[lower, upper],
            mode="lines",
            name="Scores level",
            line={"color": PALETTE["dim"], "width": 1, "dash": "dash"},
            hoverinfo="skip",
        )
    )
    figure.update_xaxes(
        title=f"{result['first']['team']} runs (batting first)",
        range=[lower, upper],
    )
    figure.update_yaxes(
        title=f"{result['second']['team']} runs (chasing)",
        range=[lower, upper],
    )
    return chart_layout(figure, height=460)


# ---------------------------------------------------------------------------
# page chrome
# ---------------------------------------------------------------------------

def render_masthead() -> None:
    st.markdown(
        '<div class="masthead">'
        '<div class="mh-brand">'
        '<span class="mh-dot" aria-hidden="true"></span>'
        '<span class="mh-name">CricPred <span>AI</span></span>'
        "</div>"
        '<div class="mh-right"><b>288,051</b> deliveries · calibrated archive · 2008 – 2026</div>'
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# match lab
# ---------------------------------------------------------------------------

def render_match_lab() -> None:
    hero_cols = st.columns([1.02, 0.98])
    with hero_cols[0]:
        st.markdown(
            '<div class="hero">'
            '<div class="eyebrow">Role-aware · ball-by-ball · 2008–2026</div>'
            '<div class="h1">Every ball, priced.</div>'
            '<div class="copy">A ball-by-ball probabilistic engine trained on every IPL '
            "delivery ever bowled. Set the batting order, nominate the attack, choose "
            "the ground — then watch one match play out, and see the full distribution "
            "of ways it could have gone.</div>"
            '<div class="herostats">'
            '<div class="hs"><b>288,051</b><span>deliveries</span></div>'
            '<div class="hs"><b>1,212</b><span>matches</span></div>'
            '<div class="hs"><b>794</b><span>players</span></div>'
            '<div class="hs"><b>37</b><span>venues</span></div>'
            "</div></div>",
            unsafe_allow_html=True,
        )
    with hero_cols[1]:
        components.html(particles_html(), height=620, scrolling=False)

    section("01", "Evidence", "How should history be weighted?")
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
        f'<div class="fieldnote">{escape(PROFILE_DESCRIPTIONS[profile])}</div>',
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
        venue = st.selectbox("Venue", venues, index=venue_index, key=f"venue_{profile}")
    with controls[2]:
        st.text_input(
            "Data coverage",
            value=f"{meta['n_matches']:,} matches · through {meta['data_end_date']}",
            disabled=True,
        )

    saved_teams = saved_team_store(profile)
    with st.expander("Team locker — reload a saved XI", expanded=bool(saved_teams)):
        st.caption(
            "Saved teams live only in this browser session. Use them to reload "
            "a batting order and bowling pool without searching player by player."
        )
        saved_message = st.session_state.pop(f"saved_team_message_{profile}", None)
        if saved_message:
            st.success(saved_message)
        saved_options = [""] + sorted(saved_teams)
        load_cols = st.columns([1, 0.55, 1, 0.55])
        with load_cols[0]:
            load_a = st.selectbox("Load into Team A", saved_options, key=f"load_a_{profile}")
        with load_cols[1]:
            if st.button("Load A", disabled=not load_a, key=f"load_a_button_{profile}", width="stretch"):
                load_saved_team(profile, "a", load_a)
        with load_cols[2]:
            load_b = st.selectbox("Load into Team B", saved_options, key=f"load_b_{profile}")
        with load_cols[3]:
            if st.button("Load B", disabled=not load_b, key=f"load_b_button_{profile}", width="stretch"):
                load_saved_team(profile, "b", load_b)

    section("02", "The elevens", "Batting order is followed exactly — pick with intent")
    names = st.columns(2)
    with names[0]:
        default_name_a = "Mumbai 2026" if profile == "modern" else "Legends XI"
        team_a = st.text_input(
            "Team A",
            team_name_default(profile, "a", default_name_a),
            key=team_name_key(profile, "a"),
        ).strip()
    with names[1]:
        default_name_b = "Gujarat 2026" if profile == "modern" else "All-time XI"
        team_b = st.text_input(
            "Team B",
            team_name_default(profile, "b", default_name_b),
            key=team_name_key(profile, "b"),
        ).strip()

    lineups = st.columns(2)
    with lineups[0]:
        st.markdown(f"#### {escape(team_a or 'Team A')} — batting order")
        default_xi_a = lineup_default(profile, "a", default_xi_a)
        xi_a = ordered_lineup_editor(
            "Player", players, default_xi_a, key=editor_key(profile, "a")
        )
    with lineups[1]:
        st.markdown(f"#### {escape(team_b or 'Team B')} — batting order")
        default_xi_b = lineup_default(profile, "b", default_xi_b)
        xi_b = ordered_lineup_editor(
            "Player", players, default_xi_b, key=editor_key(profile, "b")
        )

    bowling_columns = st.columns(2)
    with bowling_columns[0]:
        recommended_a = recommended_bowlers(xi_a, meta)
        bowling_a = st.multiselect(
            f"{team_a or 'Team A'} bowling options",
            list(dict.fromkeys(xi_a)),
            default=bowling_default(profile, "a", xi_a, recommended_a),
            key=bowler_key(profile, "a"),
            help=(
                "Select at least five. Historical powerplay, middle-over, and "
                "death-over records determine when these players are used."
            ),
        )
        st.markdown(
            f'<div class="lineup-meta">{lineup_summary(xi_a, meta, bowling_a)}</div>',
            unsafe_allow_html=True,
        )
    with bowling_columns[1]:
        recommended_b = recommended_bowlers(xi_b, meta)
        bowling_b = st.multiselect(
            f"{team_b or 'Team B'} bowling options",
            list(dict.fromkeys(xi_b)),
            default=bowling_default(profile, "b", xi_b, recommended_b),
            key=bowler_key(profile, "b"),
            help=(
                "Only nominated players can bowl. The simulator respects the "
                "four-over limit and does not use the same bowler in consecutive overs."
            ),
        )
        st.markdown(
            f'<div class="lineup-meta">{lineup_summary(xi_b, meta, bowling_b)}</div>',
            unsafe_allow_html=True,
        )

    save_cols = st.columns(2)
    team_a_can_save = len(xi_a) == 11 and len(set(xi_a)) == 11 and len(bowling_a) >= 5
    team_b_can_save = len(xi_b) == 11 and len(set(xi_b)) == 11 and len(bowling_b) >= 5
    with save_cols[0]:
        if st.button(
            f"Save {team_a or 'Team A'} to locker",
            disabled=not team_a_can_save,
            key=f"save_a_{profile}",
            width="stretch",
        ):
            save_team(profile, team_a or "Team A", xi_a, bowling_a)
            st.session_state[f"saved_team_message_{profile}"] = (
                f"Saved {team_a or 'Team A'} for this session."
            )
            st.rerun()
    with save_cols[1]:
        if st.button(
            f"Save {team_b or 'Team B'} to locker",
            disabled=not team_b_can_save,
            key=f"save_b_{profile}",
            width="stretch",
        ):
            save_team(profile, team_b or "Team B", xi_b, bowling_b)
            st.session_state[f"saved_team_message_{profile}"] = (
                f"Saved {team_b or 'Team B'} for this session."
            )
            st.rerun()

    section("03", "Conditions", "The toss decides who bats under the lights first")
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
            value=50,
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
        problems.append("Fill all 11 batting positions for each team.")
    if len(set(xi_a)) != len(xi_a) or len(set(xi_b)) != len(xi_b):
        problems.append("A player can appear only once in a batting order.")
    if overlap:
        problems.append(f"A player cannot represent both teams: {', '.join(overlap)}.")
    if len(bowling_a) < 5 or len(bowling_b) < 5:
        problems.append("Nominate at least five bowling options for each team.")
    if not team_a or not team_b or team_a == team_b:
        problems.append("Use two distinct team names.")
    if problems:
        st.warning(" ".join(problems))

    section("04", "Bowl the first ball")
    if st.button(
        "Simulate the match",
        type="primary",
        width="stretch",
        disabled=bool(problems),
    ):
        with st.spinner(
            f"Bowling {simulations} full matches ball by ball using "
            f"{PROFILE_LABELS[profile].lower()} evidence..."
        ):
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
                bowlers1=bowling_a,
                bowlers2=bowling_b,
            )
            scorecard_seed = representative_seed(distribution)
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
                seed=scorecard_seed,
                commentary=False,
                bowlers1=bowling_a,
                bowlers2=bowling_b,
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
                "scorecard_seed": scorecard_seed,
                "toss_winner": toss_winner,
                "toss_decision": toss_decision,
                "bowling_a": bowling_a,
                "bowling_b": bowling_b,
                "xi": {team_a: xi_a, team_b: xi_b},
            },
        }
        st.session_state["pending_nav"] = "Match Day"
        st.rerun()

    if not report.empty:
        best = report.sort_values("log_loss").iloc[0]
        st.caption(
            f"Current profile validation: {MODEL_LABELS.get(str(best['model']), best['model'])} "
            f"log loss {best['log_loss']:.4f}."
        )


# ---------------------------------------------------------------------------
# match day (results)
# ---------------------------------------------------------------------------

def render_results() -> None:
    run = st.session_state.get("latest_run")
    if not run:
        st.markdown(
            '<div class="hero">'
            '<div class="eyebrow">Match day · no simulation loaded</div>'
            '<div class="h1" style="font-size:clamp(44px,5.4vw,78px);letter-spacing:-0.04em">The ground is ready.<br>Nobody is batting yet.</div>'
            '<div class="copy">Build two elevens in the Match Lab, pick your ground '
            "and your evidence profile, and simulate the game. It replays here ball "
            "by ball — scorecard, worm, commentary, and the full distribution of "
            "repeated matches.</div></div>",
            unsafe_allow_html=True,
        )
        return

    render_run(run)


def render_run(run: dict, key_prefix: str = "", section_start: int = 1) -> None:
    result = run["result"]
    distribution = run["distribution"]
    config = run["config"]
    profile_label = PROFILE_LABELS.get(config["profile"], config["profile"])
    model_label = MODEL_LABELS.get(config["model"], config["model"])
    s1, s2 = f"{section_start:02d}", f"{section_start + 1:02d}"

    section(s1, "The broadcast", "Press play — or scrub straight to the result")
    payload = build_payload(result, config.get("xi", {}), config["venue"])
    components.html(build_replay_html(payload), height=680, scrolling=False)
    st.caption(
        f"{profile_label} · {model_label} · {config['venue']} · representative "
        f"scorecard (seed {config.get('scorecard_seed')}), chosen from the middle "
        "of the most common outcome across the repeated runs."
    )

    section(s2, "The verdict", f"{config['simulations']} matches, same teams, same night")
    winner_rates = distribution["winner"].value_counts(normalize=True)
    team_first = result["first"]["team"]
    team_second = result["second"]["team"]
    p_first = float(winner_rates.get(team_first, 0.0))
    p_second = float(winner_rates.get(team_second, 0.0))
    p_tie = max(0.0, 1.0 - p_first - p_second)
    favourite = team_first if p_first >= p_second else team_second
    win_verb = "win" if result["winner"] != "Tie" else ""
    tie_label = (
        f"<span>tie {100 * p_tie:.0f}%</span>" if p_tie >= 0.005 else ""
    )
    verdict_html = (
        '<div class="verdict">'
        '<div><div class="vk">This scorecard</div>'
        f'<div class="vh"><em>{escape(result["winner"])}</em> {win_verb} {escape(result["margin"])}</div></div>'
        '<div style="margin-left:auto;text-align:right">'
        f'<div class="vk">P(win) across {len(distribution)} simulations</div>'
        f'<div class="vp"><small>{escape(favourite)}</small>{100 * max(p_first, p_second):.1f}%</div></div>'
        "</div>"
        '<div class="tug"><div class="tugbar">'
        f'<div class="a" style="width:{100 * p_first:.1f}%"></div>'
        f'<div class="t" style="width:{100 * p_tie:.1f}%"></div>'
        f'<div class="b" style="width:{100 * p_second:.1f}%"></div>'
        "</div>"
        '<div class="tuglbl">'
        f"<span><b>{escape(team_first)}</b> {100 * p_first:.0f}%</span>"
        f"{tie_label}"
        f"<span><b>{escape(team_second)}</b> {100 * p_second:.0f}%</span>"
        "</div></div>"
    )
    st.markdown(verdict_html, unsafe_allow_html=True)

    metrics = st.columns(4)
    metrics[0].metric(
        f"{team_first} first-innings avg",
        f"{distribution['first_runs'].mean():.0f}",
    )
    metrics[1].metric(
        f"{team_second} chase avg",
        f"{distribution['second_runs'].mean():.0f}",
    )
    interval = wilson_interval(
        int(round(max(p_first, p_second) * len(distribution))), len(distribution)
    )
    metrics[2].metric(
        f"{favourite} 95% interval",
        f"{100 * interval[0]:.0f}–{100 * interval[1]:.0f}%",
    )
    metrics[3].metric(
        "Chases completed",
        f"{int((distribution['winner'] == team_second).sum())}/{len(distribution)}",
    )

    scorecard_tab, distribution_tab, delivery_tab = st.tabs(
        ["Scorecard", "Distribution", "Delivery log"]
    )

    with scorecard_tab:
        st.plotly_chart(
            manhattan_figure(result),
            width="stretch",
            config={"displayModeBar": False},
        )
        for index, innings in enumerate([result["first"], result["second"]]):
            st.markdown(
                f'<div class="inn-head"><h3><span class="n">{"First" if index == 0 else "Second"} innings</span> '
                f"— {escape(innings['team'])}</h3>"
                f'<div class="sc"><b>{innings["runs"]}/{innings["wickets"]}</b> '
                f"({escape(innings['overs'])} ov · {escape(innings['end_reason'])})</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown("#### Batting")
            render_sheet(innings["batting_card"])
            st.markdown("#### Bowling")
            if innings.get("bowling_options"):
                st.caption(
                    "Eligible options: " + ", ".join(map(str, innings["bowling_options"]))
                )
            render_sheet(innings["bowling_card"])
            if not innings["fall_of_wickets"].empty:
                st.markdown("#### Fall of wickets")
                render_sheet(innings["fall_of_wickets"])

    with distribution_tab:
        st.markdown("#### Paired simulation outcomes")
        st.caption(
            "Each square is one complete match. Above the dashed line the chase "
            f"succeeded ({team_second}); below it, {team_first} defended. The pairing "
            "preserves which two scores belonged to the same simulation."
        )
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
        probability_table["95% interval"] = [
            (
                lambda interval: f"{100 * interval[0]:.0f}% – {100 * interval[1]:.0f}%"
            )(wilson_interval(int(count), len(distribution)))
            for count in probability_table["Simulations"]
        ]
        probability_display = probability_table.copy()
        probability_display["Probability"] = probability_display["Probability"].map(
            lambda value: f"{100 * value:.1f}%"
        )
        render_sheet(probability_display)
        if len(distribution) < 50:
            st.warning(
                f"Only {len(distribution)} repeated matches were run. Treat these "
                "probabilities as a rough sample; use at least 50 simulations "
                "before comparing team strength."
            )

    with delivery_tab:
        innings_choice = st.radio(
            "Innings",
            [result["first"]["team"], result["second"]["team"]],
            horizontal=True,
            key=f"{key_prefix}delivery_innings",
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
            "dismissal_kind",
            "dismissal",
            "fielder",
            "score",
            "wickets",
            "p_wicket",
            "p_boundary",
            "p_extra",
        ]
        render_sheet(innings["ball_by_ball"][log_columns])
        csv_bytes = innings["ball_by_ball"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download delivery log",
            data=csv_bytes,
            file_name=f"{innings['team'].replace(' ', '_').lower()}_deliveries.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# model notes
# ---------------------------------------------------------------------------

def render_model_notes() -> None:
    st.markdown(
        '<div class="hero">'
        '<div class="eyebrow">Under the hood · two evidence profiles</div>'
        '<div class="h1" style="font-size:clamp(44px,5.4vw,78px);letter-spacing:-0.04em">One engine,<br>every era.</div>'
        '<div class="copy">Modern mode emphasises current IPL form through recency '
        "weighting. Lifetime mode keeps the full career record intact for legends "
        "and cross-era matchups. Both share the same leakage-safe delivery state "
        "and chase features.</div></div>",
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
                <div class="mcard">
                    <div class="mk">{escape(PROFILE_LABELS[profile])}</div>
                    <h3>{escape(meta["profile_description"])}</h3>
                    <p>{escape(PROFILE_DESCRIPTIONS[profile])}</p>
                    <div class="factgrid">
                        <span>Best model</span><span>{escape(MODEL_LABELS.get(str(best["model"]), str(best["model"])))}</span>
                        <span>Test log loss</span><span>{best["log_loss"]:.4f}</span>
                        <span>Matches</span><span>{meta["n_matches"]:,}</span>
                        <span>Venues</span><span>{len(meta["venues"])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    section("01", "Validation report", "Lower log loss is better")
    reports = []
    for profile, (_, report) in profile_data.items():
        frame = report.copy()
        frame.insert(0, "Profile", PROFILE_LABELS[profile])
        frame["model"] = frame["model"].map(
            lambda value: MODEL_LABELS.get(str(value), str(value))
        )
        reports.append(frame)
    combined_report = pd.concat(reports, ignore_index=True)
    report_display = combined_report.rename(
        columns={
            "model": "Model",
            "log_loss": "Log loss",
            "accuracy": "Accuracy",
            "balanced_accuracy": "Balanced accuracy",
            "macro_f1": "Macro F1",
        }
    )
    for column, places in {
        "Log loss": 4,
        "Accuracy": 3,
        "Balanced accuracy": 3,
        "Macro F1": 3,
    }.items():
        if column in report_display:
            report_display[column] = report_display[column].map(
                lambda value, places=places: f"{float(value):.{places}f}"
            )
    render_sheet(report_display)

    section("02", "What moves the simulation", "Only supported controls are exposed")
    supported = [
        (
            "Batting order",
            "The submitted order is followed exactly. Bayesian-smoothed historical position performance adjusts each batter conservatively.",
        ),
        (
            "Bowling options",
            "Only user-nominated bowlers are eligible. Historical powerplay, middle-over, and death-over records guide over allocation.",
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

    section("03", "Deliberately excluded")
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
            "No weather, dew, or pitch multipliers are applied. Matchup and chase calibration is versioned with the model artifacts and release-tested.",
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



# ---------------------------------------------------------------------------
# the scout — universal players, separate from the IPL pipeline
# ---------------------------------------------------------------------------

def scout_roster() -> dict:
    if "scout_roster" not in st.session_state:
        st.session_state["scout_roster"] = load_roster()
    return st.session_state["scout_roster"]


def sign_scout_player(name: str, profile: dict, career: dict | None, source: str) -> None:
    roster = scout_roster()
    roster[name] = {"profile": profile, "career": career or {}, "source": source}
    save_roster(roster)
    st.session_state["scout_signed_message"] = f"{name} signed to the scouted pool."


BOWLER_TYPE_LABELS = {"pace": "Pace", "spin": "Spin", "none": "Doesn't bowl"}


def scout_profile_controls(prefix: str) -> tuple[int, str, float]:
    columns = st.columns([1, 1.4, 1.4])
    with columns[0]:
        position = st.number_input(
            "Preferred position", min_value=1, max_value=11, value=4,
            key=f"{prefix}_pos",
        )
    with columns[1]:
        bowler_type = st.radio(
            "Bowler type", ["pace", "spin", "none"],
            format_func=lambda v: BOWLER_TYPE_LABELS[v],
            horizontal=True, index=2, key=f"{prefix}_type",
        )
    with columns[2]:
        trust = st.slider(
            "Evidence trust", min_value=0.1, max_value=1.0, value=0.5, step=0.05,
            key=f"{prefix}_trust",
            help=(
                "How much the career record counts against IPL-grade evidence. "
                "Lower trust shrinks the player harder toward the league average."
            ),
        )
    return int(position), bowler_type, float(trust)


def render_scout() -> None:
    st.markdown(
        '<div class="hero">'
        '<div class="eyebrow">The Scout · any player with a public record</div>'
        '<div class="h1" style="font-size:clamp(44px,5.4vw,78px);letter-spacing:-0.04em">'
        "Anyone who ever<br>played the game.</div>"
        '<div class="copy">Search a name, pull the career T20 record, and the '
        "Scout converts it into a calibrated engine profile using the same "
        "Bayesian shrinkage the IPL pipeline trains with. Scouted players can "
        "face anyone — including players they never actually met. The IPL "
        "archive itself is never modified.</div></div>",
        unsafe_allow_html=True,
    )

    scout_profile = "world" if "world" in available_profiles() else "modern"
    meta, _, models = cached_artifacts(scout_profile)
    roster = scout_roster()

    signed_message = st.session_state.pop("scout_signed_message", None)
    if signed_message:
        st.success(signed_message)

    section("01", "Find a player", "ESPNcricinfo search · Statsguru career record")
    search_columns = st.columns([2, 1])
    with search_columns[0]:
        query = st.text_input("Player name", key="sc_query", placeholder="e.g. Babar Azam, Jos Buttler, Rachin Ravindra")
    with search_columns[1]:
        st.markdown("<div style='height:29px'></div>", unsafe_allow_html=True)
        if st.button("Search", key="sc_search", width="stretch") and query:
            try:
                st.session_state["sc_results"] = search_players(query)
                st.session_state.pop("sc_career", None)
            except ScoutError as exc:
                st.session_state.pop("sc_results", None)
                st.warning(str(exc))

    results = st.session_state.get("sc_results") or []
    if results:
        labels = {
            f"{r['name']}" + (f" — {r['country']}" if r.get("country") else ""): r
            for r in results
        }
        pick_columns = st.columns([2, 1])
        with pick_columns[0]:
            chosen_label = st.selectbox("Search results", list(labels), key="sc_pick")
        with pick_columns[1]:
            st.markdown("<div style='height:29px'></div>", unsafe_allow_html=True)
            if st.button("Fetch T20 record", key="sc_fetch", width="stretch"):
                chosen = labels[chosen_label]
                try:
                    with st.spinner("Reading Statsguru career record..."):
                        st.session_state["sc_career"] = fetch_t20_career(chosen["id"])
                    st.session_state["sc_career_name"] = chosen["name"]
                except ScoutError as exc:
                    st.session_state.pop("sc_career", None)
                    st.warning(str(exc))

    career = st.session_state.get("sc_career")
    if career:
        career_name = st.session_state.get("sc_career_name", "Player")
        st.caption(f"{career_name}: {career_summary(career)}")
        position, bowler_type, trust = scout_profile_controls("sc_fetched")
        if st.button(f"Sign {career_name} to the pool", key="sc_sign"):
            profile = profile_from_statsguru(
                name=career_name, meta=meta, career=career,
                preferred_position=position, bowler_type=bowler_type, trust=trust,
            )
            sign_scout_player(career_name, profile, career, "espncricinfo")
            st.session_state.pop("sc_career", None)
            st.rerun()

    with st.expander("Add a player manually — when the scrape can't reach them"):
        manual_name = st.text_input("Name", key="scm_name")
        stat_columns = st.columns(4)
        with stat_columns[0]:
            m_innings = st.number_input("Bat innings", 0, 1000, 0, key="scm_inns")
        with stat_columns[1]:
            m_runs = st.number_input("Runs", 0, 30000, 0, key="scm_runs")
        with stat_columns[2]:
            m_balls = st.number_input("Balls faced", 0, 30000, 0, key="scm_bf")
        with stat_columns[3]:
            m_outs = st.number_input("Dismissals", 0, 1000, 0, key="scm_outs")
        bowl_columns = st.columns(3)
        with bowl_columns[0]:
            m_bballs = st.number_input("Balls bowled", 0, 30000, 0, key="scm_bb")
        with bowl_columns[1]:
            m_bruns = st.number_input("Runs conceded", 0, 40000, 0, key="scm_br")
        with bowl_columns[2]:
            m_wkts = st.number_input("Wickets", 0, 1000, 0, key="scm_bw")
        m_position, m_type, m_trust = scout_profile_controls("sc_manual")
        can_sign = bool(manual_name.strip()) and (m_balls > 0 or m_bballs > 0)
        if st.button("Sign manual player", key="scm_sign", disabled=not can_sign):
            profile = profile_from_career(
                name=manual_name.strip(), meta=meta,
                bat_innings=m_innings, bat_runs=m_runs, bat_balls=m_balls, bat_outs=m_outs,
                bowl_balls=m_bballs, bowl_runs=m_bruns, bowl_wickets=m_wkts,
                preferred_position=m_position, bowler_type=m_type, trust=m_trust,
            )
            sign_scout_player(manual_name.strip(), profile, None, "manual")
            st.rerun()

    if roster:
        section("02", "The signed", f"{len(roster)} scouted — usable below alongside the full IPL pool")
        for player_name in sorted(roster):
            profile = roster[player_name]["profile"]
            row = st.columns([2.4, 3, 0.8])
            row[0].markdown(f"#### {escape(player_name)}")
            row[1].caption(
                f"{profile['role']} · bat {profile['bat_runs_per_ball']:.3f} rpb · "
                f"out {profile['dismissal_rate']:.4f} · bowl {profile['bowl_runs_per_ball']:.3f} rpb · "
                f"wkt {profile['wicket_rate']:.4f}"
            )
            if row[2].button("Release", key=f"sc_rel_{player_name}"):
                roster.pop(player_name, None)
                save_roster(roster)
                st.rerun()

    merged_meta = merge_into_meta(meta, roster)
    pool = merged_meta.get("players", meta.get("players", []))

    section("03", "Scout matchup", "Scouted and IPL players, any combination")
    st.caption(
        f"Evidence profile: {PROFILE_LABELS.get(scout_profile, scout_profile)}. "
        + (
            "Sign scouted players above to drop them into these elevens."
            if not roster
            else "Scouted and trained players share one pool below."
        )
    )
    name_columns = st.columns(2)
    with name_columns[0]:
        team_a = st.text_input("Team A", "World XI", key="sc_team_a").strip()
    with name_columns[1]:
        team_b = st.text_input("Team B", "Rest of the World", key="sc_team_b").strip()

    default_a, default_b = profile_presets("modern", pool)
    lineup_columns = st.columns(2)
    with lineup_columns[0]:
        st.markdown(f"#### {escape(team_a or 'Team A')} — batting order")
        xi_a = ordered_lineup_editor("Player", pool, default_a, key="sc_xi_a")
    with lineup_columns[1]:
        st.markdown(f"#### {escape(team_b or 'Team B')} — batting order")
        xi_b = ordered_lineup_editor("Player", pool, default_b, key="sc_xi_b")

    bowling_columns = st.columns(2)
    with bowling_columns[0]:
        bowling_a = st.multiselect(
            f"{team_a or 'Team A'} bowling options",
            list(dict.fromkeys(xi_a)),
            default=recommended_bowlers(xi_a, merged_meta),
            key="sc_bowl_a",
        )
        st.markdown(
            f'<div class="lineup-meta">{lineup_summary(xi_a, merged_meta, bowling_a)}</div>',
            unsafe_allow_html=True,
        )
    with bowling_columns[1]:
        bowling_b = st.multiselect(
            f"{team_b or 'Team B'} bowling options",
            list(dict.fromkeys(xi_b)),
            default=recommended_bowlers(xi_b, merged_meta),
            key="sc_bowl_b",
        )
        st.markdown(
            f'<div class="lineup-meta">{lineup_summary(xi_b, merged_meta, bowling_b)}</div>',
            unsafe_allow_html=True,
        )

    condition_columns = st.columns([1.4, 1, 1, 1])
    with condition_columns[0]:
        venues = merged_meta.get("venues", [])
        venue = st.selectbox(
            "Venue", venues,
            index=venues.index("Eden Gardens") if "Eden Gardens" in venues else 0,
            key="sc_venue",
        )
    with condition_columns[1]:
        toss_winner = st.selectbox("Toss winner", [team_a or "Team A", team_b or "Team B"], key="sc_toss_w")
    with condition_columns[2]:
        toss_decision = st.selectbox(
            "Toss decision", ["bat", "field"],
            format_func=lambda v: "Bat first" if v == "bat" else "Field first",
            key="sc_toss_d",
        )
    with condition_columns[3]:
        simulations = st.slider("Simulations", 10, 100, 50, 5, key="sc_sims")

    overlap = sorted(set(xi_a) & set(xi_b))
    problems = []
    if len(xi_a) != 11 or len(xi_b) != 11:
        problems.append("Fill all 11 batting positions for each team.")
    if len(set(xi_a)) != len(xi_a) or len(set(xi_b)) != len(xi_b):
        problems.append("A player can appear only once in a batting order.")
    if overlap:
        problems.append(f"A player cannot represent both teams: {', '.join(overlap)}.")
    if len(bowling_a) < 5 or len(bowling_b) < 5:
        problems.append("Nominate at least five bowling options for each team.")
    if not team_a or not team_b or team_a == team_b:
        problems.append("Use two distinct team names.")
    if problems:
        st.warning(" ".join(problems))

    if st.button(
        "Simulate scout match", type="primary", width="stretch",
        disabled=bool(problems), key="sc_run",
    ):
        with st.spinner(
            f"Bowling {simulations} full matches on "
            f"{PROFILE_LABELS.get(scout_profile, scout_profile).lower()} evidence..."
        ):
            distribution = simulate_distribution(
                simulations, team_a, team_b, xi_a, xi_b, models, merged_meta,
                "xgboost", venue, "data-driven", "data-driven",
                toss_winner, toss_decision, seed=1017,
                bowlers1=bowling_a, bowlers2=bowling_b,
            )
            scorecard_seed = representative_seed(distribution)
            result = simulate_match(
                team_a, team_b, xi_a, xi_b, models, merged_meta,
                "xgboost", venue, "data-driven", "data-driven",
                toss_winner, toss_decision, seed=scorecard_seed,
                commentary=False, bowlers1=bowling_a, bowlers2=bowling_b,
            )
        st.session_state["scout_run"] = {
            "result": result,
            "distribution": distribution,
            "config": {
                "profile": scout_profile,
                "model": "xgboost",
                "venue": venue,
                "simulations": simulations,
                "seed": 17,
                "scorecard_seed": scorecard_seed,
                "toss_winner": toss_winner,
                "toss_decision": toss_decision,
                "bowling_a": bowling_a,
                "bowling_b": bowling_b,
                "xi": {team_a: xi_a, team_b: xi_b},
            },
        }
        st.rerun()

    scout_run = st.session_state.get("scout_run")
    if scout_run:
        render_run(scout_run, key_prefix="sc_", section_start=4)
    st.caption(
        "Scouted profiles are session evidence, not retrained models: career "
        "aggregates are shrunk toward the IPL baseline with the training "
        "pipeline's own constants, and the trained artifacts are untouched."
    )


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

render_masthead()

if "pending_nav" in st.session_state:
    st.session_state["primary_nav"] = st.session_state.pop("pending_nav")

navigation = st.radio(
    "Primary navigation",
    ["Match Lab", "Match Day", "The Scout", "The Engine"],
    horizontal=True,
    label_visibility="collapsed",
    key="primary_nav",
)

if navigation == "Match Lab":
    render_match_lab()
elif navigation == "Match Day":
    render_results()
elif navigation == "The Scout":
    render_scout()
else:
    render_model_notes()

@st.cache_resource(show_spinner=False)
def logo_data_uri(path: str, size: int = 30) -> str:
    import base64
    import io

    from PIL import Image

    image = Image.open(path).convert("RGBA")
    image.thumbnail((size * 2, size * 2), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


linkedin_logo = logo_data_uri("assets/linkedin_icon.png")
x_logo = logo_data_uri("assets/x_icon.webp")

st.markdown(
    '<div class="footer">'
    '<div class="stamp">cricpredai · trained on 288,051 deliveries · 2008–2026 · every match here is synthetic</div>'
    '<div class="who">Built by <b>Annay De</b>'
    f'<a class="applogo" href="https://www.linkedin.com/in/annayde/" target="_blank" rel="noopener noreferrer" aria-label="Annay De on LinkedIn"><img src="{linkedin_logo}" alt="LinkedIn"></a>'
    f'<a class="applogo" href="https://x.com/AnnayDe_" target="_blank" rel="noopener noreferrer" aria-label="Annay De on X"><img src="{x_logo}" alt="X"></a>'
    "</div></div>",
    unsafe_allow_html=True,
)
