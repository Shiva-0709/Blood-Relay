"""
BLOOD RELAY — Streamlit hackathon prototype
Stack: Streamlit + Python + injected CSS + Plotly (ships with most Streamlit installs)
Run:   pip install -r requirements.txt  &&  streamlit run app.py

Design notes (Streamlit limits respected):
- Navigation = st.session_state["page"] + st.rerun()  (no real router)
- Every "screen" is a Python function; state survives page switches, resets on browser refresh
- Inputs are disabled=True widgets (native Streamlit), styled through CSS
- Maps / networks are Plotly scatter plots with fictional coordinates (no API keys)
- "Animation" = st.progress / st.empty placeholders + time.sleep (Streamlit is rerun-based)
- Custom cards/badges = st.markdown(..., unsafe_allow_html=True)
"""
import time
import math
import random
from functools import lru_cache
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Blood Relay", page_icon="🩸", layout="wide",
                   initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ THEME
C = dict(bg="#080F14", bg2="#0B1220", card="#101E2E", red="#EF3340", border="#123B5A",
         green="#00C781", orange="#F59E0B", text="#F8FAFC", muted="#94A3B8", input="#182536",
         blue="#3B82F6")

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, #1a0d14 0%, {C['bg']} 45%) fixed; color:{C['text']}; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility:hidden; height:0; }}
.block-container {{ padding-top:1.2rem; padding-bottom:2rem; max-width:1300px; }}
h1,h2,h3,h4 {{ color:{C['text']} !important; letter-spacing:-.01em; }}
p, label, span, li {{ color:{C['text']}; }}

