"""SyndraLens UI layer.

Everything visual lives here: theme/CSS, hero banner, KPI cards, section
headers, the Leaflet map, record cards and region reference data.
`dashboard.py` imports from this module and handles data and app flow.
"""

import json
import os
from html import escape

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
TEAL = "#0E7C86"
AMBER = "#F2A541"
CORAL = "#E4572E"

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap');

:root {
    --ink: #07222B;
    --ink-2: #0B3440;
    --teal: #0E7C86;
    --teal-soft: #DDF1F2;
    --blue: #1D4E89;
    --blue-soft: #E1EBF7;
    --amber: #F2A541;
    --amber-soft: #FDF0DB;
    --coral: #E4572E;
    --coral-soft: #FCE6DF;
    --bg: #F2F6F8;
    --card: #FFFFFF;
    --line: #DCE6EA;
    --muted: #5E7580;
    --shadow: 0 1px 2px rgba(7,34,43,.04), 0 8px 24px rgba(7,34,43,.06);
}

html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif;
    color: var(--ink);
}
.stApp {
    background:
        radial-gradient(1100px 420px at 85% -80px, rgba(14,124,134,.10), transparent 70%),
        var(--bg);
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1320px; }

h1, h2, h3, h4 { font-family: 'Sora', sans-serif !important; color: var(--ink); letter-spacing: -0.015em; }

