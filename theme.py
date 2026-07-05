"""Global design system for the CricPredAI app.

"Night match" language: floodlit near-black green, chartreuse and hot
orange accents, condensed poster type for display, mono for data, and an
editorial serif for commentary. Sharp corners, dashed scorecard rules,
film grain — no gradients-and-glass defaults.
"""

PALETTE = {
    "bg": "#0B0F0C",
    "panel": "#11160F",
    "panel2": "#0E130D",
    "ink": "#EDEAD9",
    "muted": "#8B9182",
    "dim": "#5A6152",
    "lime": "#D6F546",
    "orange": "#FF7A3D",
    "red": "#FF4438",
    "gold": "#E8C46B",
    "line": "rgba(237,234,217,0.13)",
    "line2": "rgba(237,234,217,0.07)",
}

GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence "
    "type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix "
    "type='saturate' values='0'/%3E%3CfeComponentTransfer%3E%3CfeFuncA "
    "type='linear' slope='0.045'/%3E%3C/feComponentTransfer%3E%3C/filter%3E"
    "%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E\")"
)

APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;500;600;700;800;900&family=Newsreader:ital,opsz,wght@1,6..72,400;1,6..72,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {{
    --bg: {PALETTE["bg"]};
    --panel: {PALETTE["panel"]};
    --panel2: {PALETTE["panel2"]};
    --ink: {PALETTE["ink"]};
    --mut: {PALETTE["muted"]};
    --dim: {PALETTE["dim"]};
    --lime: {PALETTE["lime"]};
    --org: {PALETTE["orange"]};
    --red: {PALETTE["red"]};
    --gold: {PALETTE["gold"]};
    --line: {PALETTE["line"]};
    --line2: {PALETTE["line2"]};
    --mono: "IBM Plex Mono", ui-monospace, monospace;
    --disp: "Anton", "Archivo Black", system-ui, sans-serif;
    --body: "Archivo", system-ui, sans-serif;
    --serif: "Newsreader", Georgia, serif;
}}

/* ---------- shell ---------- */
.stApp {{
    background:
        radial-gradient(90% 40% at 50% -6%, rgba(214,245,70,0.05), transparent 62%),
        linear-gradient(180deg, #0D120D 0%, {PALETTE["bg"]} 34%);
    color: var(--ink);
}}
.stApp::before {{
    content: "";
    position: fixed; inset: 0;
    pointer-events: none; z-index: 0;
    opacity: .55;
    background-image: {GRAIN};
}}
/* pitch crease verticals framing the content column */
.stApp::after {{
    content: "";
    position: fixed; inset: 0;
    pointer-events: none; z-index: 0;
    background:
        linear-gradient(90deg, transparent calc(50% - 620px), var(--line2) calc(50% - 620px), transparent calc(50% - 619px)),
        linear-gradient(90deg, transparent calc(50% + 619px), var(--line2) calc(50% + 619px), transparent calc(50% + 620px));
}}
header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{
    max-width: 1200px;
    padding-top: 1.1rem;
    padding-bottom: 4rem;
    position: relative; z-index: 1;
}}
.stApp, .stApp p, .stApp li {{ font-family: var(--body); }}
h1, h2, h3, h4 {{ color: var(--ink); font-family: var(--body); letter-spacing: -0.02em; }}

[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded" !important;
    font-weight: normal !important; font-style: normal !important;
    letter-spacing: normal !important; text-transform: none !important;
    -webkit-font-feature-settings: "liga" !important; font-feature-settings: "liga" !important;
}}

