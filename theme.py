"""Global design system for the CricPredAI app.

Floodlit night match rendered as a terminal: a pure black canvas, hairline
graphite borders standing in for boundary ropes, Space Grotesk headlines at
weight 400, Inter for anything a human wrote, JetBrains Mono for every
number the model produced. Floodlight Gold is the model's voice — it marks
predictions and nothing else. A strict semantic palette maps to ball
outcomes: wicket red, boundary blue, six violet, dot gray, run green,
uncertainty amber. Ghost buttons only. No fills, no shadows, no decoration.
"""

PALETTE = {
    "bg": "#000000",          # night sky
    "line": "#26292c",        # boundary rope — the only separator
    "ink": "#ffffff",         # sightscreen
    "bone": "#f0f0f0",
    "ash": "#a1a4a5",
    "smoke": "#7d8288",
    "pitch": "#191512",       # pitch strip — allowed only inside visuals
    "gold": "#ffc72c",        # floodlight gold — model output only
    "goldglow": "#ffd968",
    "red": "#ff5c5c",         # wicket
    "blue": "#4da3ff",        # four
    "violet": "#a78bfa",      # six
    "dotgray": "#565b60",     # dot ball
    "green": "#3ad389",       # runs flow / model hit / live
    "amber": "#ff9f45",       # uncertainty
}

# keys some call-sites still reference generically
PALETTE["muted"] = PALETTE["ash"]
PALETTE["dim"] = PALETTE["smoke"]
PALETTE["mist"] = PALETTE["bone"]
PALETTE["line2"] = PALETTE["line"]


def pitch_constellation(seed: int = 11) -> str:
    """The signature visual: a perspective pitch plane scattered with
    delivery dots from the training corpus, colored by outcome, drifting
    almost imperceptibly. Pure SVG, no dependencies."""
    import random

    rng = random.Random(seed)
    # perspective trapezoid: narrow at top (far end), wide at bottom
    top_y, bot_y = 40.0, 420.0
    top_x0, top_x1 = 210.0, 350.0
    bot_x0, bot_x1 = 60.0, 500.0

    outcome_colors = [
        (PALETTE["dotgray"], 0.42),   # dot balls dominate
        (PALETTE["bone"], 0.30),      # running singles/twos
        (PALETTE["blue"], 0.14),      # fours
        (PALETTE["violet"], 0.06),    # sixes
        (PALETTE["red"], 0.08),       # wickets
    ]

    def pick_color():
        r = rng.random()
        acc = 0.0
        for color, weight in outcome_colors:
            acc += weight
            if r <= acc:
                return color
        return PALETTE["dotgray"]

    layers = {0: [], 1: [], 2: []}
    for _ in range(520):
        v = rng.random() ** 0.72          # bias toward the near (bottom) end
        y = top_y + v * (bot_y - top_y)
        x0 = top_x0 + v * (bot_x0 - top_x0)
        x1 = top_x1 + v * (bot_x1 - top_x1)
        u = rng.random()
        # cluster on and around the strip, thin toward edges
        u = 0.5 + (u - 0.5) * (0.35 + 0.65 * rng.random())
        x = x0 + u * (x1 - x0)
        r = 1.1 + 1.6 * v * rng.random()
        color = pick_color()
        op = 0.25 + 0.6 * v * rng.random()
        layers[rng.randrange(3)].append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{color}" opacity="{op:.2f}"/>'
        )

    plane = (
        f'<path d="M {top_x0:.0f} {top_y:.0f} L {top_x1:.0f} {top_y:.0f} '
        f'L {bot_x1:.0f} {bot_y:.0f} L {bot_x0:.0f} {bot_y:.0f} Z" '
        f'fill="{PALETTE["pitch"]}" opacity="0.85"/>'
        # crease lines, hairline
        f'<line x1="{top_x0 + 8:.0f}" y1="{top_y + 26:.0f}" x2="{top_x1 - 8:.0f}" y2="{top_y + 26:.0f}" stroke="{PALETTE["line"]}" stroke-width="1"/>'
        f'<line x1="{bot_x0 + 24:.0f}" y1="{bot_y - 42:.0f}" x2="{bot_x1 - 24:.0f}" y2="{bot_y - 42:.0f}" stroke="{PALETTE["line"]}" stroke-width="1"/>'
    )
    groups = "".join(
        f'<g class="drift{i}">{"".join(dots)}</g>' for i, dots in layers.items()
    )
    return (
        '<svg class="constellation" viewBox="0 0 560 440" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        "<style>"
        ".drift0{animation:cdrift 26s ease-in-out infinite}"
        ".drift1{animation:cdrift 34s ease-in-out infinite reverse}"
        ".drift2{animation:cdrift 44s ease-in-out infinite}"
        "@keyframes cdrift{0%,100%{transform:translate(0,0)}50%{transform:translate(0,-9px)}}"
        "@media (prefers-reduced-motion: reduce){.drift0,.drift1,.drift2{animation:none}}"
        "</style>"
        + plane
        + groups
        + "</svg>"
    )


APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    --bg: {PALETTE["bg"]};
    --line: {PALETTE["line"]};
    --ink: {PALETTE["ink"]};
    --bone: {PALETTE["bone"]};
    --ash: {PALETTE["ash"]};
    --smoke: {PALETTE["smoke"]};
    --gold: {PALETTE["gold"]};
    --goldglow: {PALETTE["goldglow"]};
    --red: {PALETTE["red"]};
    --blue: {PALETTE["blue"]};
    --violet: {PALETTE["violet"]};
    --green: {PALETTE["green"]};
    --amber: {PALETTE["amber"]};
    --disp: "Space Grotesk", "Inter", ui-sans-serif, system-ui, sans-serif;
    --sans: "Inter", ui-sans-serif, system-ui, sans-serif;
    --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    --glow-live: 0 0 24px rgba(255, 199, 44, 0.18);
    --t-ui: 150ms ease-out;
}}

/* ---------- shell ---------- */
.stApp {{ background: var(--bg); color: var(--bone); }}
header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{
    max-width: 1200px;
    padding-top: 1.2rem;
    padding-bottom: 6rem;
}}
.stApp, .stApp p, .stApp li {{ font-family: var(--sans); }}
h1, h2, h3, h4 {{ color: var(--ink); font-family: var(--disp); font-weight: 400; }}

[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded" !important;
    font-weight: normal !important; font-style: normal !important;
    letter-spacing: normal !important; text-transform: none !important;
    -webkit-font-feature-settings: "liga" !important; font-feature-settings: "liga" !important;
}}

/* ---------- masthead ---------- */
.masthead {{
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 8px 2px 18px;
    margin-bottom: 6px;
}}
.mh-brand {{ display: flex; align-items: center; gap: 10px; }}
.mh-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--green); flex: none;
    animation: pulse 2.4s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}
.mh-name {{
    font: 500 16px/1 var(--disp);
    color: var(--ink); letter-spacing: -0.01em;
}}
.mh-name span {{ color: var(--ash); font-weight: 400; }}
.mh-right {{
    font: 400 12px/1.6 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--smoke); text-align: right;
}}
.mh-right b {{ color: var(--ash); font-weight: 400; }}

/* ---------- nav (radio → quiet text links) ---------- */
div[data-testid="stRadio"] > div {{ gap: 22px; }}
div[data-testid="stRadio"] label {{
    border: none; background: transparent;
    border-radius: 6px;
    padding: 6px 2px;
    transition: color var(--t-ui);
}}
div[data-testid="stRadio"] label p {{
    font: 400 14px/1 var(--sans) !important;
    color: var(--ash) !important;
    transition: color var(--t-ui);
}}
div[data-testid="stRadio"] label:hover p {{ color: var(--ink) !important; }}
div[data-testid="stRadio"] label:has(input:checked) p {{
    color: var(--ink) !important; font-weight: 500 !important;
}}
div[data-testid="stRadio"] label > div:first-child {{ display: none; }}

