"""Global design system for the CricPredAI app.

Dala language: a pure-black void where content floats with no cards or
borders. Hierarchy comes from type scale (never weight — headlines are
always 400), secondary voice from grays. One violet marks every
interactive moment: filled primary pills, sliding segmented-control
active states, and the particle system. Saffron is a small-emphasis
ink only. Content gets whitespace; only controls get boxes.
"""

PALETTE = {
    "bg": "#000000",          # void
    "ink": "#ffffff",         # bone white
    "ash": "#9a9a9a",
    "silver": "#bdbdbd",
    "iris": "#8052ff",        # electric iris — interactive only
    "saffron": "#ffb829",     # small emphasis only
    "verdant": "#15846e",
    "ctrl_border": "rgba(255,255,255,0.14)",
}

# generic keys used by chart call-sites
PALETTE["muted"] = PALETTE["ash"]
PALETTE["dim"] = "#6b6b6b"
PALETTE["line"] = "rgba(255,255,255,0.10)"
PALETTE["line2"] = "rgba(255,255,255,0.06)"
PALETTE["blue"] = PALETTE["iris"]      # first innings series
PALETTE["mist"] = PALETTE["silver"]    # second innings series
PALETTE["red"] = PALETTE["saffron"]    # wicket markers
PALETTE["gold"] = PALETTE["saffron"]


APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500&family=Inter:wght@200;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    /* colors */
    --void: {PALETTE["bg"]};
    --bone: {PALETTE["ink"]};
    --ash: {PALETTE["ash"]};
    --silver: {PALETTE["silver"]};
    --iris: {PALETTE["iris"]};
    --saffron: {PALETTE["saffron"]};
    --verdant: {PALETTE["verdant"]};
    --ctrl-border: {PALETTE["ctrl_border"]};

    /* families: exactly what the project already loads */
    --disp: "Space Grotesk", "Inter", ui-sans-serif, system-ui, sans-serif;
    --sans: "Inter", ui-sans-serif, system-ui, sans-serif;
    --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

    /* type scale */
    --text-caption: 12px;      --leading-caption: 1.5;
    --text-nav-label: 14px;    --leading-nav-label: 1.2;  --tracking-nav-label: 0.35px;
    --text-body: 18px;         --leading-body: 1.5;
    --text-heading-2xs: 24px;  --leading-heading-2xs: 1.25;
    --text-heading-xs: 27px;   --leading-heading-xs: 1;
    --text-subheading: 36px;   --leading-subheading: 1.2;
    --text-heading-sm: 42px;   --leading-heading-sm: 1.2;  --tracking-heading-sm: -1.68px;
    --text-heading: 48px;      --leading-heading: 1.1;     --tracking-heading: -1.68px;
    --text-heading-lg: 78px;   --leading-heading-lg: 1.1;  --tracking-heading-lg: -3.12px;
    --text-display: 113px;     --leading-display: 1.1;     --tracking-display: -4.52px;

    /* spacing, base 6px */
    --sp-6: 6px; --sp-12: 12px; --sp-18: 18px; --sp-24: 24px;
    --sp-30: 30px; --sp-36: 36px; --sp-60: 60px; --sp-96: 96px; --sp-120: 120px;

    --page-max-width: 1280px;
    --radius-3xl: 24px;
    --radius-full: 9999px;
    --t-ui: 150ms ease-out;
    --t-slide: 250ms cubic-bezier(0.4, 0, 0.2, 1);
}}

/* ---------- shell: the void ---------- */
.stApp {{
    background:
        radial-gradient(ellipse at 75% 8%, rgba(128,82,255,0.05), transparent 55%),
        radial-gradient(ellipse at 12% 85%, rgba(21,132,110,0.04), transparent 60%),
        var(--void);
    color: var(--silver);
}}
header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{
    max-width: var(--page-max-width);
    padding-top: var(--sp-24);
    padding-bottom: var(--sp-120);
}}
.stApp, .stApp p, .stApp li {{ font-family: var(--sans); }}
h1, h2, h3, h4 {{ color: var(--bone); font-family: var(--disp); font-weight: 400; }}