/* cards */
.br-card {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:12px; padding:18px 20px; margin-bottom:14px; }}
.br-card.red {{ border-color:#5a1820; }}
.br-card.green {{ border-color:#0d5a40; }}
.br-muted {{ color:{C['muted']} !important; font-size:.85rem; }}
.br-title {{ font-size:1.05rem; font-weight:600; margin:0 0 4px 0; }}
.br-big {{ font-size:1.6rem; font-weight:800; line-height:1.1; }}
.br-row {{ display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #15283d; font-size:.9rem; }}
.br-row:last-child {{ border-bottom:none; }}
.br-row span:first-child {{ color:{C['muted']}; }}

/* brand */
.br-brand {{ font-weight:800; font-size:1.25rem; letter-spacing:.02em; }}
.br-brand b {{ color:{C['red']}; }}
.br-hero {{ font-size:3.2rem; font-weight:800; line-height:1; margin:0; }}
.br-hero b {{ color:{C['red']}; }}

/* badges */
.badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.72rem; font-weight:600; }}
.b-red {{ background:#3a0f15; color:{C['red']}; border:1px solid #5a1820; }}
.b-green {{ background:#06321f; color:{C['green']}; border:1px solid #0d5a40; }}
.b-orange {{ background:#3a2706; color:{C['orange']}; border:1px solid #5a3d0a; }}
.b-blue {{ background:#0b2236; color:#60a5fa; border:1px solid {C['border']}; }}

/* demo notice */
.demo {{ background:{C['bg2']}; border:1px solid {C['border']}; border-left:3px solid #3b82f6; border-radius:10px;
        padding:10px 14px; font-size:.82rem; color:{C['muted']}; margin-bottom:14px; }}
.demo b {{ color:#93c5fd; }}

/* disabled inputs */
.stTextInput input:disabled, .stNumberInput input:disabled, .stTextArea textarea:disabled,
div[data-baseweb="select"] > div {{ background:{C['input']} !important; color:{C['text']} !important;
   -webkit-text-fill-color:{C['text']} !important; border:1px solid {C['border']} !important; opacity:1 !important; }}
.stTextInput label, .stNumberInput label, .stTextArea label, .stSelectbox label, .stRadio label {{ color:{C['muted']} !important; font-size:.8rem !important; }}

/* buttons */
.stButton > button {{ border-radius:8px; font-weight:600; border:1px solid {C['border']}; background:{C['bg2']}; color:{C['text']};
   padding:.55rem 1rem; transition:all .15s; }}
.stButton > button:hover {{ border-color:{C['red']}; color:{C['text']}; }}
.stButton > button[kind="primary"] {{ background:{C['red']}; border-color:{C['red']}; color:white; }}
.stButton > button[kind="primary"]:hover {{ background:#d62633; box-shadow:0 0 0 3px #ef334033; }}

/* metrics */
div[data-testid="stMetric"] {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:12px; padding:14px 16px; }}
div[data-testid="stMetricLabel"] p {{ color:{C['muted']} !important; }}

/* timeline */
.tl {{ display:flex; gap:12px; align-items:flex-start; padding:8px 0; }}
.dot {{ width:22px; height:22px; border-radius:50%; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:.7rem; font-weight:800; }}
.dot.done {{ background:{C['green']}; color:#04140d; }}
.dot.now {{ background:{C['red']}; color:white; box-shadow:0 0 0 4px #ef334033; animation:pulse 1.4s infinite; }}
.dot.todo {{ border:2px solid #334155; }}
@keyframes pulse {{ 0%{{box-shadow:0 0 0 0 #ef334066}} 100%{{box-shadow:0 0 0 10px #ef334000}} }}

/* sidebar */
section[data-testid="stSidebar"] {{ background:{C['bg2']}; border-right:1px solid {C['border']}; }}
.stProgress > div > div > div > div {{ background:{C['red']}; }}
div[data-testid="stPlotlyChart"] {{ border:1px solid {C['border']}; border-radius:14px; overflow:hidden; background:#060B11; }}
/* pop-up dialog */
div[role="dialog"] {{ background:{C['card']} !important; border:1px solid {C['border']}; border-radius:16px !important; box-shadow:0 24px 80px rgba(0,0,0,.65); }}
div[role="dialog"] h2, div[role="dialog"] p, div[role="dialog"] b {{ color:{C['text']}; }}
div[role="dialog"] [aria-label="Close"] {{ color:{C['muted']} !important; }}
div[data-testid="stDialog"] {{ backdrop-filter: blur(4px); }}
div[data-testid="stDataFrame"] {{ border:1px solid {C['border']}; border-radius:10px; }}
.file {{ background:{C['input']}; border:1px dashed {C['border']}; border-radius:8px; padding:8px 12px; margin:6px 0; font-size:.85rem; }}
hr {{ border-color:{C['border']} !important; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------ DATA
COMPAT = {  # recipient -> compatible donors
    "O-": ["O-"], "O+": ["O+", "O-"], "A-": ["A-", "O-"], "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"], "B+": ["B+", "B-", "O+", "O-"], "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

def init_state():
    if "init" in st.session_state:
        return
    ss = st.session_state
    ss.init = True
    ss.page = "landing"
    ss.hospitals = [
        dict(name="Apollo Hospitals", area="Greams Road", x=6.2, y=6.8, dist=7.8, eta=18, rating=4.8,
             stock={"O-": 5, "O+": 22, "A+": 14, "A-": 3, "B+": 18, "B-": 2, "AB+": 6, "AB-": 1}),
        dict(name="MIOT International", area="Manapakkam", x=2.4, y=3.1, dist=11.2, eta=26, rating=4.6,
             stock={"O-": 4, "O+": 15, "A+": 9, "A-": 2, "B+": 11, "B-": 1, "AB+": 4, "AB-": 0}),
        dict(name="Kauvery Hospital", area="Alwarpet", x=5.1, y=4.6, dist=5.4, eta=14, rating=4.5,
             stock={"O-": 2, "O+": 19, "A+": 12, "A-": 1, "B+": 9, "B-": 3, "AB+": 2, "AB-": 1}),
        dict(name="Fortis Malar", area="Adyar", x=7.4, y=2.6, dist=9.1, eta=22, rating=4.4,
             stock={"O-": 0, "O+": 8, "A+": 7, "A-": 0, "B+": 6, "B-": 0, "AB+": 3, "AB-": 0}),
        dict(name="SIMS Hospital", area="Vadapalani", x=3.0, y=7.4, dist=8.6, eta=20, rating=4.3,
             stock={"O-": 6, "O+": 12, "A+": 10, "A-": 4, "B+": 7, "B-": 2, "AB+": 5, "AB-": 2}),
        dict(name="Rela Institute", area="Chromepet", x=1.2, y=1.0, dist=16.3, eta=35, rating=4.7,
             stock={"O-": 3, "O+": 10, "A+": 8, "A-": 2, "B+": 5, "B-": 1, "AB+": 2, "AB-": 0}),
    ]
    ss.home = dict(name="City General Hospital", x=4.4, y=5.6,
                   stock={"O-": 1, "O+": 18, "A+": 12, "A-": 3, "B+": 15, "B-": 2, "AB+": 4, "AB-": 1})
    ss.request = None
    ss.matches = []
    ss.selected = None
    ss.reserved = False
    ss.stage = 0
    ss.completed = False
    ss.registered = False
    ss.stock_updates = 0
    ss.searched = False
    now = datetime.now()
    ss.requests = [
        dict(id="BR-1187", hospital="Kauvery Hospital", group="A+", units=2, urgency="Urgent", status="In Transit"),
        dict(id="BR-1186", hospital="SIMS Hospital", group="B-", units=4, urgency="Critical", status="Matching"),
        dict(id="BR-1182", hospital="MIOT International", group="O+", units=1, urgency="Normal", status="Delivered"),
        dict(id="BR-1179", hospital="Fortis Malar", group="AB+", units=2, urgency="Urgent", status="Delivered"),
    ]
    ss.t0 = now

def go_to(page):
    st.session_state.page = page
    st.session_state.popup = page if page in DEMO_FORM_PAGES else None   # pop-up only for locked-input screens
    st.rerun()

def find_matches(group, units):
    ok = COMPAT[group]
    res = []
    for h in st.session_state.hospitals:
        avail = sum(h["stock"].get(g, 0) for g in ok if g == group) or sum(h["stock"].get(g, 0) for g in ok)
        if avail >= units:
            score = avail * 2 - h["eta"] * 0.6 + h["rating"] * 3
            res.append({**h, "avail": avail, "score": round(score, 1)})
    return sorted(res, key=lambda r: -r["score"])

STAGES = ["Request Submitted", "Hospital Confirmed", "Blood Collected", "In Transit", "Delivered"]

# ------------------------------------------------------------------ UI HELPERS
def html(s):
    st.markdown(s, unsafe_allow_html=True)

def navbar(right=""):
    a, b = st.columns([3, 2])
    with a:
        html(f'<div class="br-brand">🩸 BLOOD <b>RELAY</b></div>')
    with b:
        html(f'<div style="text-align:right" class="br-muted">{right}</div>')
    html("<hr style='margin:.6rem 0 1.2rem 0'>")

def demo_notice(text="Sample information is prefilled for prototype demonstration. Inputs are locked. Click the button below to continue."):
    html(f'<div class="demo">ⓘ <b>DEMO MODE</b> — {text}</div>')

# ------------------------------------------------------------------ DEMO POP-UP
# Screens whose inputs are pre-filled + locked. Arriving at one of them (via any button) opens a centred dialog.
DEMO_FORM_PAGES = {
    "request":  dict(screen="Emergency Blood Request",     action="Continue to Hospital Matching"),
    "register": dict(screen="New Hospital Registration",   action="Join Network"),
}

def _demo_popup_body(page):
    info = DEMO_FORM_PAGES[page]
    html(
        "<div style='text-align:center;padding:4px 6px 0'>"
        "<div style='font-size:2.4rem'>🩸</div>"
        "<p class='br-title' style='font-size:1.3rem;margin:6px 0 10px'>Prototype Demonstration</p>"
        f"<p style='line-height:1.65;margin:0 0 14px'>The input fields on the <b>{info['screen']}</b> screen have already "
        "been filled with sample data and are locked for editing, as the backend is not integrated in this prototype.</p>"
        "</div>"
        "<div class='br-card' style='margin-bottom:10px'>"
        "<p class='br-muted' style='margin:0 0 6px;letter-spacing:.06em'>HOW TO PROCEED</p>"
        "<p style='margin:0;line-height:1.6'>Please review the sample details shown, then click "
        f"<b>“{info['action']}”</b> to simulate the process and continue the demonstration.</p>"
        "</div>"
        "<p class='br-muted' style='text-align:center;margin:0 0 8px'>All names, figures and documents shown are fictional.</p>")
    if st.button("Understood, Continue", type="primary", use_container_width=True):
        st.rerun()          # closes the dialog

_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
if _dialog:
    try:
        _popup = _dialog("Demo Mode — Inputs Pre-filled", width="large")(_demo_popup_body)
    except TypeError:       # very old Streamlit builds without the width option
        _popup = _dialog("Demo Mode — Inputs Pre-filled")(_demo_popup_body)
else:
    _popup = None

def maybe_demo_popup(page):
    ss = st.session_state
    if ss.get("popup") != page:
        return
    ss.popup = None         # open once per visit; never re-open on later reruns
    if _popup:
        _popup(page)
    else:                   # very old Streamlit: fall back to an inline banner
        demo_notice("Inputs on this screen are pre-filled with sample data and locked. "
                    f"Click “{DEMO_FORM_PAGES[page]['action']}” to continue the demonstration.")

def rows(d):
    return "".join(f'<div class="br-row"><span>{k}</span><span>{v}</span></div>' for k, v in d.items())

# ------------------------------------------------------------------ MAP ENGINE
# "Emergency Command Centre" look: a procedural night-city basemap (streets, parks, river, sea)
# with a glowing red road network, drawn purely with Plotly traces -> no tiles, no API keys, works offline.
# Hover cards (name, distance, ETA, stock) live on the hospital pins, exactly like before.
MAP_W, MAP_H = 9.0, 8.2
BLUE, HOT = "#3B82F6", "#FF4D5A"


def rgba(hex_, a):
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def _join(paths):
    """list of [(x, y), ...] polylines -> one x list + one y list, broken by None."""
    xs, ys = [], []
    for p in paths:
        xs += [q[0] for q in p] + [None]
        ys += [q[1] for q in p] + [None]
    return xs, ys


def road_path(a, b, n=48):
    """Smooth, gently curved 'road' between two points (same input -> same road, every rerun)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    seed = int((x0 * 7.3 + y0 * 3.1 + x1 * 5.7 + y1 * 2.3) * 1000)
    k = (0.12 + (seed % 7) / 70) * (1 if seed % 2 else -1)          # how much the road bends
    cx, cy = (x0 + x1) / 2 - dy * k, (y0 + y1) / 2 + dx * k            # bezier control point
    nx, ny = -dy / length, dx / length
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        w = 0.035 * math.sin(t * math.pi * 5 + seed) * math.sin(math.pi * t)   # little wiggles = real-road feel
        pts.append((x + nx * w, y + ny * w))
    return pts


def _split_path(pts, frac):
    """Cut a polyline at `frac` (0..1) of its length -> (travelled, remaining, cut_point)."""
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    target, acc = sum(seg) * max(0.0, min(1.0, frac)), 0.0
    for i, s in enumerate(seg):
        if acc + s >= target:
            t = (target - acc) / s if s else 0.0
            p = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
            return pts[:i + 1] + [p], [p] + pts[i + 1:], p
        acc += s
    return pts, [pts[-1]], pts[-1]


def _wob_line(p0, p1, rnd, step=0.2):
    """Straight-ish street with a slight wobble, so the grid never looks like graph paper."""
    (x0, y0), (x1, y1) = p0, p1
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(length / step))
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    amp, fr, ph = rnd.uniform(.015, .06), rnd.uniform(1.0, 2.6), rnd.uniform(0, 6.28)
    pts = []
    for i in range(n + 1):
        t = i / n
        w = amp * math.sin(fr * length * t + ph)
        pts.append((x0 + (x1 - x0) * t + nx * w, y0 + (y1 - y0) * t + ny * w))
    return pts


def _gappy(pts, rnd, skip=.2):
    """Chop a street into pieces and randomly drop some -> broken, organic street network."""
    out, i = [], 0
    while i < len(pts) - 1:
        n = rnd.randint(5, 14)
        chunk = pts[i:i + n + 1]
        if len(chunk) > 1 and rnd.random() > skip:
            out.append(chunk)
        i += n
    return out


def _blob(cx, cy, rx, ry, rnd, wob=.16, n=36):
    ph, k = rnd.uniform(0, 6.28), rnd.choice([2, 3, 4])
    return [(cx + rx * (1 + wob * math.sin(k * 2 * math.pi * i / n + ph)) * math.cos(2 * math.pi * i / n),
             cy + ry * (1 + wob * math.sin(k * 2 * math.pi * i / n + ph)) * math.sin(2 * math.pi * i / n))
            for i in range(n + 1)]


@lru_cache(maxsize=1)
def city_layers():
    """Static basemap geometry. Built once per server process, reused by every map on every screen."""
    rnd = random.Random(11)
    minor, major = [], []
    x, k = .15, 0
    while x < MAP_W:
        major_street = k % 3 == 0
        (major if major_street else minor).extend(_gappy(_wob_line((x, 0), (x, MAP_H), rnd), rnd, .12 if major_street else .25))
        x, k = x + rnd.uniform(.3, .6), k + 1
    y, k = .15, 0
    while y < MAP_H:
        major_street = k % 3 == 0
        (major if major_street else minor).extend(_gappy(_wob_line((0, y), (MAP_W, y), rnd), rnd, .12 if major_street else .25))
        y, k = y + rnd.uniform(.3, .6), k + 1
    for p0, p1 in [((0, 1.2), (6.5, 8.2)), ((1.5, 0), (9, 5.8)), ((0, 5.2), (4.8, 0)), ((3.5, 8.2), (9, 3.0))]:
        major.extend(_gappy(_wob_line(p0, p1, rnd), rnd, .05))          # diagonal avenues

    districts = [_blob(cx, cy, rx, ry, rnd, .2) for cx, cy, rx, ry in
                 [(4.4, 5.4, 1.7, 1.3), (6.2, 6.4, 1.4, 1.0), (2.6, 3.4, 1.3, 1.1), (7.0, 2.9, 1.1, .9), (3.0, 7.0, 1.2, .9)]]
    parks = [_blob(cx, cy, rx, ry, rnd, .18) for cx, cy, rx, ry in
             [(3.5, 4.1, .45, .28), (6.5, 3.9, .5, .3), (1.5, 6.2, .5, .33), (6.9, 7.6, .45, .28)]]

    xr = [i * .15 for i in range(int(8.7 / .15) + 1)]
    mid = [1.9 + .35 * math.sin(v * .9 + .5) + .12 * math.sin(v * 2.3) for v in xr]
    upper, lower = [(v, m + .075) for v, m in zip(xr, mid)], [(v, m - .075) for v, m in zip(xr, mid)]
    river = upper + lower[::-1] + [upper[0]]

    ys = [i * .2 for i in range(int(MAP_H / .2) + 2)]
    edge = [(8.5 + .12 * math.sin(v * 1.7), v) for v in ys]
    sea = edge + [(MAP_W, ys[-1]), (MAP_W, 0), edge[0]]

    labels = [("T. NAGAR", 3.6, 6.3), ("MYLAPORE", 6.3, 5.4), ("GUINDY", 3.5, 4.1), ("VELACHERY", 5.7, 2.9),
              ("ANNA NAGAR", 1.9, 5.6), ("TAMBARAM", .8, 3.4), ("MARINA", 7.9, 6.3)]
    return dict(minor=_join(minor), major=_join(major), districts=_join(districts), parks=_join(parks),
                river=_join([river]), sea=_join([sea]), labels=labels)


def network_edges(home, hospitals):
    """Spokes (home -> every hospital) + peer roads (each hospital -> its 2 nearest neighbours)."""
    edges = [("home", (home["x"], home["y"]), (h["x"], h["y"])) for h in hospitals]
    seen = set()
    for h in hospitals:
        near = sorted((o for o in hospitals if o is not h),
                      key=lambda o: math.dist((h["x"], h["y"]), (o["x"], o["y"])))[:2]
        for o in near:
            key = frozenset([h["name"], o["name"]])
            if key not in seen:
                seen.add(key)
                edges.append(("peer", (h["x"], h["y"]), (o["x"], o["y"])))
    return edges


def hospital_hover(h, show_stock=None):
    """The small info card shown when the mouse is over a hospital pin."""
    stock = (f"🩸 {show_stock}: <b>{h['stock'].get(show_stock, 0)}</b> units" if show_stock
             else f"🩸 Total stock: <b>{sum(h['stock'].values())}</b> units")
    return (f"<b>{h['name']}</b><br><span style='color:#94A3B8'>{h['area']}, Chennai · ★ {h['rating']}</span><br>"
            f"📍 <b>{h['dist']} km</b> away<br>⏱ ETA <b>{h['eta']} min</b><br>{stock}")


def network_fig(highlight=None, route_to=None, progress=1.0, h=380, show_stock=None, radar=False, fleet=False):
    ss = st.session_state
    home, hosp = ss.home, ss.hospitals
    L = city_layers()
    f = go.Figure()

    def line(xy, color, width):
        f.add_trace(go.Scatter(x=xy[0], y=xy[1], mode="lines", line=dict(color=color, width=width), hoverinfo="skip"))

    def area(xy, fill, edge=None, ew=1):
        f.add_trace(go.Scatter(x=xy[0], y=xy[1], mode="lines", fill="toself", fillcolor=fill, hoverinfo="skip",
                               line=dict(color=edge or "rgba(0,0,0,0)", width=ew if edge else 0)))

    # 1) basemap -------------------------------------------------------------
    area(L["districts"], "rgba(40,90,140,.10)")
    line(L["minor"], "#12263a", 1)
    line(L["major"], "#1c3d59", 1.6)
    area(L["parks"], "rgba(0,199,129,.10)", "rgba(0,199,129,.28)")
    area(L["river"], "#08203a", "rgba(59,130,246,.30)", 1)
    area(L["sea"], "#07192b", "rgba(59,130,246,.35)", 1.2)
    f.add_trace(go.Scatter(x=[v[1] for v in L["labels"]], y=[v[2] for v in L["labels"]], mode="text",
                           text=[v[0] for v in L["labels"]], hoverinfo="skip",
                           textfont=dict(size=10, color="rgba(148,163,184,.40)", family="Inter")))
    f.add_trace(go.Scatter(x=[3.2], y=[5.0], mode="text", text=["Chennai"], hoverinfo="skip",
                           textfont=dict(size=16, color="#E2E8F0", family="Inter")))

    # 2) glowing road network --------------------------------------------------
    edges = network_edges(home, hosp)
    roads = {kind: _join([road_path(a, b) for k, a, b in edges if k == kind]) for kind in ("peer", "home")}
    for w, a in [(10, .05), (5, .10)]:
        line(roads["peer"], rgba(C["red"], a), w)
        line(roads["home"], rgba(C["red"], round(a * 1.6, 3)), w)
    line(roads["peer"], rgba(C["red"], .45), 1.2)
    line(roads["home"], rgba(HOT, .9), 2)

    if radar:       # search screen: radar ripples around the requesting hospital
        cols = [rgba(C["red"], a) for a in (.60, .40, .25, .12)]
        f.add_trace(go.Scatter(x=[home["x"]] * 4, y=[home["y"]] * 4, mode="markers", hoverinfo="skip",
                               marker=dict(size=[90, 170, 250, 330], color=cols, symbol="circle-open",
                                           line=dict(color=cols, width=1.6))))

    # 3) delivery route (blue = planned, red = travelled) -----------------------
    amb = None
    if route_to:
        path = road_path((home["x"], home["y"]), (route_to["x"], route_to["y"]))[::-1]    # hospital -> home
        done, rest, _ = _split_path(path, progress)
        amb = _split_path(path, max(progress, .08))[2]      # never sits on top of the hospital's "H"
        if len(rest) > 1:
            xy = _join([rest])
            line(xy, rgba(BLUE, .10), 12); line(xy, rgba(BLUE, .22), 6); line(xy, BLUE, 3)
        if len(done) > 1:
            xy = _join([done])
            line(xy, rgba(C["red"], .12), 14); line(xy, rgba(C["red"], .25), 8); line(xy, HOT, 3.5)

    if fleet:       # landing page: a few parked-on-the-network ambulances for atmosphere
        pts = []
        for (_, a, b), t in zip(edges[:3], (.42, .58, .50)):
            p = road_path(a, b)
            pts.append(p[int(len(p) * t)])
        f.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="text", text=["🚑"] * len(pts),
                               textfont=dict(size=20), hoverinfo="skip"))

    # 4) hospital pins (with hover cards) ---------------------------------------
    xs, ys, hov, edge_c, fill_c, txt_c, sizes, halo_c, labels, label_c = ([] for _ in range(10))
    for hsp in hosp:
        n = hsp["stock"].get(show_stock, 0) if show_stock else None
        has = show_stock is None or n > 0
        sel = bool(highlight) and hsp["name"] == highlight
        edge = C["green"] if sel else (BLUE if has else "#475569")
        xs.append(hsp["x"]); ys.append(hsp["y"])
        hov.append(hospital_hover(hsp, show_stock))
        edge_c.append(edge)
        fill_c.append("#06321f" if sel else ("#0B1F3A" if has else "#111827"))
        txt_c.append("#FFFFFF" if has else "#64748B")
        sizes.append(26 if sel else 21)
        halo_c.append(rgba(edge, .22 if has else .08))
        sub = f"<br><span style='color:{C['green'] if has else '#64748B'}'>{show_stock} · {n} units</span>" if show_stock else ""
        labels.append(f"<b>{hsp['name']}</b>{sub}")
        label_c.append(C["green"] if sel else ("#CBD5E1" if has else "#64748B"))
    f.add_trace(go.Scatter(x=xs, y=ys, mode="markers", hoverinfo="skip",
                           marker=dict(size=[s + 24 for s in sizes], color=halo_c, symbol="circle")))
    f.add_trace(go.Scatter(x=xs, y=ys, mode="text", text=labels, textposition="top center", hoverinfo="skip",
                           textfont=dict(size=11, color=label_c, family="Inter")))
    f.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=["<b>H</b>"] * len(xs), textposition="middle center",
                           textfont=dict(size=12, color=txt_c, family="Inter"),
                           marker=dict(size=sizes, color=fill_c, symbol="square", line=dict(color=edge_c, width=2)),
                           hovertext=hov, hoverinfo="text",
                           hoverlabel=dict(bgcolor="#0B1220", bordercolor=edge_c, align="left",
                                           font=dict(family="Inter", size=13, color=C["text"]))))

    # 5) requesting hospital (you) ----------------------------------------------
    f.add_trace(go.Scatter(x=[home["x"]] * 2, y=[home["y"]] * 2, mode="markers", hoverinfo="skip",
                           marker=dict(size=[70, 44], color=[rgba(C["red"], .08), rgba(C["red"], .18)], symbol="circle")))
    f.add_trace(go.Scatter(x=[home["x"]], y=[home["y"]], mode="text", text=["City General (You)"],
                           textposition="bottom center", hoverinfo="skip",
                           textfont=dict(size=12, color=C["text"], family="Inter")))
    f.add_trace(go.Scatter(x=[home["x"]], y=[home["y"]], mode="markers+text", text=["<b>+</b>"],
                           textposition="middle center", textfont=dict(size=15, color="#FFFFFF", family="Inter"),
                           marker=dict(size=24, color=C["red"], symbol="circle", line=dict(color="#FFFFFF", width=2)),
                           hovertext=[f"<b>{home['name']}</b><br><span style='color:#94A3B8'>Requesting hospital (You)</span>"
                                      f"<br>🩸 Local stock: <b>{sum(home['stock'].values())}</b> units"],
                           hoverinfo="text",
                           hoverlabel=dict(bgcolor="#0B1220", bordercolor=C["red"], align="left",
                                           font=dict(family="Inter", size=13, color=C["text"]))))

    # 6) ambulance on top of everything -----------------------------------------
    if amb is not None:
        f.add_trace(go.Scatter(x=[amb[0]], y=[amb[1]], mode="markers", hoverinfo="skip",
                               marker=dict(size=46, color=rgba(C["red"], .22), symbol="circle")))
        f.add_trace(go.Scatter(x=[amb[0]], y=[amb[1]], mode="text", text=["🚑"], hoverinfo="skip",
                               textfont=dict(size=24)))

    f.update_layout(height=h, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#060B11",
                    showlegend=False, dragmode=False, hovermode="closest", hoverdistance=30,
                    xaxis=dict(visible=False, range=[0, MAP_W], fixedrange=True),
                    yaxis=dict(visible=False, range=[0, MAP_H], fixedrange=True),
                    font=dict(color=C["text"], family="Inter"),
                    hoverlabel=dict(bgcolor="#0B1220", bordercolor=C["red"], align="left",
                                    font=dict(family="Inter", size=13, color=C["text"])))
    return f


CFG = {"displayModeBar": False, "staticPlot": False}

# ------------------------------------------------------------------ SCREENS
def screen_landing():
    navbar("Home · About · How it works &nbsp;&nbsp; <span class='badge b-blue'>DEMO MODE</span>")
    l, r = st.columns([1, 1.25], gap="large")
    with l:
        html("<div style='height:30px'></div><p class='br-hero'>BLOOD <b>RELAY</b></p>")
        html("<p style='font-size:1.1rem;margin-top:10px'>Connecting Hospitals. Because Every Drop Counts.</p>")
        html("<p class='br-muted'>A real-time coordination network that finds compatible blood in nearby hospitals "
             "and tracks it to the bedside — in minutes, not hours.</p>")
        if st.button("Request Blood  →", type="primary", use_container_width=True):
            go_to("request")
        if st.button("Join Hospital Network", use_container_width=True):
            go_to("login")
        demo_notice("All data in this prototype is fictional.")
    with r:
        st.plotly_chart(network_fig(h=400, fleet=True), use_container_width=True, config=CFG)
    cols = st.columns(4)
    for c, (v, t) in zip(cols, [("50+", "Partner Hospitals"), ("24/7", "Emergency Support"),
                                ("< 3 min", "Smart Matching"), ("1,240", "Deliveries Completed")]):
        c.metric(t, v)

def screen_request():
    ss = st.session_state
    maybe_demo_popup("request")
    navbar("Request Blood")
    if st.button("← Home"):
        go_to("landing")
    l, r = st.columns([1.6, 1], gap="large")
    with l:
        html("<h3 style='margin-bottom:0'>Emergency Blood Request</h3><p class='br-muted'>Prefilled demo request from City General Hospital.</p>")
        st.text_input("Requesting Hospital", "City General Hospital", disabled=True)
        a, b = st.columns(2)
        a.text_input("Patient ID", "PT-2401", disabled=True)
        b.text_input("Patient Age", "32", disabled=True)
        a.selectbox("Blood Group Required", ["O-"], disabled=True)
        b.text_input("Units Required", "3 Units", disabled=True)
        st.radio("Urgency Level", ["Normal", "Urgent", "Critical Emergency"], index=2, horizontal=True, disabled=True)
        st.text_input("Required By", (datetime.now() + timedelta(minutes=45)).strftime("Today, %I:%M %p"), disabled=True)
        st.text_area("Medical Notes", "Post-partum haemorrhage. Patient stable on fluids; immediate O- transfusion advised.",
                     disabled=True, height=80)
        html("<p class='br-muted' style='margin:8px 0 0'>Medical Documents (sample)</p>"
             "<div class='file'>📄 Doctor_Letter_Demo.pdf <span class='badge b-blue' style='float:right'>sample</span></div>"
             "<div class='file'>📄 Patient_Report_Demo.pdf <span class='badge b-blue' style='float:right'>sample</span></div>")
        st.write("")
        if st.button("Continue to Hospital Matching  →", type="primary", use_container_width=True):
            if ss.request is None:  # no duplicates
                ss.request = dict(id=f"BR-{random.randint(1200, 1999)}", hospital="City General Hospital",
                                  group="O-", units=3, urgency="Critical", status="Request Created",
                                  created=datetime.now())
                ss.requests.insert(0, {k: ss.request[k] for k in ["id", "hospital", "group", "units", "urgency", "status"]})
            go_to("search")
    with r:
        demo_notice()
        html("<div class='br-card' style='text-align:center;padding:40px 20px'><div style='font-size:4rem'>🩸</div>"
             "<p class='br-muted'>A small request<br>can make a big difference.</p></div>")
        if ss.request:
            html(f"<div class='br-card green'><span class='badge b-green'>Request exists</span>"
                 f"<p class='br-muted' style='margin-top:8px'>{ss.request['id']} already created — continuing won't duplicate it.</p></div>")

def screen_search():
    ss = st.session_state
    if ss.request is None:
        go_to("request")
    navbar(f"Request <b>{ss.request['id']}</b> · Finding the nearest hospitals")
    l, r = st.columns([1, 1.4], gap="large")
    with l:
        html("<h3>Searching Nearby Hospitals…</h3><p class='br-muted'>Scanning the network for compatible O- units.</p>")
        steps = ["Checking blood availability…", "Analyzing distance and ETA…",
                 "Contacting nearby hospitals…", "Finding the best match…"]
        box = st.empty()
        bar = st.progress(0 if not ss.searched else 100)
        if not ss.searched:
            for i in range(len(steps) + 1):
                box.markdown("".join(f"<p>{'✅' if j < i else '⏳'} {s}</p>" for j, s in enumerate(steps)), unsafe_allow_html=True)
                bar.progress(int(i / len(steps) * 100))
                time.sleep(0.6)
            ss.matches = find_matches(ss.request["group"], ss.request["units"])
            ss.searched = True
        else:
            box.markdown("".join(f"<p>✅ {s}</p>" for s in steps), unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.metric("Hospitals Checked", len(ss.hospitals))
        b.metric("With Stock", len(ss.matches))
        c.metric("Time Elapsed", "0:03")
    with r:
        st.plotly_chart(network_fig(show_stock="O-", h=360, radar=True), use_container_width=True, config=CFG)
    st.markdown("#### Ranked matches")
    if not ss.matches:
        html("<div class='br-card red'>No hospital currently has enough compatible stock. Try the Dashboard to apply a stock update.</div>")
        return
    for i, m in enumerate(ss.matches):
        c1, c2, c3, c4, c5 = st.columns([2.2, 1, 1, 1, 1.2])
        best = "<span class='badge b-green'>Best match</span>" if i == 0 else ""
        c1.markdown(f"**{m['name']}** {best}<br>"
                    f"<span class='br-muted'>{m['area']}, Chennai</span>", unsafe_allow_html=True)
        c2.metric("O- Units", m["avail"])
        c3.metric("Distance", f"{m['dist']} km")
        c4.metric("ETA", f"{m['eta']} min")
        if c5.button("Select", key=f"sel{i}", type="primary" if i == 0 else "secondary", use_container_width=True):
            if not ss.reserved:
                ss.selected = m["name"]
            go_to("match")

def screen_match():
    ss = st.session_state
    if not ss.selected:
        go_to("search")
    m = next(x for x in ss.matches if x["name"] == ss.selected)
    navbar("<span class='badge b-green'>● Match Found</span>")
    l, r = st.columns([1, 1.4], gap="large")
    with l:
        html("<h3>✅ Nearby Hospital Found!</h3><p class='br-muted'>Availability confirmed for the requested blood units.</p>")
        html(f"<div class='br-card'><div style='display:flex;justify-content:space-between'><div>"
             f"<p class='br-title'>🏥 {m['name']}</p><p class='br-muted'>{m['area']}, Chennai · ★ {m['rating']}</p></div>"
             f"<div><span class='badge {'b-green' if ss.reserved else 'b-orange'}'>{'Reserved' if ss.reserved else 'Available'}</span></div></div>"
             + rows({"Blood Group": ss.request["group"], "Units Available": f"{m['avail']} Units",
                     "Units Requested": f"{ss.request['units']} Units", "Distance": f"{m['dist']} km",
                     "Estimated Arrival": f"{m['eta']} minutes"}) + "</div>")
        if not ss.reserved:
            if st.button("Confirm Match & Reserve Units", type="primary", use_container_width=True):
                h = next(x for x in ss.hospitals if x["name"] == m["name"])
                h["stock"]["O-"] -= ss.request["units"]  # deduct once
                ss.reserved = True
                ss.stage = 1
                ss.requests[0]["status"] = "Matched"
                st.toast(f"{ss.request['units']} units reserved at {m['name']}", icon="✅")
                time.sleep(.4); st.rerun()
        else:
            if st.button("Track Delivery  →", type="primary", use_container_width=True):
                go_to("track")
        if not ss.reserved and st.button("← Back to matches", use_container_width=True):
            go_to("search")
    with r:
        st.plotly_chart(network_fig(highlight=m["name"], route_to=m, progress=0.0, h=380), use_container_width=True, config=CFG)

def screen_track():
    ss = st.session_state
    if not ss.reserved:
        go_to("match")
    m = next(x for x in ss.hospitals if x["name"] == ss.selected)
    navbar("<span class='badge b-green'>● Live Tracking</span>")
    l, r = st.columns([1, 1.4], gap="large")
    base = ss.request["created"]
    with l:
        html("<h3>Blood in Transit</h3><p class='br-muted'>The blood units are on the way to the requesting hospital.</p>")
        offsets = [0, 2, 11, 14, m["eta"] + 11]
        tl = ""
        for i, s in enumerate(STAGES):
            cls = "done" if i < ss.stage or (ss.stage == 4 and i == 4) else ("now" if i == ss.stage else "todo")
            t = (base + timedelta(minutes=offsets[i])).strftime("%I:%M %p") if i <= ss.stage else "Pending"
            tl += (f"<div class='tl'><div class='dot {cls}'>{'✓' if cls == 'done' else ''}</div>"
                   f"<div><b>{s}</b><br><span class='br-muted'>{t}</span></div></div>")
        html(f"<div class='br-card'>{tl}</div>")
        if ss.stage < 4:
            if st.button(f"Advance → {STAGES[ss.stage + 1]}", type="primary", use_container_width=True):
                ss.stage += 1
                ss.requests[0]["status"] = STAGES[ss.stage]
                st.rerun()
        else:
            if st.button("View Delivery Summary  →", type="primary", use_container_width=True):
                go_to("done")
        demo_notice("Click to simulate each delivery stage.")
    with r:
        prog = {0: 0, 1: 0, 2: 0.05, 3: 0.55, 4: 1.0}[ss.stage]
        eta_left = max(0, round(m["eta"] * (1 - prog)))
        html(f"<div class='br-card' style='display:flex;justify-content:space-between'>"
             f"<div><span class='br-muted'>From</span><br><b>{m['name']}</b></div>"
             f"<div><span class='br-muted'>Estimated arrival</span><br><span class='br-big'>{eta_left} mins</span></div></div>")
        st.plotly_chart(network_fig(highlight=m["name"], route_to=m, progress=prog, h=360), use_container_width=True, config=CFG)

def screen_done():
    ss = st.session_state
    if ss.stage < 4:
        go_to("track")
    if not ss.completed:
        ss.completed = True
        ss.requests[0]["status"] = "Delivered"
        ss.home["stock"]["O-"] += ss.request["units"]
        st.balloons()
    m = next(x for x in ss.hospitals if x["name"] == ss.selected)
    navbar("Delivery Completed")
    _, c, _ = st.columns([1, 1.6, 1])
    with c:
        html(f"<div class='br-card green' style='text-align:center'><div style='font-size:3rem'>✅</div>"
             f"<h3>Blood Successfully Delivered!</h3><p class='br-muted'>Received by the requesting hospital.</p>"
             f"<div style='text-align:left;margin-top:10px'>" + rows({
                 "Request ID": ss.request["id"], "Hospital": "City General Hospital", "Supplied by": m["name"],
                 "Blood Group": ss.request["group"], "Units Delivered": f"{ss.request['units']} Units",
                 "Total Time": f"{m['eta'] + 11} minutes"}) +
             "</div><p style='margin-top:14px'><i>“Every drop reaches a life.”</i> ❤️</p></div>")
        a, b = st.columns(2)
        if a.button("Open Hospital Dashboard", type="primary", use_container_width=True):
            go_to("dashboard")
        if b.button("Confirm & Close", use_container_width=True):
            go_to("landing")

def screen_login():
    navbar("Hospital Network")
    if st.button("← Home"):
        go_to("landing")
    l, r = st.columns([1.6, 1], gap="large")
    with l:
        html("<h3>Join the Blood Relay Network</h3><p class='br-muted'>Are you a new hospital or an existing partner?</p>")
        a, b = st.columns(2)
        with a:
            html("<div class='br-card' style='text-align:center'><div style='font-size:2.4rem'>🏥</div>"
                 "<p class='br-title'>New Hospital</p><p class='br-muted'>Register and join our network.</p></div>")
            if st.button("Register as New Hospital", type="primary", use_container_width=True):
                go_to("register")
        with b:
            html("<div class='br-card' style='text-align:center'><div style='font-size:2.4rem'>🏢</div>"
                 "<p class='br-title'>Existing Hospital</p><p class='br-muted'>Sign in to your dashboard.</p></div>")
            if st.button("Sign In to Network", type="primary", use_container_width=True):
                st.toast("Demo sign-in as City General Hospital", icon="🔓")
                go_to("dashboard")
    with r:
        demo_notice("Authentication is simulated. Click any button to continue.")

def screen_register():
    ss = st.session_state
    maybe_demo_popup("register")
    navbar("New Hospital Registration (Preview)")
    if st.button("← Back"):
        go_to("login")
    l, r = st.columns([1.6, 1], gap="large")
    with l:
        st.text_input("Hospital Name", "Sunrise Multispeciality Hospital", disabled=True)
        st.text_input("Address", "45, Anna Salai, Chennai, Tamil Nadu", disabled=True)
        a, b = st.columns(2)
        a.text_input("Team Size", "25 Members", disabled=True)
        b.text_input("Contact", "+91 98xxxxxx10", disabled=True)
        st.multiselect("Available Facilities", ["Blood Bank", "ICU", "Emergency Ward", "Ambulance", "Trauma Care", "Storage Units"],
                       default=["Blood Bank", "ICU", "Emergency Ward", "Ambulance", "Trauma Care", "Storage Units"], disabled=True)
        html("<div class='file'>📄 Hospital_Registration_Demo.pdf</div><div class='file'>📄 Blood_Bank_License_Demo.pdf</div>")
        st.write("")
        if ss.registered:
            html("<div class='br-card green'><span class='badge b-green'>Registered</span> Sunrise Multispeciality is already in the network.</div>")
            if st.button("Go to Dashboard →", type="primary", use_container_width=True):
                go_to("dashboard")
        elif st.button("Join Network", type="primary", use_container_width=True):
            ss.registered = True
            ss.hospitals.append(dict(name="Sunrise Multispeciality", area="Anna Salai", x=7.8, y=5.0, dist=6.1, eta=16, rating=4.2,
                                     stock={"O-": 2, "O+": 9, "A+": 6, "A-": 1, "B+": 5, "B-": 1, "AB+": 2, "AB-": 0}))
            st.toast("Hospital added to the network", icon="🎉")
            time.sleep(.4); st.rerun()
    with r:
        demo_notice("Form is non-editable. Click “Join Network” to simulate registration.")
        html("<div class='br-card' style='text-align:center'><div style='font-size:3rem'>🏥</div><p class='br-muted'>Be a part of the change.<br>Join today.</p></div>")

def screen_dashboard():
    ss = st.session_state
    with st.sidebar:
        html("<div class='br-brand'>🩸 BLOOD <b>RELAY</b></div><p class='br-muted'>City General Hospital</p>")
        sec = st.radio("Navigate", ["📊 Dashboard", "🚨 Emergency Requests", "🩸 Blood Stock", "🗺️ Network Map", "⚙️ Settings"],
                       label_visibility="collapsed")
        st.write("")
        if st.button("↩ Logout (end demo view)", use_container_width=True):
            go_to("landing")
    navbar("City General Hospital · Volunteer View &nbsp; <span class='badge b-blue'>Hospital Dashboard</span>")

    # Keep Home / Logout visible even when the Streamlit sidebar is collapsed.
    home_col, info_col = st.columns([1, 5])
    with home_col:
        if st.button("← Home / Log out", key="dashboard_home_logout", use_container_width=True):
            go_to("landing")
    with info_col:
        st.caption("You are viewing the hospital demo dashboard. Use Home / Log out to return to the main page.")

    reqs = pd.DataFrame(ss.requests)
    total_units = sum(ss.home["stock"].values())
    k = st.columns(4)
    k[0].metric("Total Requests", len(reqs))
    k[1].metric("Critical Requests", int((reqs.urgency == "Critical").sum()))
    k[2].metric("Available Units (yours)", total_units, f"+{ss.stock_updates * 6}" if ss.stock_updates else None)
    k[3].metric("Completed Deliveries", int((reqs.status == "Delivered").sum()))
    st.write("")

    def stock_chart():
        s = ss.home["stock"]
        f = go.Figure(go.Bar(x=list(s.keys()), y=list(s.values()), text=list(s.values()), textposition="outside",
                             marker_color=[C["red"] if v <= 2 else C["green"] if v > 10 else C["orange"] for v in s.values()]))
        f.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=C["text"]), yaxis=dict(gridcolor="#15283d"), xaxis=dict(showgrid=False))
        st.plotly_chart(f, use_container_width=True, config=CFG)

    def req_table():
        def style(v):
            return {"Critical": f"color:{C['red']}", "Urgent": f"color:{C['orange']}", "Delivered": f"color:{C['green']}"}.get(v, "")
        st.dataframe(reqs.style.map(style), hide_index=True, use_container_width=True)

    if sec.endswith("Dashboard"):
        l, r = st.columns([1.5, 1], gap="large")
        with l:
            html("<p class='br-title'>Live Emergency Map</p>")
            st.plotly_chart(network_fig(highlight=ss.selected, h=340), use_container_width=True, config=CFG)
        with r:
            html("<p class='br-title'>Critical Requests</p>")
            for q in ss.requests[:4]:
                b = "b-red" if q["urgency"] == "Critical" else "b-orange" if q["urgency"] == "Urgent" else "b-blue"
                html(f"<div class='br-card' style='padding:10px 14px;margin-bottom:8px'><b>{q['group']}</b> · {q['units']} units "
                     f"<span class='badge {b}' style='float:right'>{q['urgency']}</span><br>"
                     f"<span class='br-muted'>{q['id']} · {q['hospital']} · {q['status']}</span></div>")
        stock_chart()
    elif sec.endswith("Requests"):
        req_table()
        pick = st.selectbox("Inspect request", reqs.id.tolist())
        q = reqs[reqs.id == pick].iloc[0]
        html(f"<div class='br-card'>{rows(q.to_dict())}</div>")
    elif sec.endswith("Stock"):
        stock_chart()
        a, b = st.columns([1, 2])
        if a.button("Apply Demo Stock Update (+2 O-, +4 O+)", type="primary", use_container_width=True):
            ss.home["stock"]["O-"] += 2
            ss.home["stock"]["O+"] += 4
            ss.stock_updates += 1
            st.toast("Stock updated", icon="🩸")
            st.rerun()
        b.caption(f"Updates applied this session: {ss.stock_updates}")
    elif sec.endswith("Map"):
        g = st.radio("Highlight hospitals with stock of", list(COMPAT.keys()), horizontal=True)
        st.plotly_chart(network_fig(highlight=ss.selected, show_stock=g, h=460), use_container_width=True, config=CFG)
        st.dataframe(pd.DataFrame([{"Hospital": h["name"], "Area": h["area"], g: h["stock"].get(g, 0), "ETA (min)": h["eta"]}
                                   for h in ss.hospitals]), hide_index=True, use_container_width=True)
    else:
        html(f"<div class='br-card'>{rows({'Mode': 'Demo / prototype', 'Data': 'Fictional, in-memory (resets on refresh)', 'Version': 'Blood Relay v0.1 · Streamlit'})}</div>")
        if st.button("Reset entire demo"):
            st.session_state.clear(); st.rerun()

# ------------------------------------------------------------------ ROUTER
init_state()
{"landing": screen_landing, "request": screen_request, "search": screen_search, "match": screen_match,
 "track": screen_track, "done": screen_done, "login": screen_login, "register": screen_register,
 "dashboard": screen_dashboard}[st.session_state.page]()