/* ---------- hero ---------- */
.hero {{
    position: relative;
    padding: clamp(3.4rem, 7vw, 6rem) 0 clamp(2.2rem, 4vw, 3.4rem);
    overflow: visible;
}}
.hero .constellation {{
    position: fixed; right: 0; top: 7vh;
    width: min(44vw, 560px); height: auto;
    pointer-events: none;
    opacity: .9;
}}
.hero .eyebrow {{
    font: 400 12px/1 var(--mono);
    color: var(--smoke);
    margin-bottom: 28px;
}}
.hero .h1 {{
    position: relative;
    font: 400 clamp(3rem, 6.6vw, 5.5rem)/1.0 var(--disp);
    letter-spacing: -0.04em;
    color: var(--ink); margin: 0; max-width: 720px;
}}
.hero .copy {{
    position: relative;
    margin-top: 26px; max-width: 520px;
    font: 400 16px/1.6 var(--sans);
    color: var(--ash);
}}
.hero .herostats {{
    position: relative;
    display: flex; gap: 0; flex-wrap: wrap; margin-top: 44px;
}}
.hero .hs {{
    padding: 0 32px;
    border-left: 1px solid var(--line);
}}
.hero .hs:first-child {{ padding-left: 0; border-left: none; }}
.hero .hs b {{
    display: block;
    font: 400 28px/1.1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone); font-weight: 400;
}}
.hero .hs span {{
    font: 400 12px/2.4 var(--sans);
    color: var(--smoke);
}}

/* scroll cue */
.scrollcue {{
    display: flex; flex-direction: column; align-items: flex-start; gap: 12px;
    margin-top: 56px;
}}
.scrollcue span {{
    font: 400 12px/1 var(--mono);
    color: var(--smoke);
}}
.scrollcue i {{
    display: block; width: 1px; height: 48px;
    margin-left: 2px;
    background: linear-gradient(to bottom, var(--smoke), transparent);
    transform-origin: top;
    animation: cue 2.8s ease-out infinite;
}}
@keyframes cue {{
    0% {{ transform: scaleY(0); opacity: 0; }}
    35% {{ transform: scaleY(1); opacity: 1; }}
    100% {{ transform: scaleY(1); opacity: 0; }}
}}
@media (prefers-reduced-motion: reduce) {{
    .scrollcue i, .mh-dot {{ animation: none; }}
}}

/* scroll-driven reveals — progressive enhancement, no-op elsewhere */
@supports (animation-timeline: view()) {{
    .sect, .mcard, .inn-head, .verdict, .support-row,
    div[data-testid="stMetric"] {{
        animation: rise-in .7s ease-out both;
        animation-timeline: view();
        animation-range: entry 0% entry 55%;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .sect, .mcard, .inn-head, .verdict, .support-row,
        div[data-testid="stMetric"] {{ animation: none; }}
    }}
}}
@keyframes rise-in {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to {{ opacity: 1; transform: none; }}
}}

/* ---------- section headers ---------- */
.sect {{
    display: flex; align-items: baseline; gap: 16px;
    border-top: 1px solid var(--line);
    padding: 2.6rem 0 1.1rem;
    margin-top: 2.6rem; margin-bottom: .8rem;
}}
.sect .no {{
    font: 400 12px/1 var(--mono); color: var(--smoke);
    font-feature-settings: "tnum" 1, "zero" 1;
}}
.sect h2 {{
    margin: 0;
    font: 400 clamp(1.6rem, 3vw, 2.1rem)/1.15 var(--disp);
    letter-spacing: -0.02em;
    color: var(--ink);
}}
.sect .note {{
    margin-left: auto;
    font: 400 12px/1.6 var(--sans);
    color: var(--smoke); text-align: right;
}}