/* ---------- masthead ---------- */
.masthead {{
    display: flex; align-items: stretch; justify-content: space-between;
    border: 1px solid var(--line);
    border-bottom: none;
    background: var(--panel2);
}}
.masthead .mh-brand {{
    display: flex; align-items: center; gap: 14px;
    padding: 14px 18px;
    border-right: 1px dashed var(--line);
}}
.mh-mark {{
    width: 34px; height: 34px; position: relative; flex: none;
    background: var(--lime);
}}
.mh-mark::before {{
    content: ""; position: absolute; inset: 0;
    background:
        linear-gradient(0deg, transparent 46%, #0B0F0C 46%, #0B0F0C 54%, transparent 54%),
        linear-gradient(90deg, transparent 46%, #0B0F0C 46%, #0B0F0C 54%, transparent 54%);
}}
.mh-name {{
    font: 400 22px/1 var(--disp);
    letter-spacing: .05em; text-transform: uppercase; color: var(--ink);
}}
.mh-name span {{ color: var(--lime); }}
.mh-sub {{ font: 500 9px/1.5 var(--mono); letter-spacing: .28em; text-transform: uppercase; color: var(--dim); }}
.mh-right {{
    display: flex; align-items: center; gap: 18px; padding: 0 18px;
    font: 500 10px/1.7 var(--mono); color: var(--mut);
    letter-spacing: .12em; text-transform: uppercase; text-align: right;
}}
.mh-right b {{ color: var(--ink); font-weight: 600; }}

/* ---------- ticker ---------- */
.ticker {{
    overflow: hidden; white-space: nowrap;
    border: 1px solid var(--line);
    background: var(--panel);
    padding: 7px 0;
    margin-bottom: 14px;
    position: relative;
}}
.ticker .belt {{
    display: inline-block;
    animation: belt 38s linear infinite;
}}
.ticker:hover .belt {{ animation-play-state: paused; }}
.ticker span {{
    font: 500 10px/1 var(--mono);
    letter-spacing: .22em; text-transform: uppercase; color: var(--mut);
    padding: 0 14px;
}}
.ticker span b {{ color: var(--lime); font-weight: 600; }}
@keyframes belt {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}

/* ---------- nav (radio reskin) ---------- */
div[data-testid="stRadio"][class*=""] > div {{ gap: 0; }}
.navwrap div[data-testid="stRadio"] > div {{ gap: 0; flex-wrap: nowrap; }}
div[data-testid="stRadio"] label {{
    border: 1px solid var(--line);
    margin-right: -1px;
    background: transparent;
    border-radius: 0;
    padding: 10px 18px;
    transition: all .12s ease;
}}
div[data-testid="stRadio"] label p {{
    font: 600 11px/1 var(--mono) !important;
    letter-spacing: .18em; text-transform: uppercase;
    color: var(--mut) !important;
}}
div[data-testid="stRadio"] label:hover p {{ color: var(--ink) !important; }}
div[data-testid="stRadio"] label:has(input:checked) {{
    background: var(--lime);
    border-color: var(--lime);
}}
div[data-testid="stRadio"] label:has(input:checked) p {{
    color: #0B0F0C !important; font-weight: 600 !important;
}}
div[data-testid="stRadio"] label > div:first-child {{ display: none; }}

/* ---------- hero ---------- */
.hero {{
    position: relative;
    border: 1px solid var(--line);
    background:
        radial-gradient(70% 90% at 82% 10%, rgba(214,245,70,0.07), transparent 60%),
        var(--panel2);
    padding: clamp(1.6rem, 4vw, 3rem);
    margin: 0 0 1.4rem;
    overflow: hidden;
}}
.hero::before {{
    content: "";
    position: absolute; right: -40px; top: -40px;
    width: 300px; height: 300px;
    border-radius: 50%;
    border: 1px dashed var(--line);
    pointer-events: none;
}}
.hero::after {{
    content: "";
    position: absolute; right: 40px; top: 34px;
    width: 140px; height: 140px;
    border-radius: 50%;
    border: 1px dashed var(--line);
    pointer-events: none;
}}
.hero .eyebrow {{
    font: 600 10px/1 var(--mono);
    letter-spacing: .3em; text-transform: uppercase; color: var(--lime);
    margin-bottom: 14px;
}}
.hero h1, .hero .h1 {{
    font: 400 clamp(2.6rem, 6.5vw, 5rem)/0.98 var(--disp);
    text-transform: uppercase; letter-spacing: .012em;
    color: var(--ink); margin: 0; max-width: 830px;
}}
.hero .h1 em {{ font-style: normal; color: var(--lime); }}
.hero .copy {{
    margin-top: 16px; max-width: 620px;
    font: 500 15px/1.65 var(--serif); font-style: italic;
    color: var(--mut);
}}
.hero .herostats {{
    display: flex; gap: 26px; flex-wrap: wrap; margin-top: 22px;
}}
.hero .hs b {{ display: block; font: 500 20px/1 var(--mono); color: var(--ink); }}
.hero .hs span {{ font: 500 9px/2.2 var(--mono); letter-spacing: .22em; text-transform: uppercase; color: var(--dim); }}

/* ---------- section headers ---------- */
.sect {{
    display: flex; align-items: baseline; gap: 14px;
    border-bottom: 1px dashed var(--line);
    padding: 1.5rem 0 .65rem;
    margin-bottom: 1rem;
}}
.sect .no {{
    font: 500 11px/1 var(--mono); color: var(--lime); letter-spacing: .1em;
}}
.sect h2 {{
    margin: 0;
    font: 400 1.45rem/1 var(--disp);
    letter-spacing: .03em; text-transform: uppercase;
}}
.sect .note {{
    margin-left: auto;
    font: 500 10px/1.5 var(--mono); letter-spacing: .08em;
    color: var(--dim); text-transform: uppercase; text-align: right;
}}

/* ---------- widgets ---------- */
label, div[data-testid="stWidgetLabel"] p {{
    font: 600 10px/1.4 var(--mono) !important;
    letter-spacing: .2em !important; text-transform: uppercase;
    color: var(--mut) !important;
}}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    border-radius: 0 !important;
    background: var(--panel) !important;
    border-color: var(--line) !important;
    color: var(--ink) !important;
    font-family: var(--body);
}}
div[data-baseweb="select"] > div {{ border-radius: 0 !important; border-color: var(--line) !important; background: var(--panel) !important; }}
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{
    color: var(--ink) !important;
}}
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {{
    background: #10150F !important;
    border: 1px solid var(--line) !important;
    border-radius: 0 !important;
    box-shadow: 0 18px 50px rgba(0,0,0,.5) !important;
}}
ul[role="listbox"] li {{ background: transparent !important; color: var(--ink) !important; }}
div[role="option"], li[role="option"] {{ color: var(--ink) !important; background: transparent !important; }}
div[role="option"]:hover, li[role="option"]:hover,
li[aria-selected="true"] {{ background: rgba(214,245,70,0.12) !important; }}
[data-baseweb="tag"] {{
    background: rgba(214,245,70,0.12) !important;
    border: 1px solid rgba(214,245,70,0.45) !important;
    border-radius: 0 !important;
    color: var(--lime) !important;
}}
[data-baseweb="tag"] span, [data-baseweb="tag"] div {{
    color: var(--lime) !important;
    font-family: var(--mono);
    font-size: 12px;
}}
[data-baseweb="tag"] svg, [data-baseweb="tag"] [role="presentation"] {{ fill: var(--lime) !important; color: var(--lime) !important; }}
input:disabled {{ -webkit-text-fill-color: var(--mut) !important; opacity: 1 !important; }}

