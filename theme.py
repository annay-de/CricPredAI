"""Global design system for the CricPredAI app.

Midnight observatory: a near-black canvas, white and steel-gray editorial
type, a whisper-weight serif for display, monospace micro-labels, and a
single electric cobalt accent used as punctuation. Flat surfaces, hairline
borders, pill-shaped controls, square cards, generous space. No gradients,
no grain, no shadows, no ornament.
"""

PALETTE = {
    "bg": "#070708",
    "panel": "#101012",
    "panel2": "#0C0C0E",
    "ink": "#FFFFFF",
    "body": "#CCCCCC",
    "muted": "#8F8F93",
    "dim": "#4C4C4C",
    "blue": "#0C92F6",     # chart / data blue (brighter member of the cobalt family)
    "cobalt": "#1954EC",   # the single UI accent
    "cyan": "#00CCFF",
    "mist": "#D9D9D9",
    "red": "#FC1C46",      # wickets and the live dot only
    "line": "rgba(255,255,255,0.14)",
    "line2": "rgba(255,255,255,0.07)",
}


def hero_particles() -> str:
    """A quiet dotted arc, cyan fading to cobalt — the page's one visual."""
    import math

    dots = []
    for col in range(26):
        t = col / 25.0
        x = 40 + t * 480
        mid = 210 + 90 * math.sin(t * 2.6 + 0.4)
        count = 9 + int(7 * math.sin(t * 3.1 + 1.1) ** 2)
        for row in range(count):
            u = row / max(count - 1, 1)
            y = mid + (u - 0.5) * (130 + 70 * math.sin(t * 2.2))
            r = 1.1 + 0.9 * math.sin(t * 3.3 + u * 5.0) ** 2
            # interpolate cyan -> cobalt
            c1, c2 = (0, 204, 255), (25, 84, 236)
            k = min(1.0, 0.15 + 0.85 * (0.4 * t + 0.6 * u))
            col_rgb = tuple(round(a + (b - a) * k) for a, b in zip(c1, c2))
            op = 0.16 + 0.5 * math.sin(t * 2.9 + u * 4.2) ** 2
            dots.append(
                f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" '
                f'fill="rgb{col_rgb}" opacity="{op:.2f}"/>'
            )
    return (
        '<svg class="particles" viewBox="0 0 560 420" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        + "".join(dots)
        + "</svg>"
    )


APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Inter:wght@300;400;500;600&family=Martian+Mono:wght@300;400;500&display=swap');

:root {{
    --bg: {PALETTE["bg"]};
    --panel: {PALETTE["panel"]};
    --panel2: {PALETTE["panel2"]};
    --ink: {PALETTE["ink"]};
    --body-c: {PALETTE["body"]};
    --mut: {PALETTE["muted"]};
    --dim: {PALETTE["dim"]};
    --blue: {PALETTE["blue"]};
    --cobalt: {PALETTE["cobalt"]};
    --mist: {PALETTE["mist"]};
    --red: {PALETTE["red"]};
    --line: {PALETTE["line"]};
    --line2: {PALETTE["line2"]};
    --mono: "Martian Mono", "IBM Plex Mono", ui-monospace, monospace;
    --serif: "Cormorant Garamond", Georgia, serif;
    --sans: "Inter", system-ui, sans-serif;
}}

/* ---------- shell ---------- */
.stApp {{ background: var(--bg); color: var(--body-c); }}
header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none; }}
[data-testid="stMainBlockContainer"] {{
    max-width: 1200px;
    padding-top: 1.4rem;
    padding-bottom: 5rem;
}}
.stApp, .stApp p, .stApp li {{ font-family: var(--sans); }}
h1, h2, h3, h4 {{ color: var(--ink); font-family: var(--sans); }}

[data-testid="stIconMaterial"] {{
    font-family: "Material Symbols Rounded" !important;
    font-weight: normal !important; font-style: normal !important;
    letter-spacing: normal !important; text-transform: none !important;
    -webkit-font-feature-settings: "liga" !important; font-feature-settings: "liga" !important;
}}

/* ---------- masthead: corner nav ---------- */
.masthead {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 16px;
    padding: 6px 2px 20px;
    border-bottom: 1px solid var(--line2);
    margin-bottom: 10px;
}}
.mh-brand {{ display: flex; align-items: center; gap: 10px; }}
.mh-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--red); flex: none;
    animation: pulse 2.4s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .3; }} }}