/* ---------- Hero ---------- */
.hero {
    position: relative; overflow: hidden;
    display: flex; align-items: center; justify-content: space-between; gap: 2rem;
    background: linear-gradient(115deg, #06202A 0%, #0A3B47 55%, #0E7C86 120%);
    border-radius: 22px; padding: 2.3rem 2.6rem; margin-bottom: 1.6rem;
    box-shadow: 0 18px 40px rgba(7,34,43,.22);
}
.hero::before {
    content: ""; position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,.07) 1px, transparent 1px);
    background-size: 22px 22px; pointer-events: none;
}
.hero-text { position: relative; z-index: 1; max-width: 640px; }
.brand-row { display: flex; align-items: center; gap: .7rem; margin-bottom: .9rem; }
.brand-mark {
    width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center;
    background: linear-gradient(135deg, #2BB3BE, #0E7C86); box-shadow: 0 6px 16px rgba(0,0,0,.25);
}
.hero h1 {
    font-family: 'Sora', sans-serif !important; color: #fff !important;
    font-size: 2.7rem !important; font-weight: 800 !important; line-height: 1.05 !important;
    margin: 0 !important; padding: 0 !important;
}
.hero p { color: #B7D6DB; font-size: 1.05rem; margin: .6rem 0 1.1rem 0; max-width: 560px; }
.hero-tags { display: flex; flex-wrap: wrap; gap: .5rem; }
.hero-tag {
    background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.18);
    color: #E6F4F6; padding: .28rem .8rem; border-radius: 999px; font-size: .84rem; font-weight: 500;
}
.ecg { position: relative; z-index: 1; flex: 0 0 340px; width: 340px; height: 120px; }
.ecg .base { stroke: rgba(255,255,255,.14); }
.ecg .beat {
    stroke: #5EE0D0; stroke-dasharray: 220 780; stroke-dashoffset: 1000;
    animation: ecg-run 3.4s linear infinite; filter: drop-shadow(0 0 6px rgba(94,224,208,.8));
}
@keyframes ecg-run { to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .ecg .beat { animation: none; stroke-dashoffset: 780; } }
@media (max-width: 900px) { .ecg { display: none; } .hero h1 { font-size: 2.1rem !important; } }

/* ---------- Section headers ---------- */
.sec { display: flex; align-items: center; gap: .85rem; margin: 2.1rem 0 1rem 0; }
.sec-icon {
    width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center;
    background: var(--teal-soft); font-size: 1.25rem; flex: 0 0 42px;
}
.sec-title { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.4rem; line-height: 1.15; color: var(--ink); }
.sec-sub { color: var(--muted); font-size: .92rem; margin-top: .1rem; }

/* ---------- KPI cards ---------- */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
.kpi {
    display: flex; align-items: center; gap: 1rem; background: var(--card);
    border: 1px solid var(--line); border-radius: 18px; padding: 1.15rem 1.3rem; box-shadow: var(--shadow);
}
.kpi-icon { width: 54px; height: 54px; border-radius: 16px; display: grid; place-items: center; font-size: 1.55rem; flex: 0 0 54px; }
.kpi-label { color: var(--muted); font-size: .9rem; font-weight: 500; }
.kpi-value { font-family: 'Sora', sans-serif; font-weight: 800; font-size: 2.2rem; line-height: 1.1; color: var(--ink); }
.kpi.teal .kpi-icon { background: var(--teal-soft); }
.kpi.blue .kpi-icon { background: var(--blue-soft); }
.kpi.amber .kpi-icon { background: var(--amber-soft); }
.kpi.coral .kpi-icon { background: var(--coral-soft); }
.kpi.coral .kpi-value { color: var(--coral); }

/* ---------- Chips ---------- */
.chip-row { display: flex; flex-wrap: wrap; gap: .6rem; margin: .8rem 0 1rem 0; }
.chip {
    display: inline-flex; align-items: center; gap: .45rem; background: var(--card);
    border: 1px solid var(--line); border-radius: 999px; padding: .38rem .95rem;
    font-size: .9rem; font-weight: 500; color: var(--ink); box-shadow: 0 1px 2px rgba(7,34,43,.04);
}
.chip b { font-family: 'Sora', sans-serif; font-weight: 700; }

/* ---------- Panels ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--card); border: 1px solid var(--line) !important;
    border-radius: 18px !important; box-shadow: var(--shadow);
}
.panel-title { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.05rem; margin-bottom: .2rem; }
.panel-sub { color: var(--muted); font-size: .86rem; margin-bottom: .6rem; }
div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }

/* ---------- Tabs ---------- */
button[data-baseweb="tab"] { font-family: 'Sora', sans-serif; font-weight: 600; font-size: .95rem; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--teal); }
div[data-baseweb="tab-highlight"] { background-color: var(--teal) !important; height: 3px !important; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #06202A, #0A3340); border-right: none; }
section[data-testid="stSidebar"] * { color: #E3F0F2; }
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #0F3F4C; border: 1px solid #1D5A69; border-radius: 12px;
}
.side-brand { display: flex; align-items: center; gap: .65rem; margin-bottom: 1.2rem; }
.side-brand .brand-mark { width: 36px; height: 36px; border-radius: 11px; }
.side-brand .nm { font-family: 'Sora', sans-serif; font-weight: 800; font-size: 1.2rem; color: #fff; }
.side-label { font-size: .8rem; color: #8FB4BC; margin: 1rem 0 .3rem 0; font-weight: 600; }
span[data-baseweb="tag"] { background-color: var(--teal) !important; border-radius: 999px !important; font-weight: 500; }
span[data-baseweb="tag"] * { color: #fff !important; }

/* ---------- Inputs ---------- */
div[data-testid="stFileUploader"] section {
    background: var(--card); border: 2px dashed #7CC3CA; border-radius: 18px; padding: 1.4rem;
}
div[data-testid="stFileUploader"] section:hover { border-color: var(--teal); background: #FAFEFE; }
div[data-testid="stFileUploader"] button { border-radius: 10px; border: 1px solid var(--teal); color: var(--teal); font-weight: 600; }
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #12929D, #0E7C86); border: none; border-radius: 12px;
    font-weight: 600; padding: .6rem 1.6rem; box-shadow: 0 6px 16px rgba(14,124,134,.30);
}
div[data-testid="stButton"] button[kind="primary"]:hover { filter: brightness(1.07); }
div[data-testid="stButton"] button[kind="secondary"] { border-radius: 12px; font-weight: 600; }
.stSelectbox [data-baseweb="select"] > div { border-radius: 12px; border-color: var(--line); }
div[data-testid="stAlert"] { border-radius: 14px; }

/* ---------- Empty state ---------- */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1.2rem; }
.step { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 1.2rem 1.3rem; box-shadow: var(--shadow); }
.step .n {
    width: 30px; height: 30px; border-radius: 50%; background: var(--teal); color: #fff;
    display: grid; place-items: center; font-family: 'Sora', sans-serif; font-weight: 700; font-size: .9rem; margin-bottom: .7rem;
}
.step h4 { margin: 0 0 .25rem 0; font-size: 1.02rem; }
.step p { margin: 0; color: var(--muted); font-size: .92rem; line-height: 1.5; }

/* ---------- Complaint record ---------- */
.record-card {
    background: var(--card); border: 1px solid var(--line); border-left: 5px solid var(--teal);
    border-radius: 16px; padding: 1.1rem 1.4rem; margin: .8rem 0 1.1rem 0; box-shadow: var(--shadow);
}
.record-card .meta { color: var(--muted); font-size: .88rem; }
.record-card .text { font-size: 1.08rem; margin-top: .55rem; line-height: 1.6; }
.pill {
    display: inline-block; padding: .2rem .8rem; border-radius: 999px; background: var(--teal-soft);
    color: var(--teal); font-weight: 600; font-size: .84rem; margin: 0 .4rem .3rem 0;
}
.pill.amber { background: var(--amber-soft); color: #9A5B00; }
.pill.coral { background: var(--coral-soft); color: #B63A16; }
.pill.blue { background: var(--blue-soft); color: var(--blue); }
.none { color: var(--muted); font-size: .9rem; }

.footer-note { color: var(--muted); font-size: .84rem; text-align: center; margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--line); }
</style>
"""


def apply_theme():
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
_LOGO_SVG = (
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l2.5-6 4 12 2.5-6H22"/></svg>'
)

_ECG_SVG = (
    '<svg class="ecg" viewBox="0 0 340 120" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
    '<path class="base" d="M0 60H70L84 60 96 24 112 100 128 40 138 60H210L222 60 234 30 248 90 260 52 268 60H340"/>'
    '<path class="beat" pathLength="1000" d="M0 60H70L84 60 96 24 112 100 128 40 138 60H210L222 60 234 30 248 90 260 52 268 60H340"/>'
    "</svg>"
)


def render_hero():
    st.markdown(
        '<div class="hero"><div class="hero-text">'
        f'<div class="brand-row"><span class="brand-mark">{_LOGO_SVG}</span></div>'
        "<h1>SyndraLens</h1>"
        "<p>Regional symptom monitoring for early detection of emerging health signals.</p>"
        '<div class="hero-tags">'
        '<span class="hero-tag">🩺 Syndromic surveillance</span>'
        '<span class="hero-tag">🗺️ Regional hotspots</span>'
        '<span class="hero-tag">🚨 Threshold alerts</span>'
        "</div></div>" + _ECG_SVG + "</div>",
        unsafe_allow_html=True,
    )


def sidebar_brand():
    st.sidebar.markdown(
        f'<div class="side-brand"><span class="brand-mark">{_LOGO_SVG}</span>'
        '<span class="nm">SyndraLens</span></div>',
        unsafe_allow_html=True,
    )


def sidebar_label(text):
    st.sidebar.markdown(f'<div class="side-label">{escape(text)}</div>', unsafe_allow_html=True)


def section_header(icon, title, subtitle=""):
    sub = f'<div class="sec-sub">{escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="sec"><div class="sec-icon">{icon}</div>'
        f'<div><div class="sec-title">{escape(title)}</div>{sub}</div></div>',
        unsafe_allow_html=True,
    )


def panel_title(title, subtitle=""):
    sub = f'<div class="panel-sub">{escape(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="panel-title">{escape(title)}</div>{sub}', unsafe_allow_html=True)


def kpi_cards(items):
    """items: list of (icon, label, value, tone) where tone is teal|blue|amber|coral."""
    cards = "".join(
        f'<div class="kpi {tone}"><div class="kpi-icon">{icon}</div>'
        f'<div><div class="kpi-label">{escape(label)}</div><div class="kpi-value">{value:,}</div></div></div>'
        for icon, label, value, tone in items
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def chips(items):
    """items: list of (icon, label, value)."""
    html = "".join(
        f'<span class="chip">{icon} {escape(label)} <b>{escape(str(value))}</b></span>'
        for icon, label, value in items
    )
    st.markdown(f'<div class="chip-row">{html}</div>', unsafe_allow_html=True)


def empty_state():
    steps = [
        ("Upload", "Add a CSV with id, region, report_date and text columns."),
        ("Analyse", "Each complaint is scanned for symptoms, exposures and syndromes."),
        ("Explore", "Review hotspots on the map, trends and alerts by region."),
    ]
    body = "".join(
        f'<div class="step"><div class="n">{i}</div><h4>{t}</h4><p>{d}</p></div>'
        for i, (t, d) in enumerate(steps, 1)
    )
    st.markdown(f'<div class="steps">{body}</div>', unsafe_allow_html=True)


def pills(items, tone=""):
    if not items:
        st.markdown('<span class="none">None detected</span>', unsafe_allow_html=True)
        return
    html = "".join(f'<span class="pill {tone}">{escape(str(i))}</span>' for i in items)
    st.markdown(html, unsafe_allow_html=True)


def record_card(record):
    st.markdown(
        '<div class="record-card">'
        f'<span class="pill">📍 {escape(str(record["region"]))}</span>'
        f'<span class="meta">Reported on {escape(str(record["report_date"]))}</span>'
        f'<div class="text">{escape(str(record["text"]))}</div></div>',
        unsafe_allow_html=True,
    )


def render_record_fields(record):
    fields = [("🤒", "symptoms", ""), ("☣️", "exposures", "amber"), ("🧬", "syndromes", "blue")]
    for col, (icon, name, tone) in zip(st.columns(3), fields):
        with col:
            with st.container(border=True):
                panel_title(f"{icon} {name.title()}")
                try:
                    parsed = json.loads(record[name])
                except (ValueError, TypeError):
                    parsed = record[name]
                if isinstance(parsed, list) and all(not isinstance(p, (dict, list)) for p in parsed):
                    pills(parsed, tone)
                elif isinstance(parsed, (dict, list)):
                    st.json(parsed)
                else:
                    pills([parsed] if parsed and not pd.isna(parsed) else [], tone)


def footer():
    st.markdown(
        '<div class="footer-note">SyndraLens regional monitor · '
        "For surveillance support only, not a diagnostic tool.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------
REGION_COORDS = {
    "Kukatpally": (17.4948, 78.3996), "LB Nagar": (17.3457, 78.5522),
    "Secunderabad": (17.4399, 78.4983), "Serilingampally": (17.4933, 78.3170),
    "Uppal": (17.4058, 78.5591),
    # IT corridor
    "Madhapur": (17.4483, 78.3915), "Gachibowli": (17.4401, 78.3489),
    "Kondapur": (17.4697, 78.3657), "HITEC City": (17.4435, 78.3772),
    "Financial District": (17.4169, 78.3397), "Nanakramguda": (17.4156, 78.3430),
    # Central Hyderabad
    "Ameerpet": (17.4375, 78.4483), "Begumpet": (17.4448, 78.4675),
    "Banjara Hills": (17.4126, 78.4482), "Jubilee Hills": (17.4325, 78.4071),
    "Khairatabad": (17.4092, 78.4657), "Himayatnagar": (17.4062, 78.4843),
    "Abids": (17.3890, 78.4760),
    # East and southeast
    "Dilsukhnagar": (17.3688, 78.5247), "Kothapet": (17.3727, 78.5480),
    "Nagole": (17.3710, 78.5678), "Habsiguda": (17.4150, 78.5430),
    "Tarnaka": (17.4280, 78.5380), "Boduppal": (17.4130, 78.5800),
    "Peerzadiguda": (17.4050, 78.5860), "Hayathnagar": (17.3230, 78.6060),
    # West and southwest
    "Miyapur": (17.4968, 78.3568), "Chandanagar": (17.4950, 78.3230),
    "Nizampet": (17.5170, 78.3670), "Bachupally": (17.5440, 78.3650),
    "Manikonda": (17.4050, 78.3830), "Mehdipatnam": (17.3940, 78.4390),
    "Tolichowki": (17.3990, 78.4140), "Attapur": (17.3680, 78.4310),
    "Rajendranagar": (17.3210, 78.4030),
}

_REGION_ALIASES = {
    "hitech city": "HITEC City", "hi-tech city": "HITEC City",
    "lb nagar": "LB Nagar", "l.b. nagar": "LB Nagar",
    "kukatpally": "Kukatpally", "serilingampally": "Serilingampally",
    "lingampally": "Serilingampally", "secunderabad": "Secunderabad", "uppal": "Uppal",
}


def normalize_region(value):
    """Return the canonical region spelling; unknown regions are kept as typed."""
    if pd.isna(value):
        return None
    cleaned = " ".join(str(value).strip().split()).casefold()
    return _REGION_ALIASES.get(cleaned, str(value).strip())


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------
def get_map_key():
    try:
        return st.secrets.get("MAP_API_KEY") or os.environ.get("MAP_API_KEY")
    except Exception:
        return os.environ.get("MAP_API_KEY")


_MAP_TEMPLATE = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body { margin: 0; padding: 0; font-family: 'DM Sans', Arial, sans-serif; }
  #map { height: 460px; border-radius: 18px; border: 1px solid #DCE6EA; background: #F2F6F8;
         box-shadow: 0 8px 24px rgba(7,34,43,.08); }
  .legend { background: #fff; padding: 10px 14px; border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,.18); font-size: 12px; line-height: 1.8; color: #07222B; }
  .dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:7px; }
  .leaflet-tooltip.tip { background: rgba(255,255,255,.96); border: 1px solid #DCE6EA; border-radius: 999px;
        box-shadow: 0 1px 4px rgba(7,34,43,.15); color: #07222B; font-weight: 600; font-size: 12px; padding: 2px 10px; }
  .leaflet-tooltip-bottom.tip:before { display: none; }
  .leaflet-control-layers { border-radius: 12px; border: none; box-shadow: 0 2px 10px rgba(0,0,0,.18); }
  .leaflet-bar { border: none !important; box-shadow: 0 2px 10px rgba(0,0,0,.18) !important; }
  .leaflet-bar a:first-child { border-radius: 10px 10px 0 0; }
  .leaflet-bar a:last-child { border-radius: 0 0 10px 10px; }
  .pulse { animation: pulse 1.8s ease-out infinite; transform-origin: center; transform-box: fill-box; }
  @keyframes pulse { 0% { opacity: .9; } 100% { opacity: .25; } }
</style>
<div id="map"></div>
<script>
  const pts = __POINTS__;
  const map = L.map('map', { scrollWheelZoom: false });
  const esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  const lightBase = L.tileLayer(esri + 'Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', { attribution: 'Tiles &copy; Esri', maxZoom: 16 });
  const lightLabels = L.tileLayer(esri + 'Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxZoom: 16 });
  const baseLayers = {
    'Light': L.layerGroup([lightBase, lightLabels]),
    'Streets': L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }),
    'Satellite': L.tileLayer(esri + 'World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: 'Tiles &copy; Esri', maxZoom: 18 })
  };
  let defaultBase = baseLayers['Light'];
  const keyedUrl = __TILE_URL__;
  if (keyedUrl) {
    baseLayers['Streets (MapTiler)'] = L.tileLayer(keyedUrl, { attribution: __TILE_ATTR__, maxZoom: 18 });
    defaultBase = baseLayers['Streets (MapTiler)'];
  }
  defaultBase.addTo(map);
  L.control.layers(baseLayers, null, { position: 'topright', collapsed: true }).addTo(map);

  const maxC = Math.max(...pts.map(p => p.complaints), 1);
  const group = [];
  pts.forEach(p => {
    const hasAlert = p.alerts > 0;
    const color = hasAlert ? '#E4572E' : '#0E7C86';
    const radius = 12 + 20 * (p.complaints / maxC);
    const circle = L.circleMarker([p.lat, p.lon], {
      radius: radius, color: color, weight: 2, fillColor: color, fillOpacity: 0.30,
      className: hasAlert ? 'pulse' : ''
    }).addTo(map);
    L.circleMarker([p.lat, p.lon], { radius: 4, color: '#fff', weight: 1, fillColor: color, fillOpacity: 1 }).addTo(map);
    circle.bindPopup('<b>' + p.region + '</b><br>Complaints: ' + p.complaints + '<br>Alerts: ' + p.alerts);
    circle.bindTooltip(p.region + ' (' + p.complaints + ')', {
      permanent: true, direction: 'bottom', offset: [0, radius * 0.9], className: 'tip'
    });
    group.push([p.lat, p.lon]);
  });
  map.fitBounds(group, { padding: [50, 50], maxZoom: 13 });

  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function () {
    const d = L.DomUtil.create('div', 'legend');
    d.innerHTML =
      '<div><span class="dot" style="background:#0E7C86"></span>No alert</div>' +
      '<div><span class="dot" style="background:#E4572E"></span>Alert raised</div>' +
      '<div style="color:#5E7580">Circle size = complaint volume</div>';
    return d;
  };
  legend.addTo(map);
</script>
"""


def build_map_html(map_points, api_key=None):
    tile_url = (
        "https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=" + api_key
        if api_key
        else None
    )
    tile_attr = "&copy; MapTiler &copy; OpenStreetMap contributors"
    return (
        _MAP_TEMPLATE.replace("__POINTS__", json.dumps(map_points))
        .replace("__TILE_URL__", json.dumps(tile_url))
        .replace("__TILE_ATTR__", json.dumps(tile_attr))
    )