[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded" !important;
    font-weight: normal !important; font-style: normal !important;
    letter-spacing: normal !important; text-transform: none !important;
    -webkit-font-feature-settings: "liga" !important; font-feature-settings: "liga" !important;
}}

/* ---------- masthead: floating, no bar ---------- */
.masthead {{
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: var(--sp-6) 2px var(--sp-24);
}}
.mh-brand {{ display: flex; align-items: center; gap: 10px; }}
.mh-dot {{
    width: 6px; height: 6px; border-radius: var(--radius-full);
    background: var(--iris); flex: none;
    animation: pulse 2.4s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}
.mh-name {{
    font: 600 var(--text-nav-label)/1 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    color: var(--bone);
}}
.mh-name span {{ color: var(--ash); font-weight: 600; }}
.mh-right {{
    font: 400 var(--text-caption)/1.5 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash); text-align: right;
}}
.mh-right b {{ color: var(--silver); font-weight: 400; }}

/* ---------- nav & radios → boxed segmented controls, sliding violet ---------- */
div[data-testid="stRadio"] > div[role="radiogroup"] {{
    position: relative;
    display: inline-grid;
    grid-auto-flow: column;
    grid-auto-columns: 1fr;
    gap: 0;
    border: 1px solid var(--ctrl-border);
    border-radius: var(--radius-3xl);
    padding: 5px;
    background: transparent;
    --segs: 3; --seg-i: 0;
}}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(2):last-child) {{ --segs: 2; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(3):last-child) {{ --segs: 3; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(4):last-child) {{ --segs: 4; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(1) input:checked) {{ --seg-i: 0; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(2) input:checked) {{ --seg-i: 1; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(3) input:checked) {{ --seg-i: 2; }}
div[data-testid="stRadio"] [role="radiogroup"]:has(> label:nth-child(4) input:checked) {{ --seg-i: 3; }}
div[data-testid="stRadio"] [role="radiogroup"]::before {{
    content: "";
    position: absolute;
    top: 5px; bottom: 5px; left: 5px;
    width: calc((100% - 10px) / var(--segs));
    background: var(--iris);
    border-radius: calc(var(--radius-3xl) - 5px);
    transform: translateX(calc(var(--seg-i) * 100%));
    transition: transform var(--t-slide);
}}
div[data-testid="stRadio"] [role="radiogroup"] > label {{
    position: relative; z-index: 1;
    display: flex; align-items: center; justify-content: center;
    border: none; background: transparent;
    border-radius: calc(var(--radius-3xl) - 5px);
    padding: 11px 22px;
    margin: 0;
    min-height: 44px;
    cursor: pointer;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label p {{
    font: 600 var(--text-nav-label)/1.2 var(--sans) !important;
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    color: var(--ash) !important;
    transition: color var(--t-ui);
    white-space: nowrap;
}}
div[data-testid="stRadio"] [role="radiogroup"] > label:hover p {{ color: var(--bone) !important; }}
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {{ color: #ffffff !important; }}
div[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {{ display: none; }}

/* ---------- tabs → boxed segmented control (baseweb highlight slides) ---------- */
div[data-testid="stTabs"] [role="tablist"] {{
    position: relative;
    display: inline-flex;
    border: 1px solid var(--ctrl-border) !important;
    border-radius: var(--radius-3xl);
    padding: 5px;
    gap: 0;
    background: transparent;
}}
div[data-testid="stTabs"] [role="tab"] {{
    position: relative; z-index: 1;
    color: var(--ash);
    border-radius: calc(var(--radius-3xl) - 5px);
    padding: 10px 22px;
    font: 600 var(--text-nav-label)/1.2 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    transition: color var(--t-ui);
    min-height: 34px;
}}
div[data-testid="stTabs"] [role="tab"] p {{
    font: inherit !important; color: inherit !important; letter-spacing: inherit;
}}
div[data-testid="stTabs"] [role="tab"]:hover {{ color: var(--bone); }}
div[data-testid="stTabs"] [aria-selected="true"] {{ color: #ffffff; }}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--iris);
    height: calc(100% - 10px) !important;
    top: 5px !important;
    border-radius: calc(var(--radius-3xl) - 5px);
    z-index: 0;
    transition: all var(--t-slide) !important;
}}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none; }}

/* ---------- typography helpers ---------- */
label, div[data-testid="stWidgetLabel"] p {{
    font: 600 var(--text-caption)/1.5 var(--sans) !important;
    letter-spacing: var(--tracking-nav-label) !important; text-transform: uppercase;
    color: var(--ash) !important;
}}

/* ---------- inputs: interactive → boxed ---------- */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    border-radius: var(--radius-3xl) !important;
    background: transparent !important;
    border-color: var(--ctrl-border) !important;
    color: var(--bone) !important;
    font-family: var(--sans);
    font-size: 14px;
    min-height: 44px;
    transition: border-color var(--t-ui);
}}
div[data-baseweb="select"] > div {{
    border-radius: var(--radius-3xl) !important;
    border-color: var(--ctrl-border) !important;
    background: transparent !important;
}}
div[data-baseweb="select"] > div:hover,
div[data-testid="stTextInput"] input:hover {{ border-color: rgba(255,255,255,0.4) !important; }}
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{
    color: var(--bone) !important;
}}
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {{
    background: #000000 !important;
    border: 1px solid var(--ctrl-border) !important;
    border-radius: 16px !important;
    box-shadow: none !important;
}}
ul[role="listbox"] li {{ background: transparent !important; color: var(--silver) !important; }}
div[role="option"], li[role="option"] {{ color: var(--silver) !important; background: transparent !important; }}
div[role="option"]:hover, li[role="option"]:hover,
li[aria-selected="true"] {{ background: rgba(128,82,255,0.18) !important; color: #ffffff !important; }}
[data-baseweb="tag"] {{
    background: transparent !important;
    border: 1px solid var(--ctrl-border) !important;
    border-radius: var(--radius-full) !important;
    color: var(--silver) !important;
}}
[data-baseweb="tag"] span, [data-baseweb="tag"] div {{
    color: var(--silver) !important;
    font-family: var(--sans);
    font-size: 12.5px;
}}
[data-baseweb="tag"] svg, [data-baseweb="tag"] [role="presentation"] {{ fill: var(--ash) !important; color: var(--ash) !important; }}
input:disabled {{ -webkit-text-fill-color: var(--ash) !important; opacity: 1 !important; }}

/* ---------- buttons ---------- */
/* primary: the one filled violet pill per view */
div[data-testid="stButton"] button[kind="primary"] {{
    background: var(--iris);
    border: none;
    border-radius: 22.5px;
    height: 45px; min-height: 45px;
    color: #ffffff;
    font: 600 var(--text-nav-label)/1.2 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    padding-left: var(--sp-30); padding-right: var(--sp-30);
    transition: background var(--t-ui), transform var(--t-ui);
    box-shadow: none;
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{
    background: #916bff; color: #ffffff;
}}
div[data-testid="stButton"] button[kind="primary"]:disabled {{
    background: rgba(128,82,255,0.25); color: rgba(255,255,255,0.5);
}}
/* secondary: bare text links, no border, no background */
div[data-testid="stButton"] button:not([kind="primary"]),
div[data-testid="stDownloadButton"] button {{
    border: none;
    background: transparent;
    border-radius: 22.5px;
    color: var(--ash);
    font: 600 var(--text-nav-label)/1.2 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    min-height: 44px;
    padding-left: var(--sp-12); padding-right: var(--sp-12);
    transition: color var(--t-ui);
    box-shadow: none;
}}
div[data-testid="stButton"] button:not([kind="primary"]):hover,
div[data-testid="stDownloadButton"] button:hover {{
    color: var(--bone); background: transparent; border: none;
}}
div[data-testid="stButton"] button:not([kind="primary"]):disabled {{
    color: rgba(255,255,255,0.22); background: transparent;
}}
div[data-testid="stButton"] button p {{ font: inherit !important; }}

/* ---------- metrics: content floats, no boxes ---------- */
div[data-testid="stMetric"] {{
    background: transparent;
    border: none;
    padding: var(--sp-12) 0;
}}
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {{
    font: 600 var(--text-caption)/1.5 var(--sans) !important;
    letter-spacing: var(--tracking-nav-label) !important; text-transform: uppercase;
    color: var(--ash) !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
    color: var(--bone) !important;
    font-family: var(--mono) !important;
    font-feature-settings: "tnum" 1, "zero" 1;
    font-weight: 400;
}}

/* ---------- expander: interactive → boxed ---------- */
[data-testid="stExpander"] {{
    border: 1px solid var(--ctrl-border) !important;
    border-radius: var(--radius-3xl) !important;
    background: transparent;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{ padding: var(--sp-12) var(--sp-24); min-height: 44px; }}
[data-testid="stExpander"] summary p {{
    font: 600 var(--text-caption)/1.5 var(--sans) !important;
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    color: var(--ash) !important;
    transition: color var(--t-ui);
}}
[data-testid="stExpander"] summary:hover p {{ color: var(--bone) !important; }}
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
    font: 400 13px/1 var(--mono);
    color: var(--ash);
}}
[data-testid="stExpander"] details[open] summary span[data-testid="stIconMaterial"]::after {{
    content: "–";
}}

/* dataframes / editors: interactive grids keep a control box */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid var(--ctrl-border);
    border-radius: var(--radius-3xl);
    overflow: hidden;
}}

/* slider */
div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background: var(--iris); border-radius: var(--radius-full);
    box-shadow: none;
    width: 18px; height: 18px;
}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{
    font-family: var(--mono) !important; font-size: 12px !important;
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone) !important;
}}
div[data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
div[data-testid="stSlider"] [data-testid="stSliderTickBarMax"] {{
    font-family: var(--mono) !important; font-size: 11px !important;
    color: var(--ash) !important;
}}

/* alerts + captions: float, no boxes */
.stAlert, div[data-testid="stAlert"] {{
    border-radius: 0;
    background: transparent !important;
    border: none;
    border-left: 2px solid var(--saffron);
    color: var(--silver);
}}
div[data-testid="stAlert"] p {{ color: var(--silver) !important; font-family: var(--sans); font-size: 14px; }}
div[data-testid="stCaptionContainer"] p {{
    color: var(--ash) !important;
    font: 400 var(--text-caption)/1.7 var(--mono) !important;
    font-feature-settings: "tnum" 1, "zero" 1;
}}
[data-testid="stMarkdownContainer"] h4 {{
    font: 600 var(--text-caption)/1.5 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    color: var(--ash);
}}

/* spinner */
[data-testid="stSpinner"] p {{
    font-family: var(--mono) !important; font-size: 12px !important;
    color: var(--ash) !important;
}}

/* ---------- hero ---------- */
.hero {{
    position: relative;
    padding: var(--sp-60) 0 var(--sp-36);
}}
.hero .eyebrow {{
    font: 600 var(--text-caption)/1.5 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    color: var(--saffron);
    margin-bottom: var(--sp-30);
}}
.hero .h1 {{
    font: 400 clamp(48px, 8vw, var(--text-display))/var(--leading-display) var(--disp);
    letter-spacing: -0.04em;
    color: var(--bone); margin: 0; max-width: 720px;
}}
.hero .copy {{
    margin-top: var(--sp-30); max-width: 520px;
    font: 200 var(--text-body)/var(--leading-body) var(--sans);
    color: var(--silver);
}}
.hero .herostats {{
    display: flex; gap: var(--sp-60); flex-wrap: wrap; margin-top: var(--sp-60);
}}
.hero .hs b {{
    display: block;
    font: 400 28px/1.1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone);
}}
.hero .hs span {{
    font: 400 var(--text-caption)/2.2 var(--sans);
    color: var(--ash);
}}

/* scroll-driven reveals — progressive enhancement, no-op elsewhere */
@supports (animation-timeline: view()) {{
    .sect, .inn-head, .verdict, .support-row,
    div[data-testid="stMetric"] {{
        animation: rise-in .3s ease-out both;
        animation-timeline: view();
        animation-range: entry 0% entry 45%;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .sect, .inn-head, .verdict, .support-row,
        div[data-testid="stMetric"] {{ animation: none; }}
    }}
}}
@keyframes rise-in {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: none; }}
}}