.mh-name {{
    font: 500 12px/1 var(--mono);
    letter-spacing: .38em; text-transform: uppercase; color: var(--ink);
}}
.mh-name span {{ color: var(--mut); }}
.mh-right {{
    font: 300 10px/1.8 var(--mono);
    letter-spacing: .22em; text-transform: uppercase;
    color: var(--mut); text-align: right;
}}
.mh-right b {{ color: var(--ink); font-weight: 400; }}

/* ---------- nav (radio reskin → ghost pills) ---------- */
div[data-testid="stRadio"] > div {{ gap: 8px; }}
div[data-testid="stRadio"] label {{
    border: 1px solid #3d3d3d;
    background: transparent;
    border-radius: 9999px;
    padding: 8px 20px;
    transition: border-color .15s ease, background .15s ease;
}}
div[data-testid="stRadio"] label p {{
    font: 400 10.5px/1 var(--mono) !important;
    letter-spacing: .18em; text-transform: uppercase;
    color: var(--mut) !important;
}}
div[data-testid="stRadio"] label:hover {{ border-color: var(--ink); }}
div[data-testid="stRadio"] label:hover p {{ color: var(--ink) !important; }}
div[data-testid="stRadio"] label:has(input:checked) {{
    background: var(--ink);
    border-color: var(--ink);
}}
div[data-testid="stRadio"] label:has(input:checked) p {{
    color: #070708 !important;
}}
div[data-testid="stRadio"] label > div:first-child {{ display: none; }}

/* ---------- hero ---------- */
.hero {{
    position: relative;
    padding: clamp(3rem, 7vw, 5.5rem) 0 clamp(2.4rem, 5vw, 4rem);
    margin-bottom: .5rem;
    overflow: visible;
}}
/* The one background graphic: a particle field pinned to the right edge.
   It stays put while content scrolls over it — the field bleeds across
   sections — and drifts very slowly so the page feels alive at rest. */
.hero .particles {{
    position: fixed; right: 1vw; top: 9vh;
    width: min(44vw, 560px); height: auto;
    pointer-events: none;
    opacity: .8;
    animation: drift 26s ease-in-out infinite;
}}
@keyframes drift {{
    0%, 100% {{ transform: translateY(0) rotate(0deg); }}
    50% {{ transform: translateY(-22px) rotate(1.2deg); }}
}}
@media (prefers-reduced-motion: reduce) {{
    .hero .particles {{ animation: none; }}
}}

/* scroll prompt — bracketed micro-label with a slow-pulsing vertical line */
.scrollcue {{
    display: flex; flex-direction: column; align-items: flex-start; gap: 12px;
    margin-top: 52px;
}}
.scrollcue span {{
    font: 300 9px/1 var(--mono);
    letter-spacing: .4em; text-transform: uppercase; color: var(--dim);
}}
.scrollcue i {{
    display: block; width: 1px; height: 52px;
    margin-left: 2px;
    background: linear-gradient(to bottom, var(--mut), transparent);
    transform-origin: top;
    animation: cue 2.6s ease-in-out infinite;
}}
@keyframes cue {{
    0% {{ transform: scaleY(0); opacity: 0; }}
    35% {{ transform: scaleY(1); opacity: 1; }}
    100% {{ transform: scaleY(1); opacity: 0; }}
}}

/* scroll-driven reveals — progressive enhancement, no-op elsewhere */
@supports (animation-timeline: view()) {{
    .sect, .mcard, .inn-head, .verdict, .support-row,
    div[data-testid="stMetric"] {{
        animation: rise-in .8s ease both;
        animation-timeline: view();
        animation-range: entry 0% entry 55%;
    }}
    @media (prefers-reduced-motion: reduce) {{
        .sect, .mcard, .inn-head, .verdict, .support-row,
        div[data-testid="stMetric"] {{ animation: none; }}
    }}
}}
@keyframes rise-in {{
    from {{ opacity: 0; transform: translateY(18px); }}
    to {{ opacity: 1; transform: none; }}
}}
.hero .eyebrow {{
    font: 300 10px/1 var(--mono);
    letter-spacing: .4em; text-transform: uppercase; color: var(--mut);
    margin-bottom: 26px;
    display: flex; align-items: center; gap: 10px;
}}
.hero .eyebrow::before {{
    content: ""; width: 6px; height: 6px; border-radius: 50%;
    background: var(--cobalt); display: inline-block;
}}
.hero .h1 {{
    position: relative;
    font: 300 clamp(2.8rem, 6vw, 4.6rem)/1.13 var(--serif);
    color: var(--ink); margin: 0; max-width: 780px;
    letter-spacing: 0;
}}
.hero .h1 em {{ font-style: italic; color: var(--blue); }}
.hero .copy {{
    position: relative;
    margin-top: 28px; max-width: 520px;
    font: 400 15px/1.65 var(--sans);
    color: var(--mut);
}}
.hero .herostats {{
    position: relative;
    display: flex; gap: 0; flex-wrap: wrap; margin-top: 44px;
}}
.hero .hs {{
    padding: 0 34px;
    border-left: 1px solid var(--line2);
}}
.hero .hs:first-child {{ padding-left: 0; border-left: none; }}
.hero .hs b {{
    display: block;
    font: 300 26px/1.1 var(--serif);
    color: var(--ink); font-variant-numeric: tabular-nums;
}}
.hero .hs span {{
    font: 300 9px/2.6 var(--mono);
    letter-spacing: .3em; text-transform: uppercase; color: var(--dim);
}}