/* ---------- widgets ---------- */
label, div[data-testid="stWidgetLabel"] p {{
    font: 500 12px/1.5 var(--sans) !important;
    letter-spacing: .04em !important; text-transform: uppercase;
    color: var(--ash) !important;
}}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    border-radius: 6px !important;
    background: var(--bg) !important;
    border-color: var(--line) !important;
    color: var(--bone) !important;
    font-family: var(--sans);
    font-size: 14px;
    transition: border-color var(--t-ui);
}}
div[data-baseweb="select"] > div {{ border-radius: 6px !important; border-color: var(--line) !important; background: var(--bg) !important; }}
div[data-baseweb="select"] > div:hover,
div[data-testid="stTextInput"] input:hover {{ border-color: var(--smoke) !important; }}
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{
    color: var(--bone) !important;
}}
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {{
    background: #000000 !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    box-shadow: none !important;
}}
ul[role="listbox"] li {{ background: transparent !important; color: var(--bone) !important; }}
div[role="option"], li[role="option"] {{ color: var(--bone) !important; background: transparent !important; }}
div[role="option"]:hover, li[role="option"]:hover,
li[aria-selected="true"] {{ background: rgba(255,255,255,0.05) !important; color: var(--ink) !important; }}
[data-baseweb="tag"] {{
    background: transparent !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    color: var(--bone) !important;
}}
[data-baseweb="tag"] span, [data-baseweb="tag"] div {{
    color: var(--bone) !important;
    font-family: var(--sans);
    font-size: 12.5px;
}}
[data-baseweb="tag"] svg, [data-baseweb="tag"] [role="presentation"] {{ fill: var(--ash) !important; color: var(--ash) !important; }}
input:disabled {{ -webkit-text-fill-color: var(--ash) !important; opacity: 1 !important; }}

/* buttons: every button on the site is the same ghost button */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{
    border-radius: 6px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink);
    font: 500 14px/1.2 var(--sans);
    min-height: 2.6rem;
    padding-left: 1.3rem; padding-right: 1.3rem;
    transition: border-color var(--t-ui);
    box-shadow: none;
}}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {{
    border-color: var(--ink); color: var(--ink); background: transparent;
}}
div[data-testid="stButton"] button[kind="primary"] {{
    background: transparent;
    border-color: var(--ash);
    color: var(--ink);
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{
    background: transparent; border-color: var(--ink); color: var(--ink);
}}
div[data-testid="stButton"] button:disabled {{
    border-color: var(--line); color: var(--smoke); background: transparent;
}}
div[data-testid="stButton"] button p {{ font: inherit !important; }}

/* metrics — model estimates: mono gold figures */
div[data-testid="stMetric"] {{
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1.1rem 1.25rem;
    transition: border-color var(--t-ui);
}}
div[data-testid="stMetric"]:hover {{ border-color: var(--smoke); }}
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {{
    font: 500 11px/1.5 var(--sans) !important;
    letter-spacing: .04em !important; text-transform: uppercase;
    color: var(--ash) !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
    color: var(--gold) !important;
    font-family: var(--mono) !important;
    font-feature-settings: "tnum" 1, "zero" 1;
    font-weight: 400;
}}

/* tabs */
div[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid var(--line);
    gap: 4px;
}}
div[data-testid="stTabs"] [role="tab"] {{
    color: var(--ash);
    border-radius: 6px 6px 0 0;
    padding: .8rem 1.1rem;
    font: 400 14px/1 var(--sans);
    transition: color var(--t-ui);
}}
div[data-testid="stTabs"] [role="tab"] p {{
    font: inherit !important; color: inherit !important;
}}
div[data-testid="stTabs"] [aria-selected="true"] {{ color: var(--ink); }}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color: var(--ink); height: 1px; }}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {{ background-color: var(--line); }}

/* expander */
[data-testid="stExpander"] {{
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    background: transparent;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{ padding: .8rem 1.2rem; }}
[data-testid="stExpander"] summary p {{
    font: 500 12px/1.6 var(--sans) !important;
    letter-spacing: .04em; text-transform: uppercase;
    color: var(--ash) !important;
}}
[data-testid="stExpander"] summary:hover p {{ color: var(--ink) !important; }}
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

/* dataframes / editors */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid var(--line);
    border-radius: 16px;
    overflow: hidden;
}}