/* ---------- section headers: float on whitespace ---------- */
.sect {{
    display: flex; align-items: baseline; gap: var(--sp-18);
    padding: var(--sp-96) 0 var(--sp-18);
}}
.sect .no {{
    font: 600 var(--text-caption)/1.5 var(--sans);
    letter-spacing: var(--tracking-nav-label);
    color: var(--saffron);
}}
.sect h2 {{
    margin: 0;
    font: 400 var(--text-heading-sm)/var(--leading-heading-sm) var(--disp);
    letter-spacing: var(--tracking-heading-sm);
    color: var(--bone);
}}
.sect .note {{
    margin-left: auto;
    font: 400 var(--text-caption)/1.6 var(--sans);
    color: var(--ash); text-align: right;
}}

/* ---------- bespoke blocks: content floats ---------- */
.fieldnote {{
    padding: 0;
    margin: var(--sp-6) 0 var(--sp-24);
    font: 200 16px/1.6 var(--sans);
    color: var(--silver);
    max-width: 640px;
}}
.lineup-meta {{
    font: 400 var(--text-caption)/1.8 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash);
    padding-top: var(--sp-6);
    margin: var(--sp-6) 0 var(--sp-18);
}}
.lineup-meta b {{ color: var(--bone); font-weight: 400; }}