/* ---------- section headers ---------- */
.sect {{
    display: flex; align-items: baseline; gap: 18px;
    border-top: 1px solid var(--line2);
    padding: 2.4rem 0 1rem;
    margin-top: 2.2rem; margin-bottom: .8rem;
}}
.sect .no {{
    font: 300 10px/1 var(--mono); color: var(--blue); letter-spacing: .3em;
}}
.sect h2 {{
    margin: 0;
    font: 300 1.8rem/1.15 var(--serif);
    color: var(--ink);
}}
.sect .note {{
    margin-left: auto;
    font: 300 9px/1.8 var(--mono); letter-spacing: .22em;
    color: var(--dim); text-transform: uppercase; text-align: right;
}}

/* ---------- widgets ---------- */
label, div[data-testid="stWidgetLabel"] p {{
    font: 300 9.5px/1.6 var(--mono) !important;
    letter-spacing: .28em !important; text-transform: uppercase;
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
    font-family: var(--sans);
    font-size: 14px;
}}
div[data-baseweb="select"] > div {{ border-radius: 0 !important; border-color: var(--line) !important; background: var(--panel) !important; }}
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {{
    color: var(--ink) !important;
}}
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {{
    background: #101012 !important;
    border: 1px solid var(--line) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}}
ul[role="listbox"] li {{ background: transparent !important; color: var(--body-c) !important; }}
div[role="option"], li[role="option"] {{ color: var(--body-c) !important; background: transparent !important; }}
div[role="option"]:hover, li[role="option"]:hover,
li[aria-selected="true"] {{ background: rgba(255,255,255,0.06) !important; color: var(--ink) !important; }}
[data-baseweb="tag"] {{
    background: transparent !important;
    border: 1px solid #3d3d3d !important;
    border-radius: 9999px !important;
    color: var(--body-c) !important;
}}
[data-baseweb="tag"] span, [data-baseweb="tag"] div {{
    color: var(--body-c) !important;
    font-family: var(--sans);
    font-size: 12.5px;
}}
[data-baseweb="tag"] svg, [data-baseweb="tag"] [role="presentation"] {{ fill: var(--mut) !important; color: var(--mut) !important; }}
input:disabled {{ -webkit-text-fill-color: var(--mut) !important; opacity: 1 !important; }}

/* buttons: pills */
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{
    border-radius: 9999px;
    border: 1px solid #3d3d3d;
    background: transparent;
    color: var(--ink);
    font: 400 11px/1.2 var(--mono);
    letter-spacing: .14em; text-transform: uppercase;
    min-height: 2.6rem;
    padding-left: 1.4rem; padding-right: 1.4rem;
    transition: border-color .15s ease, background .15s ease;
    box-shadow: none;
}}
div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {{
    border-color: var(--ink); color: var(--ink); background: transparent;
}}
div[data-testid="stButton"] button[kind="primary"] {{
    background: var(--cobalt);
    border-color: var(--cobalt);
    color: #ffffff;
}}
div[data-testid="stButton"] button[kind="primary"]:hover {{
    background: #2563f0; border-color: #2563f0; color: #ffffff;
}}
div[data-testid="stButton"] button:disabled {{
    border-color: #2a2a2c; color: var(--dim); background: transparent;
}}

/* metrics */
div[data-testid="stMetric"] {{
    background: transparent;
    border: 1px solid var(--line2);
    border-radius: 0;
    padding: 1rem 1.15rem;
}}
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {{
    font: 300 8.5px/1.6 var(--mono) !important;
    letter-spacing: .26em !important; text-transform: uppercase;
    color: var(--dim) !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
    color: var(--ink) !important;
    font-family: var(--serif) !important;
    font-weight: 300;
}}