/* buttons */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{
    border-radius: 0;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink);
    font: 600 11px/1.2 var(--mono);
    letter-spacing: .16em; text-transform: uppercase;
    min-height: 2.6rem;
    transition: all .12s ease;
}}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {{
    border-color: var(--lime); color: var(--lime); background: rgba(214,245,70,0.05);
}}
div[data-testid="stButton"] button[kind="primary"] {{
    background: var(--lime);
    border-color: var(--lime);
    color: #0B0F0C;
    font-weight: 600;
    box-shadow: 4px 4px 0 rgba(214,245,70,0.25);
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{
    background: #E4FF66; color: #0B0F0C;
    transform: translate(-1px,-1px);
    box-shadow: 6px 6px 0 rgba(214,245,70,0.3);
}}
div[data-testid="stButton"] button:disabled {{
    border-color: var(--line2); color: var(--dim); background: transparent; box-shadow: none;
}}

/* metrics */
div[data-testid="stMetric"] {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-top: 3px solid var(--lime);
    border-radius: 0;
    padding: .85rem 1rem;
}}
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {{
    font: 600 9px/1.4 var(--mono) !important;
    letter-spacing: .2em !important; text-transform: uppercase;
    color: var(--dim) !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
    color: var(--ink) !important;
    font-family: var(--mono) !important;
    font-weight: 600;
}}

/* tabs */
div[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid var(--line);
    gap: 0;
}}
div[data-testid="stTabs"] [role="tab"] {{
    color: var(--dim);
    border-radius: 0;
    padding: .8rem 1.1rem;
    font: 600 11px/1 var(--mono);
    letter-spacing: .16em; text-transform: uppercase;
}}
div[data-testid="stTabs"] [role="tab"] p {{
    font: inherit !important; color: inherit !important; letter-spacing: inherit;
}}
div[data-testid="stTabs"] [aria-selected="true"] {{ color: var(--lime); }}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color: var(--lime); height: 2px; }}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {{ background-color: var(--line); }}