/* scorecard tables: content — no borders, whitespace separation */
.sheetwrap {{
    width: 100%; max-height: 520px; overflow: auto;
    margin: var(--sp-6) 0 var(--sp-30);
    scrollbar-width: thin; scrollbar-color: #2a2a2a transparent;
}}
table.sheet {{ width: 100%; border-collapse: collapse; }}
table.sheet th {{
    position: sticky; top: 0; z-index: 1;
    background: var(--void);
    color: var(--ash);
    font: 600 var(--text-caption)/1.5 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    text-align: left;
    padding: var(--sp-12) var(--sp-18) var(--sp-12) 0;
    white-space: nowrap;
}}
table.sheet td {{
    font: 400 13.5px/1.5 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--silver);
    padding: var(--sp-12) var(--sp-18) var(--sp-12) 0;
    white-space: nowrap;
}}
table.sheet td:first-child {{ color: var(--bone); }}
table.sheet tr:hover td {{ color: var(--bone); }}

/* verdict: floating type */
.verdict {{
    display: flex; align-items: flex-end; gap: var(--sp-36); flex-wrap: wrap;
    padding: var(--sp-24) 0 var(--sp-12);
}}
.verdict .vk {{
    font: 600 var(--text-caption)/2 var(--sans); letter-spacing: var(--tracking-nav-label);
    text-transform: uppercase; color: var(--saffron);
}}
.verdict .vh {{
    font: 400 var(--text-subheading)/var(--leading-subheading) var(--disp);
    letter-spacing: -0.02em;
    color: var(--bone);
}}
.verdict .vh em {{ font-style: normal; color: var(--bone); }}
.verdict .vp {{
    font: 400 42px/1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone);
}}
.verdict .vp small {{
    font: 200 16px/1 var(--sans); color: var(--ash);
    margin-right: var(--sp-12);
}}