/* slider */
div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background: var(--bone); border-radius: 50%;
    box-shadow: none;
}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{
    font-family: var(--mono) !important; font-size: 12px !important;
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone) !important;
}}
div[data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
div[data-testid="stSlider"] [data-testid="stSliderTickBarMax"] {{
    font-family: var(--mono) !important; font-size: 11px !important;
    color: var(--smoke) !important;
}}

/* alerts + captions */
.stAlert, div[data-testid="stAlert"] {{
    border-radius: 16px;
    background: var(--bg) !important;
    border: 1px solid var(--line);
    color: var(--bone);
}}
div[data-testid="stAlert"] p {{ color: var(--bone) !important; font-family: var(--sans); font-size: 14px; }}
div[data-testid="stCaptionContainer"] p {{
    color: var(--smoke) !important;
    font: 400 12px/1.7 var(--mono) !important;
    font-feature-settings: "tnum" 1, "zero" 1;
}}
[data-testid="stMarkdownContainer"] h4 {{
    font: 500 12px/1.6 var(--sans);
    letter-spacing: .04em; text-transform: uppercase;
    color: var(--ash);
}}

/* spinner */
[data-testid="stSpinner"] p {{
    font-family: var(--mono) !important; font-size: 12px !important;
    color: var(--gold) !important;
}}

/* ---------- bespoke blocks ---------- */
.fieldnote {{
    border-left: 1px solid var(--line);
    padding: .35rem 0 .35rem 1.2rem;
    margin: .5rem 0 1.4rem;
    font: 400 14px/1.6 var(--sans);
    color: var(--ash);
    max-width: 640px;
}}
.lineup-meta {{
    font: 400 12px/1.8 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--smoke);
    border-top: 1px solid var(--line);
    padding-top: .6rem;
    margin: .2rem 0 1rem;
}}
.lineup-meta b {{ color: var(--bone); font-weight: 400; }}

/* scorecard tables — terminal blocks */
.sheetwrap {{
    width: 100%; max-height: 520px; overflow: auto;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--bg);
    margin: .3rem 0 1.2rem;
    scrollbar-width: thin; scrollbar-color: #26292c transparent;
}}
table.sheet {{ width: 100%; border-collapse: collapse; }}
table.sheet th {{
    position: sticky; top: 0; z-index: 1;
    background: #000000;
    color: var(--ash);
    font: 500 12px/1.5 var(--sans);
    letter-spacing: .04em; text-transform: uppercase;
    text-align: left;
    padding: .7rem .85rem;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}}
table.sheet td {{
    font: 400 13.5px/1.5 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--bone);
    padding: .5rem .85rem;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}}
table.sheet td:first-child {{ color: var(--ink); }}
table.sheet tr:hover td {{ background: rgba(255,255,255,0.02); }}

/* verdict — probability tickers on black, no container */
.verdict {{
    display: flex; align-items: flex-end; gap: 32px; flex-wrap: wrap;
    padding: 1.4rem 0 1rem;
}}
.verdict .vk {{
    font: 500 11px/2.2 var(--sans); letter-spacing: .04em;
    text-transform: uppercase; color: var(--smoke);
}}
.verdict .vh {{
    font: 400 clamp(1.5rem, 3.2vw, 2.2rem)/1.1 var(--disp);
    letter-spacing: -0.02em;
    color: var(--ink);
}}
.verdict .vh em {{ font-style: normal; color: var(--ink); }}
.verdict .vp {{
    font: 400 40px/1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--gold);
    text-shadow: var(--glow-live);
}}
.verdict .vp small {{
    font: 400 16px/1 var(--sans); color: var(--ash);
    margin-right: 12px; text-shadow: none;
}}

/* win probability tug bar */
.tug {{ margin: .3rem 0 1.8rem; }}
.tugbar {{
    display: flex; height: 2px;
    background: var(--line);
    overflow: hidden;
}}
.tugbar .a {{ background: {PALETTE["blue"]}; }}
.tugbar .t {{ background: {PALETTE["smoke"]}; }}
.tugbar .b {{ background: {PALETTE["bone"]}; }}
.tugbar div {{ transition: width .6s ease-out; }}
.tuglbl {{
    display: flex; justify-content: space-between; gap: 10px;
    font: 400 12px/1 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--smoke); padding-top: 10px;
}}
.tuglbl b {{ color: var(--bone); font-weight: 400; }}