/* expander */
[data-testid="stExpander"] {{
    border: 1px dashed var(--line) !important;
    border-radius: 0 !important;
    background: var(--panel2);
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{ padding: .7rem 1rem; }}
[data-testid="stExpander"] summary p {{
    font: 600 11px/1.4 var(--mono) !important;
    letter-spacing: .16em; text-transform: uppercase;
    color: var(--mut) !important;
}}
[data-testid="stExpander"] summary:hover p {{ color: var(--lime) !important; }}
/* replace the material icon ligature with a text glyph so the label can
   never be overlapped by raw icon text when the icon font is slow/blocked */
[data-testid="stExpander"] summary span[data-testid="stIconMaterial"] {{
    font-size: 0 !important;
    width: 1rem; height: 1rem;
    display: inline-flex; align-items: center; justify-content: center;
    flex: none;
}}
[data-testid="stExpander"] summary span[data-testid="stIconMaterial"]::after {{
    content: "+";
    font: 600 14px/1 var(--mono);
    color: var(--lime);
}}
[data-testid="stExpander"] details[open] summary span[data-testid="stIconMaterial"]::after {{
    content: "–";
}}

/* dataframes / editors */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid var(--line);
    border-radius: 0;
    overflow: hidden;
}}

/* slider */
div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background: var(--lime); border-radius: 0;
    box-shadow: none;
}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{
    font-family: var(--mono) !important; color: var(--lime) !important;
}}
div[data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
div[data-testid="stSlider"] [data-testid="stSliderTickBarMax"] {{
    font-family: var(--mono) !important; color: var(--dim) !important;
}}

/* alerts + captions */
.stAlert, div[data-testid="stAlert"] {{
    border-radius: 0;
    background: var(--panel) !important;
    border: 1px solid rgba(232,196,107,0.4);
    color: var(--ink);
}}
div[data-testid="stAlert"] p {{ color: var(--ink) !important; font-family: var(--body); }}
div[data-testid="stCaptionContainer"] p {{
    color: var(--dim) !important;
    font: 500 11px/1.6 var(--mono) !important;
}}
[data-testid="stMarkdownContainer"] h4 {{
    font: 600 12px/1.3 var(--mono);
    letter-spacing: .2em; text-transform: uppercase;
    color: var(--mut);
}}

/* spinner */
[data-testid="stSpinner"] p {{ font-family: var(--mono) !important; color: var(--lime) !important; }}

/* ---------- bespoke blocks ---------- */
.fieldnote {{
    border-left: 3px solid var(--lime);
    background: var(--panel);
    padding: .7rem .95rem;
    margin: .2rem 0 1rem;
    font: 500 13.5px/1.55 var(--serif); font-style: italic;
    color: var(--mut);
}}
.lineup-meta {{
    font: 500 10px/1.6 var(--mono);
    letter-spacing: .1em; text-transform: uppercase;
    color: var(--dim);
    border-top: 1px dashed var(--line);
    padding-top: .5rem;
    margin: .1rem 0 .9rem;
}}
.lineup-meta b {{ color: var(--lime); }}

/* scorecard tables */
.sheetwrap {{
    width: 100%; max-height: 520px; overflow: auto;
    border: 1px solid var(--line);
    background: var(--panel2);
    margin: .3rem 0 1rem;
    scrollbar-width: thin; scrollbar-color: #2A3226 transparent;
}}
table.sheet {{ width: 100%; border-collapse: collapse; }}
table.sheet th {{
    position: sticky; top: 0; z-index: 1;
    background: #10150F;
    color: var(--dim);
    font: 600 9px/1.4 var(--mono);
    letter-spacing: .2em; text-transform: uppercase;
    text-align: left;
    padding: .6rem .75rem;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}}
table.sheet td {{
    font: 500 12.5px/1.4 var(--mono);
    color: var(--ink);
    padding: .55rem .75rem;
    border-bottom: 1px solid var(--line2);
    white-space: nowrap;
}}
table.sheet tr:hover td {{ background: rgba(214,245,70,0.04); }}

/* verdict strip on results page */
.verdict {{
    border: 1px solid var(--line);
    background: var(--panel2);
    padding: 1.1rem 1.3rem;
    margin: 0 0 1rem;
    display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
}}
.verdict .vk {{
    font: 600 9px/1.6 var(--mono); letter-spacing: .26em;
    text-transform: uppercase; color: var(--dim);
}}
.verdict .vh {{
    font: 400 clamp(1.5rem, 3.4vw, 2.4rem)/1 var(--disp);
    letter-spacing: .02em; text-transform: uppercase;
}}
.verdict .vh em {{ font-style: normal; color: var(--lime); }}

/* win probability tug bar */
.tug {{ margin: .4rem 0 1.2rem; }}
.tugbar {{
    display: flex; height: 34px;
    border: 1px solid var(--line);
    overflow: hidden;
}}
.tugbar .a {{ background: {PALETTE["lime"]}; }}
.tugbar .t {{ background: {PALETTE["gold"]}; }}
.tugbar .b {{ background: {PALETTE["orange"]}; }}
.tugbar div {{ transition: width .6s ease; }}
.tuglbl {{
    display: flex; justify-content: space-between; gap: 10px;
    font: 600 10px/1 var(--mono); letter-spacing: .14em; text-transform: uppercase;
    color: var(--mut); padding-top: 7px;
}}
.tuglbl b {{ color: var(--ink); }}

.inn-head {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
    border: 1px solid var(--line);
    border-left: 4px solid var(--lime);
    background: var(--panel);
    padding: .7rem 1rem;
    margin: .4rem 0 .8rem;
}}
.inn-head.second {{ border-left-color: var(--org); }}
.inn-head h3 {{ margin: 0; font: 400 1.1rem/1 var(--disp); letter-spacing: .04em; text-transform: uppercase; }}
.inn-head .sc {{ font: 600 14px/1 var(--mono); color: var(--lime); white-space: nowrap; }}
.inn-head.second .sc {{ color: var(--org); }}

