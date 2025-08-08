"""
RunTogether Radcliffe – Weekly Message Generator (Streamlit)

This version includes NaN-safe handling for spreadsheet cells to prevent
AttributeError on weeks where cells are blank (e.g., Special events).
"""

from __future__ import annotations
import os
import json
import time
import random
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple

import pandas as pd
import requests
import streamlit as st
from dateutil import tz

# =============================
# Config shim (Streamlit first)
# =============================

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read from st.secrets if present, otherwise env vars (for easy Render port)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)

# =============================
# Constants & helpers
# =============================
UK_TZ = tz.gettz("Europe/London")

ELEVATION_TEXT_CHOICES = [
    (0, 20, [
        "flat as a pancake 🥞",
        "pancake-flat",
        "nice and flat",
        "no climbs to worry about",
    ]),
    (20, 60, [
        "a gently rolling route 🌿",
        "soft ups and downs",
        "a touch of undulation",
        "lightly rolling",
    ]),
    (60, 140, [
        "some hills this week ⛰️",
        "a few punchy rises",
        "rolling with a couple of climbs",
        "a bit lumpy",
    ]),
    (140, 99999, [
        "hilly – bring your climbing legs! 🧗",
        "properly hilly",
        "plenty of climbing on tap",
        "a big-elevation outing",
    ]),
]

def seeded_choice(options: List[str], seed: str, tag: str) -> str:
    rnd = random.Random(f"{seed}:{tag}")
    return rnd.choice(options)

def describe_elevation(total_elev_m: float, *, seed: str = "") -> str:
    for lo, hi, choices in ELEVATION_TEXT_CHOICES:
        if lo <= total_elev_m < hi:
            return seeded_choice(choices, seed, f"elev_{lo}_{hi}")
    return "varied terrain"

def next_thursday(today: Optional[date] = None) -> date:
    today = today or datetime.now(UK_TZ).date()
    days_ahead = (3 - today.weekday()) % 7  # Monday=0 ... Thursday=3
    return today + timedelta(days=days_ahead)

def cell_text(row: pd.Series, key: str, default: str = "") -> str:
    """Safely extract text from a row; returns '' for NaN/None."""
    try:
        val = row.get(key, default)
    except Exception:
        val = default
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()

# =============================
# Sheet loading & parsing
# =============================
@st.cache_data(show_spinner=False, ttl=600)
def load_schedule(path: str = "data/RTR route schedule.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="schedule")
    expected = [
        'Week','Date','Special events','Notes','Meeting point','Meeting point google link',
        '8k Route','8k Strava link','5k Route','5k Strava link'
    ]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

# =============================
# Strava API
# =============================
STRAVA_BASE = "https://www.strava.com/api/v3"

@dataclass
class StravaRoute:
    id: int
    name: str
    distance_km: float
    elevation_m: float
    summary_polyline: Optional[str]

@st.cache_data(show_spinner=False, ttl=60*60*24)
def strava_exchange_refresh(refresh_token: str) -> Dict:
    client_id = get_secret("STRAVA_CLIENT_ID")
    client_secret = get_secret("STRAVA_CLIENT_SECRET")
    r = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }, timeout=20,
    )
    r.raise_for_status()
    return r.json()

@st.cache_data(show_spinner=False, ttl=60*60*24)
def strava_exchange_code(auth_code: str) -> Dict:
    client_id = get_secret("STRAVA_CLIENT_ID")
    client_secret = get_secret("STRAVA_CLIENT_SECRET")
    r = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
        }, timeout=20,
    )
    r.raise_for_status()
    return r.json()

@st.cache_data(show_spinner=False, ttl=60*60*24)
def get_route_meta(access_token: str, route_id: int) -> StravaRoute:
    r = requests.get(
        f"{STRAVA_BASE}/routes/{route_id}",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=20
    )
    r.raise_for_status()
    data = r.json()
    dist_km = (data.get("distance", 0) or 0)/1000.0
    elev_m = data.get("elevation_gain", 0) or 0
    poly = data.get("map", {}).get("summary_polyline")
    return StravaRoute(
        id=int(data.get("id")),
        name=str(data.get("name")),
        distance_km=round(dist_km, 1),
        elevation_m=round(elev_m, 0),
        summary_polyline=poly,
    )

