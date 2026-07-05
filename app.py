from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulator import (
    available_profiles,
    load_artifacts,
    representative_seed,
    simulate_distribution,
    simulate_match,
)

st.set_page_config(
    page_title="CricPredAI | IPL Simulation Lab",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="collapsed",
)

COLORS = {
    "ink": "#F7FBFF",
    "muted": "#93A8C2",
    "paper": "#06111F",
    "panel": "rgba(8, 23, 42, 0.78)",
    "line": "rgba(150, 187, 226, 0.18)",
    "blue": "#38BDF8",
    "navy": "#020817",
    "copper": "#8B5CF6",
    "gold": "#F8C14A",
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
        --cyan: #67E8F9;
        --violet: #A78BFA;
        --ice: #DDF7FF;
        --glass: rgba(8, 23, 42, 0.58);
        --glass-strong: rgba(10, 30, 55, 0.78);
        --glass-light: rgba(226, 245, 255, 0.08);
        --shadow: 0 26px 90px rgba(0, 0, 0, 0.42);
        --glow: 0 0 42px rgba(56, 189, 248, 0.20);
        --font: Inter, "SF Pro Display", "SF Pro Text", "Aptos", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .stApp,
    .stApp button,
    .stApp input,
    .stApp textarea,
    .stApp select {{
        font-family: var(--font);
    }}
    [data-testid="stIconMaterial"],
    .material-symbols-rounded {{
        font-family: "Material Symbols Rounded" !important;
        font-style: normal !important;
        font-weight: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        -webkit-font-feature-settings: "liga" !important;
        font-feature-settings: "liga" !important;
        -webkit-font-smoothing: antialiased;
    }}
    .material-symbols-outlined {{
        font-family: "Material Symbols Outlined" !important;
        font-style: normal !important;
        font-weight: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        -webkit-font-feature-settings: "liga" !important;
        font-feature-settings: "liga" !important;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp {{
        background:
            radial-gradient(circle at 8% 6%, rgba(56, 189, 248, 0.30), transparent 32rem),
            radial-gradient(circle at 92% 2%, rgba(99, 102, 241, 0.24), transparent 34rem),
            radial-gradient(circle at 82% 78%, rgba(34, 211, 238, 0.16), transparent 30rem),
            linear-gradient(135deg, #020817 0%, #06142A 46%, #020817 100%);
        color: var(--ink);
        overflow-x: hidden;
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image:
            linear-gradient(rgba(148, 188, 226, 0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148, 188, 226, 0.08) 1px, transparent 1px);
        background-size: 44px 44px;
        mask-image: radial-gradient(circle at 50% 0%, rgba(0,0,0,0.86), transparent 70%);
        z-index: 0;
    }}
    .stApp::after {{
        content: "";
        position: fixed;
        width: 48rem;
        height: 48rem;
        right: -18rem;
        top: 8rem;
        pointer-events: none;
        border-radius: 42% 58% 68% 32% / 42% 38% 62% 58%;
        background:
            radial-gradient(circle at 34% 24%, rgba(103, 232, 249, 0.40), transparent 15rem),
            radial-gradient(circle at 68% 66%, rgba(79, 70, 229, 0.35), transparent 17rem),
            linear-gradient(135deg, rgba(56, 189, 248, 0.14), rgba(2, 8, 23, 0));
        filter: blur(18px);
        opacity: 0.86;
        transform: rotate(-14deg);
        z-index: 0;
    }}
    header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
    [data-testid="stMainBlockContainer"] {{
        max-width: 1260px;
        padding-top: 1.4rem;
        padding-bottom: 4rem;
        position: relative;
        z-index: 1;
    }}
    h1, h2, h3, h4 {{
        color: var(--ink);
        letter-spacing: -0.055em;
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
        border: 1px solid rgba(170, 214, 255, 0.17);
        background:
            linear-gradient(135deg, rgba(15, 35, 62, 0.70), rgba(7, 18, 34, 0.52)),
            linear-gradient(90deg, rgba(56, 189, 248, 0.12), transparent 42%);
        backdrop-filter: blur(28px) saturate(180%);
        -webkit-backdrop-filter: blur(28px) saturate(180%);
        box-shadow: 0 18px 54px rgba(0, 0, 0, 0.26);
        border-radius: 28px;
        padding: 0.78rem 0.92rem;
        margin-bottom: 1.05rem;
    }}
    .brand {{ display: flex; align-items: center; gap: 0.75rem; }}
    .brand-mark {{
        width: 2.5rem;
        height: 2.5rem;
        position: relative;
        display: block;
        border-radius: 999px;
        background:
            radial-gradient(circle at 34% 28%, rgba(221, 247, 255, 0.95), transparent 0.42rem),
            conic-gradient(from 210deg, var(--cyan), var(--blue), var(--violet), var(--cyan));
        box-shadow: 0 0 28px rgba(56, 189, 248, 0.35);
        overflow: hidden;
    }}
    .brand-mark::after {{
        content: "";
        position: absolute;
        inset: 0.45rem;
        border: 1px solid rgba(2, 8, 23, 0.56);
        border-radius: 999px;
    }}
    .brand-mark span {{
        position: absolute;
        display: block;
        border-radius: 999px;
        background: rgba(2, 8, 23, 0.60);
        transform: rotate(-35deg);
    }}
    .brand-mark span:nth-child(1) {{
        width: 1.15rem;
        height: 0.22rem;
        left: 0.62rem;
        top: 0.72rem;
    }}
    .brand-mark span:nth-child(2) {{
        width: 1.55rem;
        height: 0.22rem;
        left: 0.48rem;
        top: 1.12rem;
        opacity: 0.72;
    }}
    .brand-mark span:nth-child(3) {{
        width: 0.86rem;
        height: 0.22rem;
        left: 0.92rem;
        top: 1.52rem;
        opacity: 0.54;
    }}
    .brand-name {{
        font-weight: 850;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--ink);
    }}
    .brand-sub, .coverage {{
        color: var(--muted);
        font-size: 0.76rem;
    }}
    .coverage strong {{ color: var(--ice); }}
    .coverage {{ text-align: right; letter-spacing: 0.02em; }}
    .hero {{
        position: relative;
        overflow: hidden;
        padding: clamp(2.2rem, 5vw, 4.8rem);
        border: 1px solid rgba(170, 214, 255, 0.18);
        border-radius: 38px;
        margin-bottom: 1.8rem;
        background:
            radial-gradient(circle at 85% 20%, rgba(103, 232, 249, 0.36), transparent 20rem),
            radial-gradient(circle at 18% 0%, rgba(99, 102, 241, 0.38), transparent 22rem),
            linear-gradient(135deg, rgba(6, 20, 42, 0.96) 0%, rgba(8, 38, 73, 0.92) 56%, rgba(2, 8, 23, 0.96) 100%);
        color: white;
        box-shadow: var(--shadow);
        backdrop-filter: blur(18px) saturate(165%);
        -webkit-backdrop-filter: blur(18px) saturate(165%);
    }}
    .hero::before {{
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(rgba(221,247,255,0.07) 1px, transparent 1px),
            linear-gradient(90deg, rgba(221,247,255,0.07) 1px, transparent 1px);
        background-size: 46px 46px;
        mask-image: linear-gradient(120deg, rgba(0,0,0,0.70), transparent 72%);
    }}
    .hero::after {{
        content: "";
        position: absolute;
        right: -7rem;
        bottom: -10rem;
        width: 31rem;
        height: 31rem;
        border-radius: 44% 56% 60% 40% / 47% 37% 63% 53%;
        background:
            radial-gradient(circle at 38% 30%, rgba(221,247,255,0.34), transparent 7rem),
            conic-gradient(from 140deg, rgba(103,232,249,0.55), rgba(79,70,229,0.32), rgba(56,189,248,0.08), rgba(103,232,249,0.55));
        filter: blur(2px);
        opacity: 0.64;
    }}
    .eyebrow {{
        position: relative;
        color: var(--cyan);
        font-size: 0.72rem;
        font-weight: 850;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }}
    .hero h1 {{
        position: relative;
        color: white;
        max-width: 900px;
        margin: 0;
        font-weight: 850;
    }}
    .hero-copy {{
        position: relative;
        color: rgba(221,247,255,0.78);
        max-width: 720px;
        margin-top: 1.2rem;
        font-size: 1.04rem;
        line-height: 1.65;
    }}
    .section-head {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid var(--line);
        padding: 1.2rem 0 0.8rem;
        margin: 0.55rem 0 1.1rem;
    }}
    .section-head h2 {{
        margin: 0;
        font-size: 1.35rem;
        line-height: 1.15;
        font-weight: 850;
    }}
    .section-note {{
        color: var(--muted);
        font-size: 0.8rem;
        text-align: right;
    }}
    div[data-testid="stMetric"],
    .score-box,
    .model-card {{
        background: var(--glass-strong);
        border: 1px solid rgba(170, 214, 255, 0.16);
        border-radius: 26px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(22px) saturate(170%);
        -webkit-backdrop-filter: blur(22px) saturate(170%);
    }}
    div[data-testid="stMetric"] {{
        padding: 0.95rem 1rem;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
        color: var(--muted) !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
        color: var(--ink) !important;
    }}
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stNumberInput"] input,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] {{
        border-radius: 18px !important;
        background: rgba(221, 247, 255, 0.08) !important;
        border-color: rgba(170, 214, 255, 0.18) !important;
        color: var(--ink) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }}
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        color: var(--ink) !important;
    }}
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"] {{
        background: rgba(7, 18, 34, 0.98) !important;
        border: 1px solid rgba(170, 214, 255, 0.18) !important;
        color: var(--ink) !important;
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.44) !important;
    }}
    div[role="option"],
    li[role="option"] {{
        color: var(--ink) !important;
        background: transparent !important;
    }}
    div[role="option"]:hover,
    li[role="option"]:hover {{
        background: rgba(56, 189, 248, 0.16) !important;
    }}
    div[data-baseweb="tag"] {{
        background: rgba(56, 189, 248, 0.18) !important;
        border: 1px solid rgba(103, 232, 249, 0.28) !important;
        color: var(--ink) !important;
    }}
    input:disabled {{
        -webkit-text-fill-color: var(--muted) !important;
        opacity: 1 !important;
    }}
    label, div[data-testid="stWidgetLabel"] p {{
        color: var(--ice) !important;
        font-weight: 650;
    }}
    div[data-testid="stRadio"] > div {{ gap: 0.35rem; }}
    div[data-testid="stRadio"] label {{
        border: 1px solid rgba(170, 214, 255, 0.18);
        background: rgba(221, 247, 255, 0.07);
        border-radius: 999px;
        padding: 0.45rem 0.88rem;
        min-height: 2.35rem;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
    }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        border-color: rgba(103, 232, 249, 0.42);
        background: linear-gradient(135deg, rgba(14, 116, 144, 0.92), rgba(37, 99, 235, 0.86));
        color: white;
        box-shadow: 0 0 26px rgba(56, 189, 248, 0.18);
    }}
    div[data-testid="stRadio"] label:has(input:checked) p,
    div[data-testid="stRadio"] label:has(input:checked) span {{
        color: white !important;
    }}
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {{
        border-radius: 999px;
        min-height: 2.75rem;
        font-weight: 850;
        letter-spacing: 0.03em;
        border-color: rgba(170, 214, 255, 0.22);
        background: rgba(221, 247, 255, 0.08);
        color: var(--ink);
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
    }}
    div[data-testid="stButton"] button[kind="primary"] {{
        background: linear-gradient(135deg, #0EA5E9, #2563EB 58%, #7C3AED);
        border-color: rgba(221,247,255,0.28);
        color: white;
        box-shadow: 0 18px 48px rgba(37, 99, 235, 0.34);
    }}
    .profile-note {{
        border: 1px solid rgba(170, 214, 255, 0.18);
        border-left: 5px solid var(--blue);
        border-radius: 18px;
        background: rgba(8, 23, 42, 0.62);
        padding: 0.82rem 1rem;
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
        border: 1px solid rgba(170, 214, 255, 0.18);
        border-top: 6px solid var(--cyan);
        border-radius: 30px;
        background:
            radial-gradient(circle at 92% 10%, rgba(103,232,249,0.34), transparent 18rem),
            radial-gradient(circle at 24% 0%, rgba(124,58,237,0.26), transparent 18rem),
            linear-gradient(135deg, rgba(4,16,31,0.96), rgba(8,47,73,0.88));
        color: white;
        padding: 1.8rem 2rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow);
    }}
    .result-kicker {{
        color: var(--cyan);
        font-size: 0.72rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}
    .result-title {{
        font-size: clamp(1.9rem, 4vw, 3.4rem);
        line-height: 1.05;
        font-weight: 850;
        margin-top: 0.35rem;
    }}
    .score-box {{ padding: 1.15rem 1.2rem; min-height: 8.2rem; }}
    .score-team {{
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 850;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}
    .score-value {{
        color: var(--ink);
        font-size: 2.45rem;
        line-height: 1.1;
        font-weight: 850;
        margin-top: 0.35rem;
    }}
    .score-detail {{ color: var(--muted); font-size: 0.8rem; margin-top: 0.25rem; }}
    .innings-heading {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        border: 1px solid rgba(170, 214, 255, 0.17);
        border-left: 5px solid var(--blue);
        border-radius: 20px;
        background: rgba(8, 23, 42, 0.66);
        padding: 0.85rem 1rem;
        margin: 0.45rem 0 0.9rem;
    }}
    .innings-heading h3 {{ margin: 0; font-size: 1.25rem; font-weight: 850; }}
    .innings-score {{ color: var(--blue); font-weight: 850; white-space: nowrap; }}
    .innings-divider {{
        height: 1px;
        background: var(--line);
        margin: 1.8rem 0;
    }}
    .model-card {{
        border-top: 5px solid var(--blue);
        padding: 1.2rem;
        min-height: 13rem;
    }}
    .model-card h3 {{ font-size: 1.18rem; font-weight: 850; margin: 0.25rem 0 0.65rem; }}
    .model-card p {{ color: var(--muted); line-height: 1.55; font-size: 0.88rem; }}
    .fact-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem 1rem;
        margin-top: 0.8rem;
        font-size: 0.82rem;
    }}
    .fact-grid span:nth-child(odd) {{ color: var(--muted); }}
    .fact-grid span:nth-child(even) {{ text-align: right; font-weight: 850; }}
    .support-row {{
        display: grid;
        grid-template-columns: 11rem 1fr;
        gap: 1rem;
        padding: 0.85rem 0;
        border-bottom: 1px solid var(--line);
    }}
    .support-row strong {{ font-size: 0.84rem; }}
    .support-row span {{ color: var(--muted); font-size: 0.84rem; line-height: 1.5; }}
    .footer {{
        border-top: 1px solid var(--line);
        margin-top: 3rem;
        padding-top: 1.15rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        color: var(--muted);
        font-size: 0.78rem;
    }}
    .footer strong {{ color: var(--ink); }}
    .footer a {{ color: var(--ice); text-decoration: none; border-bottom: 1px solid rgba(103,232,249,0.36); }}
    .footer-meta {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.6rem;
        flex-wrap: wrap;
    }}
    .social-links {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }}
    .footer a.social-link {{
        width: 2.05rem;
        height: 2.05rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        border: 1px solid rgba(103, 232, 249, 0.30);
        border-bottom: 1px solid rgba(103, 232, 249, 0.30);
        background:
            radial-gradient(circle at 32% 24%, rgba(221, 247, 255, 0.20), transparent 0.72rem),
            linear-gradient(135deg, rgba(56, 189, 248, 0.16), rgba(124, 58, 237, 0.12));
        color: var(--ink);
        font-weight: 850;
        line-height: 1;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
        transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
    }}
    .footer a.social-link:hover {{
        border-color: rgba(103, 232, 249, 0.62);
        box-shadow: 0 0 28px rgba(56, 189, 248, 0.20);
        transform: translateY(-1px);
    }}
    .social-link .social-glyph {{
        display: inline-block;
        color: var(--ink);
        font-size: 0.82rem;
        letter-spacing: -0.03em;
    }}
    .social-link.linkedin .social-glyph {{
        font-size: 0.78rem;
        letter-spacing: -0.08em;
        transform: translateY(-0.02rem);
    }}
    .glass-table-wrap {{
        width: 100%;
        max-height: 520px;
        overflow: auto;
        border: 1px solid rgba(170, 214, 255, 0.16);
        border-radius: 22px;
        background: rgba(8, 23, 42, 0.68);
        box-shadow: 0 18px 54px rgba(0,0,0,0.24);
        backdrop-filter: blur(20px) saturate(160%);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
        margin: 0.35rem 0 1rem;
    }}
    table.glass-table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
    table.glass-table th {{
        position: sticky;
        top: 0;
        z-index: 1;
        background: rgba(7, 18, 34, 0.98);
        color: var(--cyan);
        text-align: left;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-size: 0.68rem;
        padding: 0.72rem 0.82rem;
        border-bottom: 1px solid rgba(170, 214, 255, 0.18);
        white-space: nowrap;
    }}
    table.glass-table td {{
        padding: 0.68rem 0.82rem;
        border-bottom: 1px solid rgba(170, 214, 255, 0.10);
        color: var(--ink);
        white-space: nowrap;
    }}
    table.glass-table tr:nth-child(even) td {{ background: rgba(221, 247, 255, 0.045); }}
    div[data-testid="stTabs"] [role="tablist"] {{
        border-bottom: 1px solid var(--line);
        gap: 0.4rem;
    }}
    div[data-testid="stTabs"] [role="tab"] {{
        color: var(--muted);
        border-radius: 999px 999px 0 0;
        padding: 0.85rem 1rem;
    }}
    div[data-testid="stTabs"] [aria-selected="true"] {{
        color: var(--ink);
        background: rgba(221, 247, 255, 0.08);
    }}
    [data-testid="stExpander"] {{
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(170, 214, 255, 0.16);
        background: rgba(8, 23, 42, 0.46);
    }}
    [data-testid="stExpander"] details > summary {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    [data-testid="stExpander"] details > summary > span:first-child {{
        font-size: 0;
        width: 1rem;
        height: 1rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }}
    [data-testid="stExpander"] details > summary > span:first-child::after {{
        content: "▸";
        font-size: 1rem;
    }}
    [data-testid="stExpander"] details[open] > summary > span:first-child::after {{
        content: "▾";
    }}
    [data-testid="stExpander"] details > summary > span:first-child::after {{
        content: ">";
        color: var(--cyan);
    }}
    [data-testid="stExpander"] details[open] > summary > span:first-child::after {{
        content: "v";
    }}
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
        border-radius: 22px;
        overflow: hidden;
        border: 1px solid rgba(170, 214, 255, 0.16);
        box-shadow: 0 18px 54px rgba(0,0,0,0.24);
    }}
    .stAlert {{
        background: rgba(8, 23, 42, 0.74);
        border: 1px solid rgba(248, 193, 74, 0.28);
        color: var(--ink);
    }}
    @media (max-width: 760px) {{
        .coverage {{ display: none; }}
        .hero {{ padding: 2rem; }}
        .section-head {{ display: block; }}
        .section-note {{ margin-top: 0.35rem; text-align: left; }}
        div[data-testid="stRadio"] > div {{ flex-wrap: nowrap; gap: 0.25rem; }}
        div[data-testid="stRadio"] label {{ padding: 0.35rem 0.5rem; }}
        div[data-testid="stRadio"] label p {{ font-size: 0.8rem; }}
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


def render_static_table(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No rows to display.")
        return
    safe = frame.copy()
    st.markdown(
        '<div class="glass-table-wrap">'
        + safe.to_html(
            index=False,
            escape=True,
            classes="glass-table",
            border=0,
        )
        + "</div>",
        unsafe_allow_html=True,
    )


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
                "Batting position": [str(position) for position in range(1, 12)],
                "Player": default_players,
            }
        ),
        key=key,
        width="stretch",
        height=425,
        hide_index=True,
        num_rows="fixed",
        disabled=["Batting position"],
        column_config={
            "Batting position": st.column_config.TextColumn(
                width="small",
            ),
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
    st.session_state[f"team_name_version_{side}_{profile}"] = (
        st.session_state.get(f"team_name_version_{side}_{profile}", 0) + 1
    )
    st.session_state[f"lineup_version_{side}_{profile}"] = (
        st.session_state.get(f"lineup_version_{side}_{profile}", 0) + 1
    )
    st.session_state[f"bowling_version_{side}_{profile}"] = (
        st.session_state.get(f"bowling_version_{side}_{profile}", 0) + 1
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
        f"{len(xi)}/11 selected | {counts['batter']} batters | "
        f"{counts['all-rounder']} all-rounders | {counts['bowler']} bowlers | "
        f"{bowling_count} selected bowling options"
    )


def section_header(title: str, note: str = "") -> None:
    note_html = f'<div class="section-note">{escape(note)}</div>' if note else ""

    st.markdown(
        f"""
        <div class="section-head">
            <h2>{escape(title)}</h2>
            {note_html}
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


def bowling_phase_summary(innings: dict) -> pd.DataFrame:
    deliveries = innings.get("ball_by_ball", pd.DataFrame()).copy()
    if deliveries.empty:
        return pd.DataFrame()
    deliveries["legal_delivery"] = ~deliveries["outcome"].isin(["WD", "NB"])
    first_use = (
        deliveries.reset_index()
        .groupby("bowler", sort=False)["index"]
        .min()
        .to_dict()
    )
    grouped = (
        deliveries.groupby(["bowler", "phase"], sort=False)["legal_delivery"]
        .sum()
        .unstack(fill_value=0)
    )
    for phase in ["powerplay", "middle", "death"]:
        if phase not in grouped:
            grouped[phase] = 0
    grouped = grouped[["powerplay", "middle", "death"]].reset_index()
    grouped["_first_use"] = grouped["bowler"].map(first_use)
    grouped = grouped.sort_values("_first_use").drop(columns="_first_use")

    def overs(balls: int) -> str:
        balls = int(balls)
        return f"{balls // 6}.{balls % 6}"

    for phase in ["powerplay", "middle", "death"]:
        grouped[phase] = grouped[phase].map(overs)
    return grouped.rename(
        columns={
            "bowler": "Bowler",
            "powerplay": "Powerplay overs",
            "middle": "Middle overs",
            "death": "Death overs",
        }
    )


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
        plot_bgcolor="rgba(8, 23, 42, 0.72)",
        font={
            "color": COLORS["ink"],
            "family": "Inter, SF Pro Display, Segoe UI, sans-serif",
        },
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={
            "title": "Overs",
            "range": [0, 20],
            "gridcolor": COLORS["line"],
            "zeroline": False,
            "linecolor": COLORS["line"],
            "tickcolor": COLORS["line"],
        },
        yaxis={
            "title": "Runs",
            "gridcolor": COLORS["line"],
            "zeroline": False,
            "linecolor": COLORS["line"],
            "tickcolor": COLORS["line"],
        },
        hoverlabel={"bgcolor": "#020817", "font_color": "white"},
    )
    return figure


def probability_figure(distribution: pd.DataFrame, result: dict) -> go.Figure:
    figure = go.Figure()
    palette = {
        result["first"]["team"]: COLORS["blue"],
        result["second"]["team"]: COLORS["copper"],
        "Tie": COLORS["gold"],
    }
    for winner, group in distribution.groupby("winner", sort=False):
        figure.add_trace(
            go.Scatter(
                x=group["first_runs"],
                y=group["second_runs"],
                mode="markers",
                name=str(winner),
                marker={
                    "color": palette.get(str(winner), COLORS["muted"]),
                    "size": 11,
                    "opacity": 0.78,
                    "line": {"color": "rgba(221,247,255,0.32)", "width": 1},
                },
                customdata=np.column_stack([group["sim"], group["seed"]]),
                hovertemplate=(
                    "Simulation %{customdata[0]}<br>"
                    "Seed %{customdata[1]}<br>"
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
            line={"color": COLORS["muted"], "width": 1.5, "dash": "dash"},
            hoverinfo="skip",
        )
    )
    figure.update_layout(
        height=440,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8, 23, 42, 0.72)",
        font={
            "color": COLORS["ink"],
            "family": "Inter, SF Pro Display, Segoe UI, sans-serif",
        },
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={
            "title": f"{result['first']['team']} runs (batting first)",
            "gridcolor": COLORS["line"],
            "zeroline": False,
            "range": [lower, upper],
            "linecolor": COLORS["line"],
            "tickcolor": COLORS["line"],
        },
        yaxis={
            "title": f"{result['second']['team']} runs (chasing)",
            "gridcolor": COLORS["line"],
            "zeroline": False,
            "range": [lower, upper],
            "scaleanchor": "x",
            "scaleratio": 1,
            "linecolor": COLORS["line"],
            "tickcolor": COLORS["line"],
        },
        hoverlabel={"bgcolor": "#020817", "font_color": "white"},
    )
    return figure


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


def render_header() -> None:
    st.markdown(
        """
        <div class="site-head">
            <div class="brand">
                <div class="brand-mark" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div>
                    <div class="brand-name">CricPredAI</div>
                    <div class="brand-sub">IPL simulation laboratory</div>
                </div>
            </div>
            <div class="coverage">
                288,051 ball-by-ball events<br>
                Calibrated IPL archive, 2008-2026
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_match_lab() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Role-aware match intelligence</div>
            <h1>Pressure-test IPL elevens before the first ball is bowled.</h1>
            <div class="hero-copy">
                A ball-by-ball simulator trained on 288,051 IPL deliveries.
                Set batting positions, nominate the bowling pool, choose the venue,
                and compare a representative scorecard against the full outcome distribution.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_header("Model basis", "Choose how historical player data should be weighted")
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

    saved_teams = saved_team_store(profile)
    with st.expander("Temporary team drawer", expanded=bool(saved_teams)):
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
            load_a = st.selectbox(
                "Load into Team A",
                saved_options,
                key=f"load_a_{profile}",
            )
        with load_cols[1]:
            if st.button(
                "Load A",
                disabled=not load_a,
                key=f"load_a_button_{profile}",
                width="stretch",
            ):
                load_saved_team(profile, "a", load_a)
        with load_cols[2]:
            load_b = st.selectbox(
                "Load into Team B",
                saved_options,
                key=f"load_b_{profile}",
            )
        with load_cols[3]:
            if st.button(
                "Load B",
                disabled=not load_b,
                key=f"load_b_button_{profile}",
                width="stretch",
            ):
                load_saved_team(profile, "b", load_b)

    section_header(
        "Playing XIs",
        "Set all 11 batting positions, then nominate at least five bowling options",
    )
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
        st.markdown(f"#### {escape(team_a or 'Team A')} batting order")
        default_xi_a = lineup_default(profile, "a", default_xi_a)
        xi_a = ordered_lineup_editor(
            "Player",
            players,
            default_xi_a,
            key=editor_key(profile, "a"),
        )
    with lineups[1]:
        st.markdown(f"#### {escape(team_b or 'Team B')} batting order")
        default_xi_b = lineup_default(profile, "b", default_xi_b)
        xi_b = ordered_lineup_editor(
            "Player",
            players,
            default_xi_b,
            key=editor_key(profile, "b"),
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
            f'<div class="lineup-meta">{escape(lineup_summary(xi_a, meta, bowling_a))}</div>',
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
            f'<div class="lineup-meta">{escape(lineup_summary(xi_b, meta, bowling_b))}</div>',
            unsafe_allow_html=True,
        )

    save_cols = st.columns(2)
    team_a_can_save = len(xi_a) == 11 and len(set(xi_a)) == 11 and len(bowling_a) >= 5
    team_b_can_save = len(xi_b) == 11 and len(set(xi_b)) == 11 and len(bowling_b) >= 5
    with save_cols[0]:
        if st.button(
            f"Save {team_a or 'Team A'} temporarily",
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
            f"Save {team_b or 'Team B'} temporarily",
            disabled=not team_b_can_save,
            key=f"save_b_{profile}",
            width="stretch",
        ):
            save_team(profile, team_b or "Team B", xi_b, bowling_b)
            st.session_state[f"saved_team_message_{profile}"] = (
                f"Saved {team_b or 'Team B'} for this session."
            )
            st.rerun()

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
                    will remain available here.
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
    modal_winner = str(distribution["winner"].value_counts().index[0])
    representative_number = distribution.loc[
        distribution["seed"].eq(config.get("scorecard_seed")),
        "sim",
    ]
    representative_label = (
        f"Simulation {int(representative_number.iloc[0])}"
        if not representative_number.empty
        else "Representative simulation"
    )
    st.caption(
        f"Displayed scorecard: {representative_label} from this distribution "
        f"(seed {config.get('scorecard_seed')}); selected near the center of "
        f"the most frequent outcome, {modal_winner}."
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
            render_static_table(innings["batting_card"])
            st.markdown("#### Bowling")
            if innings.get("bowling_options"):
                st.caption(
                    "Eligible options: "
                    + ", ".join(map(str, innings["bowling_options"]))
                )
            render_static_table(innings["bowling_card"])
            phase_summary = bowling_phase_summary(innings)
            if not phase_summary.empty:
                st.caption(
                    "Phase deployment from the user-nominated bowling options"
                )
                render_static_table(phase_summary)
            if not innings["fall_of_wickets"].empty:
                st.markdown("#### Fall of wickets")
                render_static_table(innings["fall_of_wickets"])
            if index == 0:
                st.markdown('<div class="innings-divider"></div>', unsafe_allow_html=True)

    with probability_tab:
        st.markdown("#### Paired simulation outcomes")
        st.caption(
            "Each dot is one complete match. Dots above the dashed line are "
            f"{result['second']['team']} chase wins; dots below it are "
            f"{result['first']['team']} wins. This preserves which two scores "
            "belonged to the same simulation."
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
                lambda interval: f"{100 * interval[0]:.0f}% - {100 * interval[1]:.0f}%"
            )(wilson_interval(int(count), len(distribution)))
            for count in probability_table["Simulations"]
        ]
        probability_display = probability_table.copy()
        probability_display["Probability"] = probability_display["Probability"].map(
            lambda value: f"{100 * value:.1f}%"
        )
        render_static_table(probability_display)
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
            "dismissal_kind",
            "dismissal",
            "fielder",
            "score",
            "wickets",
            "p_wicket",
            "p_boundary",
            "p_extra",
        ]
        render_static_table(innings["ball_by_ball"][log_columns])
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
            <h1>Every combination, one simulation engine.</h1>
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
    render_static_table(report_display)

    section_header("Inputs that change the simulation", "Only supported controls are exposed")
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

    section_header("Excluded Aspects")
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
        <div>CricPredAI | IPL simulation laboratory</div>
        <div class="footer-meta">
            <span>Built by <strong>Annay De</strong></span>
            <span class="social-links" aria-label="Annay De social links">
                <a class="social-link linkedin" href="https://www.linkedin.com/in/annayde/" target="_blank" rel="noopener noreferrer" aria-label="Annay De on LinkedIn">
                    <span class="social-glyph">in</span>
                </a>
                <a class="social-link" href="https://x.com/AnnayDe_" target="_blank" rel="noopener noreferrer" aria-label="Annay De on X">
                    <span class="social-glyph">X</span>
                </a>
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