/* model notes cards */
.mcard {{
    border: 1px solid var(--line);
    border-top: 3px solid var(--lime);
    background: var(--panel2);
    padding: 1.1rem 1.2rem;
    min-height: 12rem;
}}
.mcard .mk {{ font: 600 9px/1 var(--mono); letter-spacing: .26em; text-transform: uppercase; color: var(--lime); }}
.mcard h3 {{ font: 400 1.15rem/1.25 var(--disp); letter-spacing: .03em; text-transform: uppercase; margin: .6rem 0 .5rem; }}
.mcard p {{ font: 500 13.5px/1.6 var(--serif); font-style: italic; color: var(--mut); }}
.factgrid {{
    display: grid; grid-template-columns: 1fr auto; gap: .4rem 1rem;
    margin-top: .8rem;
    font: 500 11px/1.5 var(--mono);
}}
.factgrid span:nth-child(odd) {{ color: var(--dim); letter-spacing: .1em; text-transform: uppercase; font-size: 9px; align-self: center; }}
.factgrid span:nth-child(even) {{ text-align: right; color: var(--ink); }}

.support-row {{
    display: grid; grid-template-columns: 12rem 1fr; gap: 1rem;
    padding: .8rem 0;
    border-bottom: 1px dashed var(--line2);
}}
.support-row strong {{
    font: 600 10px/1.6 var(--mono); letter-spacing: .16em; text-transform: uppercase;
    color: var(--ink);
}}
.support-row span {{ font: 500 13px/1.6 var(--serif); font-style: italic; color: var(--mut); }}

/* footer */
.footer {{
    border-top: 1px solid var(--line);
    margin-top: 3.4rem; padding-top: 1rem;
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    font: 500 10px/1.7 var(--mono); letter-spacing: .14em; text-transform: uppercase;
    color: var(--dim);
}}
.footer b {{ color: var(--ink); }}
.footer a {{ color: var(--mut); text-decoration: none; border-bottom: 1px solid var(--line); padding-bottom: 1px; }}
.footer a:hover {{ color: var(--lime); border-color: var(--lime); }}
.footer .social {{ display: inline-flex; gap: .6rem; margin-left: .8rem; }}

@media (max-width: 760px) {{
    .mh-right {{ display: none; }}
    .hero .h1 {{ font-size: 2.4rem; }}
    .sect {{ flex-wrap: wrap; }}
    .sect .note {{ margin-left: 0; text-align: left; width: 100%; }}
    .support-row {{ grid-template-columns: 1fr; gap: .25rem; }}
    .footer {{ display: block; }}
}}
</style>
"""