/* tabs */
div[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid var(--line2);
    gap: 0;
}}
div[data-testid="stTabs"] [role="tab"] {{
    color: var(--dim);
    border-radius: 0;
    padding: .85rem 1.2rem;
    font: 400 10.5px/1 var(--mono);
    letter-spacing: .2em; text-transform: uppercase;
}}
div[data-testid="stTabs"] [role="tab"] p {{
    font: inherit !important; color: inherit !important; letter-spacing: inherit;
}}
div[data-testid="stTabs"] [aria-selected="true"] {{ color: var(--ink); }}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background-color: var(--ink); height: 1px; }}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {{ background-color: var(--line2); }}

/* expander */
[data-testid="stExpander"] {{
    border: 1px solid var(--line2) !important;
    border-radius: 0 !important;
    background: transparent;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{ padding: .75rem 1.1rem; }}
[data-testid="stExpander"] summary p {{
    font: 300 10px/1.6 var(--mono) !important;
    letter-spacing: .24em; text-transform: uppercase;
    color: var(--mut) !important;
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
    font: 300 13px/1 var(--mono);
    color: var(--mut);
}}
[data-testid="stExpander"] details[open] summary span[data-testid="stIconMaterial"]::after {{
    content: "–";
}}

/* dataframes / editors */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid var(--line2);
    border-radius: 0;
    overflow: hidden;
}}