.inn-head {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
    border-bottom: 1px solid var(--line);
    padding: 1.2rem 0 .65rem;
    margin: .6rem 0 .9rem;
}}
.inn-head h3 {{
    margin: 0;
    font: 400 1.3rem/1.15 var(--disp);
    letter-spacing: -0.01em;
    color: var(--ink);
}}
.inn-head h3 .n {{ color: var(--ash); }}
.inn-head .sc {{
    font: 400 13px/1.6 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: var(--ash); white-space: nowrap;
}}
.inn-head .sc b {{ color: var(--bone); font-weight: 400; }}

/* model notes cards */
.mcard {{
    border: 1px solid var(--line);
    border-radius: 16px;
    background: transparent;
    padding: 1.8rem 1.8rem 1.5rem;
    min-height: 12rem;
    transition: border-color var(--t-ui);
}}
.mcard:hover {{ border-color: var(--smoke); }}
.mcard .mk {{
    font: 500 11px/1 var(--sans); letter-spacing: .04em;
    text-transform: uppercase; color: var(--ash);
}}
.mcard h3 {{
    font: 400 1.35rem/1.3 var(--disp);
    letter-spacing: -0.01em;
    color: var(--ink); margin: .9rem 0 .5rem;
}}
.mcard p {{ font: 400 14px/1.6 var(--sans); color: var(--ash); }}
.factgrid {{
    display: grid; grid-template-columns: 1fr auto; gap: .55rem 1rem;
    margin-top: 1.2rem;
    border-top: 1px solid var(--line);
    padding-top: 1.1rem;
}}
.factgrid span:nth-child(odd) {{
    color: var(--smoke);
    font: 500 11px/1.5 var(--sans);
    letter-spacing: .04em; text-transform: uppercase;
    align-self: center;
}}
.factgrid span:nth-child(even) {{
    text-align: right; color: var(--bone);
    font: 400 13.5px/1.4 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
}}
.factgrid span.gold {{ color: var(--gold); }}

.support-row {{
    display: grid; grid-template-columns: 13rem 1fr; gap: 1.4rem;
    padding: 1rem 0;
    border-bottom: 1px solid var(--line);
}}
.support-row strong {{
    font: 500 12px/1.7 var(--sans); letter-spacing: .04em; text-transform: uppercase;
    color: var(--bone); font-weight: 500;
}}
.support-row span {{ font: 400 14px/1.65 var(--sans); color: var(--ash); }}

/* footer */
.footer {{
    border-top: 1px solid var(--line);
    margin-top: 5rem; padding-top: 1.4rem;
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}}
.footer .stamp {{
    font: 400 12px/1.7 var(--mono);
    font-feature-settings: "tnum" 1, "zero" 1;
    color: {PALETTE["dotgray"]};
}}
.footer .who {{
    display: inline-flex; align-items: center; gap: 14px;
    font: 400 13px/1 var(--sans); color: var(--ash);
}}
.footer .who b {{ color: var(--bone); font-weight: 500; }}
.footer a.applogo {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px;
    border: 1px solid var(--line); border-radius: 6px;
    opacity: .75;
    transition: border-color var(--t-ui), opacity var(--t-ui);
}}
.footer a.applogo:hover {{ border-color: var(--ash); opacity: 1; }}
.footer a.applogo img {{ width: 15px; height: 15px; display: block; }}

@media (max-width: 760px) {{
    .mh-right {{ display: none; }}
    .hero .constellation {{ opacity: .3; }}
    .hero .h1 {{ font-size: 2.6rem; }}
    .hero .hs {{ padding: 0 18px; }}
    .sect {{ flex-wrap: wrap; }}
    .sect .note {{ margin-left: 0; text-align: left; width: 100%; }}
    .support-row {{ grid-template-columns: 1fr; gap: .3rem; }}
    .footer {{ display: block; }}
    .verdict {{ gap: 18px; }}
}}
</style>
"""