def extract_route_id_from_strava_url(url: str) -> Optional[int]:
    try:
        parts = url.strip('/').split('/')
        idx = parts.index('routes')
        return int(parts[idx+1])
    except Exception:
        return None

# =============================
# Polyline decode & LocationIQ
# =============================
def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    points = []
    index = lat = lng = 0
    while index < len(encoded):
        result = 1
        shift = 0
        b = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1f:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        result = 1
        shift = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1f:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng
        points.append((lat * 1e-5, lng * 1e-5))
    return points

@st.cache_data(show_spinner=False, ttl=60*60*24*7)
def locationiq_reverse(lat: float, lon: float) -> Optional[Dict]:
    key = get_secret("LOCATIONIQ_API_KEY")
    if not key:
        return None
    url = "https://us1.locationiq.com/v1/reverse"
    params = {"key": key, "lat": lat, "lon": lon, "format": "json", "zoom": 17}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def on_route_landmarks(polyline: Optional[str], max_points: int = 8) -> List[str]:
    if not polyline:
        return []
    coords = decode_polyline(polyline)
    if not coords:
        return []
    step = max(1, len(coords) // max_points)
    sampled = coords[::step][:max_points]
    names: List[str] = []
    seen = set()
    for (lat, lon) in sampled:
        info = locationiq_reverse(lat, lon)
        if not info:
            continue
        props = info.get("address", {})
        candidates = [
            props.get("road"), props.get("pedestrian"), props.get("footway"), props.get("path"),
            props.get("cycleway"), props.get("neighbourhood"), props.get("suburb"), props.get("hamlet"),
            info.get("display_name")
        ]
        name = next((c for c in candidates if c), None)
        if not name:
            continue
        name = str(name).strip()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        names.append(name)
        if len(names) >= max_points:
            break
    return names

# =============================
# Message generation – richer variety
# =============================
GREETINGS = [
    "👋 Hope you're having a great week!",
    "Hey team!",
    "Hiya!",
    "Evening crew!",
    "Hello runners!",
    "Ready to run?",
]

THURSDAY_LEADS = [
    "Here's what's lined up for Thursday…",
    "Thursday's nearly here – time to lace up!",
    "Fancy a Thursday run? Here's the plan…",
    "This week's routes are looking good:",
    "Two routes ready for you this Thursday:",
]

ROUTE_INTROS_GENERAL = [
    "🛣️ This week we’ve got two route options to choose from:",
    "🗺️ Pick your route – two options this week:",
    "🏃 Two choices – take your pick:",
    "📍 Two routes on offer this Thursday:",
]

TRAIL_INTROS = [
    "🌿 Summer trails are calling – expect softer ground and scenery!",
    "🌳 Trail time! Let's enjoy the paths while the light lasts.",
    "🟢 Trails this week – watch your footing and enjoy the views.",
]

ROAD_INTROS = [
    "🚦 It's road time as the evenings draw in.",
    "💡 Running after dark means roads this week.",
    "🛣️ Sticking to the roads tonight for safety.",
]

SAFETY_NOTES = [
    "If you’re able to join us, please ensure you have your lights with you and wear hi-vis clothing.",
    "Please bring a headtorch and wear hi-vis so we can all be seen.",
    "Pack your lights and pop on some hi‑vis for the darker miles, please.",
]

OUTROS = [
    "👟 Grab your shoes, bring your smiles – see you Thursday!",
    "See you at 7:00pm – let's make it a good one!",
    "Bring a mate, say hello, and enjoy the miles!",
    "Happy running – see you soon!",
]

EVENT_TEMPLATES = {
    "Social after the run": [
        "🍻 After the run, many of us are going for drinks and food at the market – come along for a friendly social!",
        "🍻 Post‑run social at the market – come for a drink and a bite!",
    ],
    "Wear it green": [
        "🟩 It's Mental Health Awareness Week – we're encouraging everyone to wear something green. Afterwards, join us at the market for a relaxed social.",
        "🟩 Wear something green for Mental Health Awareness Week, and stick around after for a market social.",
    ],
    "Pride": [
        "🏳️‍🌈 Our Pride Run coincides with Manchester Pride – wear something colourful and show your support!",
        "🏳️‍🌈 Pride week! Bring the colour and the good vibes.",
    ],
}

def build_intro(seed: str, terrain: str, special: str) -> str:
    g = seeded_choice(GREETINGS, seed, "greet")
    t = seeded_choice(THURSDAY_LEADS, seed, "lead")
    bits = [g, t]
    if terrain == "trail":
        bits.append(seeded_choice(TRAIL_INTROS, seed, "trail"))
    elif terrain == "road":
        bits.append(seeded_choice(ROAD_INTROS, seed, "road"))
    return " ".join(bits)

def special_event_blurb(event_cell: Optional[str], meet_maps: Optional[str], *, seed: str = "") -> str:
    if not event_cell:
        return ""
    text: List[str] = []
    e = event_cell.lower()
    if "social" in e:
        text.append(seeded_choice(EVENT_TEMPLATES["Social after the run"], seed, "ev_social"))
    if "rtr on tour" in e and meet_maps:
        text.append(f"📍 We're on tour! Tap for the meet point: {meet_maps}")
    if "wear it green" in e:
        text.append(seeded_choice(EVENT_TEMPLATES["Wear it green"], seed, "ev_green"))
    if "pride" in e:
        text.append(seeded_choice(EVENT_TEMPLATES["Pride"], seed, "ev_pride"))
    if not text:
        text.append(f"🎉 This week features: {event_cell}")
    return "\n".join(text)

def platform_blocks(
    platform: str,
    *,
    intro: str,
    route_intro: str,
    meet_point: str,
    depart_time: str,
    routes: List[Tuple[str, str, float, float, List[str]]],
    terrain_flag: str,
    safety_note: Optional[str],
    event_text: str,
    outro: str,
) -> str:
    lines: List[str] = []
    wa_bold = (lambda s: f"*{s}*") if platform == "WhatsApp" else (lambda s: s)

    lines.append(intro)
    lines.append("")
    lines.append(f"📍 Meeting at: {meet_point}")
    lines.append(f"🕖 We set off at 7:00pm")
    lines.append("")
    lines.append(route_intro)

    for label, url, km, elev, landmarks in routes:
        elev_desc = describe_elevation(elev, seed=intro)
        lines.append(f"• {label}: {url}")
        if km and elev is not None:
            lines.append(f"  {km:.1f} km with {int(elev)}m of elevation – {elev_desc}")
        if landmarks:
            lines.append(f"  🏞️ This route passes " + ", ".join(landmarks))

    if terrain_flag == "road" and safety_note:
        lines.append("")
        lines.append(safety_note)

    if event_text:
        lines.append("")
        lines.append(event_text)

    lines.append("")
    lines.append("📲 Book now: https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs")
    lines.append("❌ Can’t make it? Cancel at least 1 hour before: https://groups.runtogether.co.uk/My/BookedRuns")

    lines.append("")
    lines.append(outro)

    text = "\n".join(lines)

    if platform == "Email":
        return text
    elif platform == "WhatsApp":
        text = text.replace("Meeting at:", wa_bold("Meeting at:"))
        text = text.replace("We set off at 7:00pm", wa_bold("We set off at 7:00pm"))
        return text
    elif platform in {"Facebook", "Instagram"}:
        return text
    else:
        return text

# =============================
# UI – Admin & Generator
# =============================

def admin_page():
    st.title("Admin Settings")
    st.caption("Connect Strava, manage tokens, and test APIs.")

    admin_pass = get_secret("ADMIN_PASS")
    if admin_pass:
        pw = st.text_input("Admin password", type="password")
        if pw != admin_pass:
            st.stop()

    st.subheader("Strava – OAuth setup")
    client_id = get_secret("STRAVA_CLIENT_ID")
    client_secret = get_secret("STRAVA_CLIENT_SECRET")
    if not (client_id and client_secret):
        st.warning("Add STRAVA_CLIENT_ID/STRAVA_CLIENT_SECRET in Secrets first.")
    app_url = st.text_input("Your app URL (exactly as it appears in the browser)")
    if client_id and app_url:
        auth_url = (
            f"https://www.strava.com/oauth/authorize?client_id={client_id}"
            f"&response_type=code&redirect_uri={app_url}"
            f"&approval_prompt=auto&scope=read,read_all"
        )
        st.write("1) Set your Strava application's callback URL to your app root (same as above).")
        st.code(app_url)
        st.write("2) Click to authorise:")
        st.code(auth_url)

    qp = st.experimental_get_query_params()
    if "code" in qp:
        auth_code = qp["code"][0]
        st.info("Auth code detected in URL – exchanging for tokens…")
        try:
            token_data = strava_exchange_code(auth_code)
            refresh_token = token_data.get("refresh_token")
            access_token = token_data.get("access_token")
            st.success("Token exchange successful.")
            st.write("Copy this REFRESH TOKEN into Streamlit Secrets as STRAVA_REFRESH_TOKEN:")
            st.code(refresh_token)
            st.write("(After saving secrets, click ‘Rerun’ to use it.)")
        except Exception as e:
            st.error(f"Exchange failed: {e}")

    st.divider()
    st.subheader("LocationIQ")
    if not get_secret("LOCATIONIQ_API_KEY"):
        st.warning("Add LOCATIONIQ_API_KEY to Secrets.")
    else:
        st.success("LocationIQ key present.")

    st.divider()
    st.subheader("Test Strava route fetch")
    refresh = get_secret("STRAVA_REFRESH_TOKEN")
    rid_input = st.text_input("Strava route URL or ID")
    if st.button("Fetch route meta") and rid_input:
        try:
            route_id = int(rid_input) if rid_input.isdigit() else extract_route_id_from_strava_url(rid_input)
            if not route_id:
                st.error("Could not parse route ID.")
            else:
                if not refresh:
                    st.warning("No STRAVA_REFRESH_TOKEN in secrets. Complete OAuth above, then paste it into Secrets.")
                else:
                    td = strava_exchange_refresh(refresh)
                    access = td.get("access_token")
                    sr = get_route_meta(access, route_id)
                    st.json(sr.__dict__)
                    lms = on_route_landmarks(sr.summary_polyline)
                    st.write("Landmarks:", ", ".join(lms) if lms else "(none)")
        except Exception as e:
            st.error(str(e))

def generator_page():
    st.title("RunTogether Radcliffe – Weekly Message Generator")
    st.caption("Generates friendly, varied messages for WhatsApp, Facebook, Instagram, and Email.")

    with st.expander("Data source", expanded=True):
        st.write("Reading schedule from `data/RTR route schedule.xlsx` (commit updates to GitHub).")

    try:
        df = load_schedule()
    except Exception as e:
        st.error(f"Could not load schedule: {e}")
        st.stop()

    dates = sorted(df['Date'].unique())
    default_date = next_thursday()
    if default_date not in dates and dates:
        default_date = dates[0]

    chosen_date = st.selectbox("Pick the run date", options=dates, index=dates.index(default_date) if default_date in dates else 0)

    row = df.loc[df['Date'] == chosen_date].iloc[0]

    meet_point = cell_text(row, 'Meeting point') or 'Radcliffe Market'
    meet_link  = cell_text(row, 'Meeting point google link')
    notes      = cell_text(row, 'Notes')
    special    = cell_text(row, 'Special events')

    terrain_flag = 'trail' if 'trail' in notes.lower() else 'road' if 'after dark' in notes.lower() else ''

    base_seed = f"{chosen_date}-{terrain_flag}-{special}"
    if 'var_seed_offset' not in st.session_state:
        st.session_state['var_seed_offset'] = 0
    if st.button("🔀 Shuffle wording"):
        st.session_state['var_seed_offset'] += 1
    seed = f"{base_seed}-#{st.session_state['var_seed_offset']}"

    routes_in = [
        (cell_text(row, '8k Route', '8k route'), cell_text(row, '8k Strava link')),
        (cell_text(row, '5k Route', '5k route'), cell_text(row, '5k Strava link')),
    ]

    refresh = get_secret("STRAVA_REFRESH_TOKEN")
    access = None
    if refresh:
        try:
            td = strava_exchange_refresh(refresh)
            access = td.get("access_token")
        except Exception:
            access = None

    routes_out: List[Tuple[str, str, float, float, List[str]]] = []
    for name, url in routes_in:
        km = 0.0
        elev = 0.0
        lms: List[str] = []
        if url and access:
            rid = extract_route_id_from_strava_url(url)
            if rid:
                try:
                    meta = get_route_meta(access, rid)
                    km = meta.distance_km
                    elev = meta.elevation_m
                    lms = on_route_landmarks(meta.summary_polyline)
                except Exception:
                    pass
        routes_out.append((name, url or "", km, elev, lms))

    intro = build_intro(seed, terrain_flag, special)
    route_intro = seeded_choice(ROUTE_INTROS_GENERAL, seed, "route_intro")
    safety_note = seeded_choice(SAFETY_NOTES, seed, "safety") if terrain_flag == 'road' else None
    event_text = special_event_blurb(special, meet_link, seed=seed)
    outro = seeded_choice(OUTROS, seed, "outro")

    st.subheader("Preview messages")
    platform = st.selectbox("Platform", ["WhatsApp", "Facebook", "Instagram", "Email"], index=0)

    msg = platform_blocks(
        platform,
        intro=intro,
        route_intro=route_intro,
        meet_point=meet_point,
        depart_time="7:00pm",
        routes=routes_out,
        terrain_flag=terrain_flag,
        safety_note=safety_note,
        event_text=event_text,
        outro=outro,
    )

    st.text_area("Generated message", value=msg, height=420)

    st.download_button(
        label="Download message as .txt",
        data=msg,
        file_name=f"RTR_{chosen_date}_{platform}.txt",
        mime="text/plain",
    )

    st.info("URLs are shown in full. WhatsApp uses *bold* for emphasis. Email is plain text only. You can use ‘Shuffle wording’ to try alternative phrasings for the same week.")

# =============================
# App router
# =============================

def main():
    st.set_page_config(page_title="RTR Message Generator", page_icon="🏃", layout="centered")
    page = st.sidebar.radio("Navigation", ["Generator", "Admin"], index=0)
    if page == "Admin":
        admin_page()
    else:
        generator_page()

if __name__ == "__main__":
    main()



def _pr_fetch_data(date_choice, check_course_pbs=False):
    # Try global, then UK site as fallback
    bases = [
        "https://www.parkrun.com",
        "https://www.parkrun.org.uk",
    ]
    path = "/results/consolidatedclub/"
    qs = f"?clubNum=49581&eventDate={date_choice.strftime('%Y-%m-%d')}"

    # Browsery headers to avoid basic bot blocks
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Referer": "https://www.parkrun.com/results/consolidatedclub/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    last_err = None
    for base in bases:
        url = f"{base}{path}{qs}"
        try:
            s = _pr_requests.Session()
            s.headers.update(headers)
            r = s.get(url, timeout=30, allow_redirects=True)
            # One light retry on 403 with a slightly different UA
            if r.status_code == 403:
                s.headers["User-Agent"] = (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
                )
                r = s.get(url, timeout=30, allow_redirects=True)
            r.raise_for_status()

            soup = _pr_BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", class_="Results")
            if not table:
                return []

            out = []
            for tr in table.find_all("tr")[1:]:  # skip header
                tds = tr.find_all("td")
                if len(tds) < 7:
                    continue

                def txt(i):
                    try:
                        return tds[i].get_text(strip=True)
                    except Exception:
                        return ""

                name   = txt(0)
                event  = txt(1)
                time   = txt(3)
                note   = txt(6)  # PB / First timer flags usually here

                if not name or not event:
                    continue

                ach = []
                if "PB" in note:
                    ach.append("parkrun PB")
                if "First timer" in note:
                    ach.append("First time at this event")

                if check_course_pbs:
                    pass  # keep optional deep check off by default

                out.append({"name": name, "event": event, "time": time or "—", "achievements": ach})

            return out

        except Exception as e:
            last_err = e
            continue

    # If all bases failed, raise the last error so the UI shows a friendly message
    if last_err:
        raise last_err
    return []