/* slider */
div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
    background: var(--ink); border-radius: 50%;
    box-shadow: none;
}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{
    font-family: var(--mono) !important; font-size: 11px !important;
    color: var(--ink) !important;
}}
div[data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
div[data-testid="stSlider"] [data-testid="stSliderTickBarMax"] {{
    font-family: var(--mono) !important; font-size: 10px !important;
    color: var(--dim) !important;
}}

/* alerts + captions */
.stAlert, div[data-testid="stAlert"] {{
    border-radius: 0;
    background: var(--panel) !important;
    border: 1px solid var(--line);
    color: var(--body-c);
}}
div[data-testid="stAlert"] p {{ color: var(--body-c) !important; font-family: var(--sans); font-size: 13.5px; }}
div[data-testid="stCaptionContainer"] p {{
    color: var(--dim) !important;
    font: 300 10.5px/1.7 var(--mono) !important;
    letter-spacing: .04em;
}}
[data-testid="stMarkdownContainer"] h4 {{
    font: 300 10px/1.6 var(--mono);
    letter-spacing: .3em; text-transform: uppercase;
    color: var(--mut);
}}

/* spinner */
[data-testid="stSpinner"] p {{ font-family: var(--mono) !important; font-size: 11px !important; color: var(--mut) !important; }}

/* ---------- bespoke blocks ---------- */
.fieldnote {{
    border-left: 2px solid var(--cobalt);
    padding: .3rem 0 .3rem 1.1rem;
    margin: .4rem 0 1.4rem;
    font: 400 16px/1.55 var(--serif); font-style: italic;
    color: var(--mut);
    max-width: 640px;
}}
.lineup-meta {{
    font: 300 9.5px/1.8 var(--mono);
    letter-spacing: .18em; text-transform: uppercase;
    color: var(--dim);
    border-top: 1px solid var(--line2);
    padding-top: .6rem;
    margin: .2rem 0 1rem;
}}
.lineup-meta b {{ color: var(--body-c); font-weight: 400; }}

/* scorecard tables */
.sheetwrap {{
    width: 100%; max-height: 520px; overflow: auto;
    border: 1px solid var(--line2);
    background: transparent;
    margin: .3rem 0 1.2rem;
    scrollbar-width: thin; scrollbar-color: #2a2a2c transparent;
}}
table.sheet {{ width: 100%; border-collapse: collapse; }}
table.sheet th {{
    position: sticky; top: 0; z-index: 1;
    background: #0c0c0e;
    color: var(--dim);
    font: 300 8.5px/1.6 var(--mono);
    letter-spacing: .24em; text-transform: uppercase;
    text-align: left;
    padding: .65rem .8rem;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
}}
table.sheet td {{
    font: 400 13px/1.45 var(--sans);
    font-variant-numeric: tabular-nums;
    color: var(--body-c);
    padding: .55rem .8rem;
    border-bottom: 1px solid var(--line2);
    white-space: nowrap;
}}
table.sheet td:first-child {{ color: var(--ink); }}
table.sheet tr:hover td {{ background: rgba(255,255,255,0.025); }}

/* verdict strip on results page */
.verdict {{
    display: flex; align-items: baseline; gap: 24px; flex-wrap: wrap;
    padding: 1.4rem 0 1.2rem;
}}
.verdict .vk {{
    font: 300 9px/2 var(--mono); letter-spacing: .3em;
    text-transform: uppercase; color: var(--dim);
}}
.verdict .vh {{
    font: 300 clamp(1.7rem, 3.6vw, 2.6rem)/1.15 var(--serif);
    color: var(--ink);
}}
.verdict .vh em {{ font-style: italic; color: var(--blue); }}

/* win probability tug bar */
.tug {{ margin: .2rem 0 1.6rem; }}
.tugbar {{
    display: flex; height: 3px;
    background: var(--line2);
    overflow: hidden;
}}
.tugbar .a {{ background: {PALETTE["blue"]}; }}
.tugbar .t {{ background: {PALETTE["dim"]}; }}
.tugbar .b {{ background: {PALETTE["mist"]}; }}
.tugbar div {{ transition: width .6s ease; }}
.tuglbl {{
    display: flex; justify-content: space-between; gap: 10px;
    font: 300 9.5px/1 var(--mono); letter-spacing: .2em; text-transform: uppercase;
    color: var(--dim); padding-top: 10px;
}}
.tuglbl b {{ color: var(--body-c); font-weight: 400; }}

.inn-head {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
    border-bottom: 1px solid var(--line2);
    padding: 1.1rem 0 .6rem;
    margin: .6rem 0 .9rem;
}}
.inn-head h3 {{
    margin: 0;
    font: 300 1.35rem/1.15 var(--serif);
    color: var(--ink);
}}
.inn-head h3 .n {{ color: var(--blue); font-style: italic; }}
.inn-head .sc {{
    font: 300 11px/1.6 var(--mono); letter-spacing: .08em;
    color: var(--mut); white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}
.inn-head .sc b {{ color: var(--ink); font-weight: 400; }}

/* model notes cards */
.mcard {{
    border: 1px solid var(--line2);
    background: transparent;
    padding: 1.6rem 1.6rem 1.4rem;
    min-height: 12rem;
}}
.mcard .mk {{
    font: 300 9px/1 var(--mono); letter-spacing: .3em;
    text-transform: uppercase; color: var(--blue);
    display: flex; align-items: center; gap: 8px;
}}
.mcard h3 {{
    font: 300 1.45rem/1.25 var(--serif);
    color: var(--ink); margin: 1rem 0 .6rem;
}}
.mcard p {{ font: 400 13.5px/1.6 var(--sans); color: var(--mut); }}
.factgrid {{
    display: grid; grid-template-columns: 1fr auto; gap: .5rem 1rem;
    margin-top: 1.1rem;
    border-top: 1px solid var(--line2);
    padding-top: 1rem;
}}
.factgrid span:nth-child(odd) {{
    color: var(--dim);
    font: 300 8.5px/1.6 var(--mono);
    letter-spacing: .24em; text-transform: uppercase;
    align-self: center;
}}
.factgrid span:nth-child(even) {{
    text-align: right; color: var(--ink);
    font: 400 13px/1.4 var(--sans);
    font-variant-numeric: tabular-nums;
}}

.support-row {{
    display: grid; grid-template-columns: 13rem 1fr; gap: 1.4rem;
    padding: .95rem 0;
    border-bottom: 1px solid var(--line2);
}}
.support-row strong {{
    font: 300 10px/1.8 var(--mono); letter-spacing: .2em; text-transform: uppercase;
    color: var(--ink); font-weight: 400;
}}
.support-row span {{ font: 400 13.5px/1.65 var(--sans); color: var(--mut); }}

/* footer */
.footer {{
    border-top: 1px solid var(--line2);
    margin-top: 4.5rem; padding-top: 1.2rem;
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    font: 300 9px/1.9 var(--mono); letter-spacing: .22em; text-transform: uppercase;
    color: var(--dim);
}}
.footer b {{ color: var(--body-c); font-weight: 400; }}
.footer a {{ color: var(--mut); text-decoration: none; }}
.footer a:hover {{ color: var(--ink); }}
.footer .social {{ display: inline-flex; gap: 1.2rem; margin-left: 1.2rem; }}

@media (max-width: 760px) {{
    .mh-right {{ display: none; }}
    .hero .particles {{ opacity: .35; }}
    .hero .h1 {{ font-size: 2.3rem; }}
    .hero .hs {{ padding: 0 18px; }}
    .sect {{ flex-wrap: wrap; }}
    .sect .note {{ margin-left: 0; text-align: left; width: 100%; }}
    .support-row {{ grid-template-columns: 1fr; gap: .3rem; }}
    .footer {{ display: block; }}
}}
</style>
"""