/* win probability tug bar (content viz — thin, borderless) */
.tug {{ margin: var(--sp-6) 0 var(--sp-36); }}
.tugbar {{
    display: flex; height: 2px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}}
.tugbar .a {{ background: {PALETTE["iris"]}; }}
.tugbar .t {{ background: {PALETTE["dim"]}; }}
.tugbar .b {{ background: {PALETTE["silver"]}; }}
.tugbar div {{ transition: width 250ms cubic-bezier(0.4, 0, 0.2, 1); }}
.tuglbl {{
    display: flex; justify-content: space-between; gap: 10px;
    font: 400 var(--text-caption)/1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash); padding-top: var(--sp-12);
}}
.tuglbl b {{ color: var(--bone); font-weight: 400; }}

.inn-head {{
    display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-12);
    padding: var(--sp-30) 0 var(--sp-6);
}}
.inn-head h3 {{
    margin: 0;
    font: 400 var(--text-heading-xs)/1.2 var(--disp);
    letter-spacing: -0.01em;
    color: var(--bone);
}}
.inn-head h3 .n {{ color: var(--ash); }}
.inn-head .sc {{
    font: 400 13px/1.6 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash); white-space: nowrap;
}}
.inn-head .sc b {{ color: var(--bone); font-weight: 400; }}

/* model notes: floating columns, no cards */
.mcard {{
    border: none;
    background: transparent;
    padding: var(--sp-12) 0;
}}
.mcard .mk {{
    font: 600 var(--text-caption)/1.5 var(--sans); letter-spacing: var(--tracking-nav-label);
    text-transform: uppercase; color: var(--saffron);
}}
.mcard h3 {{
    font: 400 var(--text-heading-2xs)/var(--leading-heading-2xs) var(--disp);
    letter-spacing: -0.48px;
    color: var(--bone); margin: var(--sp-18) 0 var(--sp-12);
}}
.mcard p {{ font: 200 15px/1.6 var(--sans); color: var(--silver); }}
.factgrid {{
    display: grid; grid-template-columns: 1fr auto; gap: var(--sp-12) var(--sp-24);
    margin-top: var(--sp-24);
}}
.factgrid span:nth-child(odd) {{
    color: var(--ash);
    font: 600 11px/1.5 var(--sans);
    letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
    align-self: center;
}}
.factgrid span:nth-child(even) {{
    text-align: right; color: var(--bone);
    font: 400 14px/1.4 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
}}

.support-row {{
    display: grid; grid-template-columns: 13rem 1fr; gap: var(--sp-24);
    padding: var(--sp-18) 0;
}}
.support-row strong {{
    font: 600 var(--text-caption)/1.7 var(--sans); letter-spacing: var(--tracking-nav-label);
    text-transform: uppercase;
    color: var(--bone); font-weight: 600;
}}
.support-row span {{ font: 200 15px/1.65 var(--sans); color: var(--silver); }}

/* footer: floats */
.footer {{
    margin-top: var(--sp-120); padding-top: var(--sp-24);
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}}
.footer .stamp {{
    font: 400 var(--text-caption)/1.7 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash);
}}
.footer .who {{
    display: inline-flex; align-items: center; gap: var(--sp-18);
    font: 400 13px/1 var(--sans); color: var(--ash);
}}
.footer .who b {{ color: var(--silver); font-weight: 600; }}
.footer a.applogo {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 34px; height: 34px;
    border: 1px solid var(--ctrl-border); border-radius: var(--radius-full);
    opacity: .8;
    transition: border-color var(--t-ui), opacity var(--t-ui);
}}
.footer a.applogo:hover {{ border-color: var(--iris); opacity: 1; }}
.footer a.applogo img {{ width: 15px; height: 15px; display: block; }}

@media (max-width: 760px) {{
    .mh-right {{ display: none; }}
    .hero .h1 {{ font-size: 52px; letter-spacing: -2px; }}
    .hero .herostats {{ gap: var(--sp-30); }}
    .sect {{ flex-wrap: wrap; padding-top: var(--sp-60); }}
    .sect .note {{ margin-left: 0; text-align: left; width: 100%; }}
    .sect h2 {{ font-size: 32px; letter-spacing: -1px; }}
    .support-row {{ grid-template-columns: 1fr; gap: var(--sp-6); }}
    .footer {{ display: block; }}
    .verdict {{ gap: var(--sp-18); }}
    div[data-testid="stRadio"] > div[role="radiogroup"] {{ width: 100%; }}
    div[data-testid="stRadio"] [role="radiogroup"] > label {{ padding: 11px 4px; }}
    div[data-testid="stRadio"] [role="radiogroup"] > label p {{ font-size: 12px !important; letter-spacing: 0.2px; }}
    div[data-testid="stTabs"] [role="tab"] {{ padding: 10px 12px; font-size: 12px; }}
}}
</style>
"""
