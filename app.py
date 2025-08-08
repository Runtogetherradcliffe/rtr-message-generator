
# RTR Message Generator — platform-specific wording + shuffle
# Plus:
# - Only show dates from NEXT THURSDAY onward
# - Label routes as 8k / 5k from the spreadsheet, add "(or Jeff it!)" to 5k
# - Restore special events messaging (Pride, Wear it green, Social, RTR on tour + Google Maps link)
import streamlit as st
import pandas as pd
import random
import os
from datetime import date, timedelta

# ---- Load spreadsheet (expects data/RTR route schedule.xlsx) ----
DATA_PATH = os.path.join("data", "RTR route schedule.xlsx")
try:
    df = pd.read_excel(DATA_PATH)
except Exception as e:
    st.error(f"Could not load spreadsheet at {DATA_PATH}. Please ensure the file exists in the repo. Error: {e}")
    st.stop()

st.title("RTR Message Generator")

# ---------------- Helpers ----------------
def seeded_choice(options, seed_str, tag):
    rnd = random.Random(f"{seed_str}:{tag}")
    return rnd.choice(options)

def next_thursday(today: date | None = None) -> date:
    if today is None:
        today = date.today()
    # Monday=0 ... Sunday=6; Thursday is 3
    days_ahead = (3 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # force NEXT Thursday
    return today + timedelta(days=days_ahead)

def date_label_from_cell(val):
    try:
        return val.strftime('%A %d %B %Y') if pd.notnull(val) else ""
    except Exception:
        return str(val) or ""

def safe_get(row, col):
    try:
        v = row.get(col)
        if v is None: return ""
        if isinstance(v, float) and pd.isna(v): return ""
        return str(v).strip()
    except Exception:
        return ""

# ---------------- Copy pools ----------------
INTRO_WA = [
    "Evening crew! Fancy a Thursday run? Here's the plan…",
    "Ready for Thursday miles? Here’s what’s happening…",
    "Hiya! Plan for this Thursday…",
]
INTRO_FB = [
    "Hello runners! Here’s what we’ve got lined up…",
    "Hey team — it’s nearly Thursday night run time!",
    "Evening crew! Here’s the plan…",
]
INTRO_IG = [
    "Thursday vibes. Let’s run.",
    "We run Thursday. You in?",
    "Ready to roll this Thursday?",
]
INTRO_EMAIL = [
    "Here are the details for Thursday’s run:",
    "This is the plan for Thursday’s run:",
    "Thursday run details:",
]

ROUTES_WA = [
    "📍 *Two routes on offer this Thursday:*",
    "🗺️ *Pick from two options this week:*",
]
ROUTES_FB = [
    "📍 Two routes on offer this Thursday:",
    "🗺️ Pick from two options this week:",
]
ROUTES_IG = [
    "Two routes tonight:",
    "Pick your route:",
]
ROUTES_EMAIL = [
    "Two routes available:",
    "Routes this week:",
]

OUTRO_WA = [
    "Happy running – see you soon!",
    "👟 See you Thursday!",
]
OUTRO_FB = [
    "Happy running – see you soon!",
    "Bring a mate, say hello – see you there!",
]
OUTRO_IG = [
    "See you out there ✌️",
    "Good vibes only ✨",
]
OUTRO_EMAIL = [
    "See you Thursday.",
    "Thanks, and see you soon.",
]

SAFETY_LINES = [
    "If you’re able to join us, please ensure you have your lights with you and wear hi-vis clothing.",
    "Please bring a headtorch and wear hi-vis so we can all be seen.",
    "Pack your lights and pop on some hi‑vis for the darker miles, please.",
]

# Special events templates
EVT_SOCIAL = [
    "🍻 After the run, many of us are going for drinks and food at the market – come along for a friendly social!",
    "🍻 Post‑run social at the market – grab a drink and a bite with us!",
]
EVT_GREEN = [
    "🟩 It's Mental Health Awareness Week – please wear something green. We’ll also have a relaxed social at the market afterwards.",
    "🟩 Wear something green for Mental Health Awareness Week, and stick around after for a market social.",
]
EVT_PRIDE = [
    "🏳️‍🌈 Our Pride run coincides with Manchester Pride – wear something colourful and bring the good vibes!",
    "🏳️‍🌈 Pride week! Bright kit encouraged – let’s celebrate together.",
]

def platform_copy(platform: str, *, seed: str):
    if platform == "WhatsApp":
        return {
            "intro": seeded_choice(INTRO_WA, seed, "intro"),
            "meet_lbl": "📍 *Meeting at:*",
            "time_lbl": "🕖 *We set off at 7:00pm*",
            "routes_lbl": seeded_choice(ROUTES_WA, seed, "routes"),
            "book_lbl": "📲 Book now:",
            "cancel_lbl": "❌ Can’t make it? Cancel at least 1 hour before:",
            "outro": seeded_choice(OUTRO_WA, seed, "outro"),
            "hashtags": None,
            "allow_emoji": True,
        }
    elif platform == "Facebook":
        return {
            "intro": seeded_choice(INTRO_FB, seed, "intro"),
            "meet_lbl": "📍 Meeting at:",
            "time_lbl": "🕖 We set off at 7:00pm",
            "routes_lbl": seeded_choice(ROUTES_FB, seed, "routes"),
            "book_lbl": "📲 Book now:",
            "cancel_lbl": "❌ Can’t make it? Cancel at least 1 hour before:",
            "outro": seeded_choice(OUTRO_FB, seed, "outro"),
            "hashtags": None,
            "allow_emoji": True,
        }
    elif platform == "Instagram":
        return {
            "intro": seeded_choice(INTRO_IG, seed, "intro"),
            "meet_lbl": "📍 Meeting at:",
            "time_lbl": "🕖 7:00pm start",
            "routes_lbl": seeded_choice(ROUTES_IG, seed, "routes"),
            "book_lbl": "Book now:",
            "cancel_lbl": "Can’t make it? Cancel at least 1 hour before:",
            "outro": seeded_choice(OUTRO_IG, seed, "outro"),
            "hashtags": " ".join(["#RunTogetherRadcliffe", "#RadcliffeRunners", "#ThursdayRun"]),
            "allow_emoji": True,
        }
    else:  # Email
        return {
            "intro": seeded_choice(INTRO_EMAIL, seed, "intro"),
            "meet_lbl": "Meeting at:",
            "time_lbl": "We set off at 7:00pm",
            "routes_lbl": seeded_choice(ROUTES_EMAIL, seed, "routes"),
            "book_lbl": "Book now:",
            "cancel_lbl": "Can’t make it? Cancel at least 1 hour before:",
            "outro": seeded_choice(OUTRO_EMAIL, seed, "outro"),
            "hashtags": None,
            "allow_emoji": False,
        }

def special_event_lines(platform: str, special_raw: str, meeting_point: str, maps_link: str, *, seed: str):
    """Return a list of lines to insert for special events."""
    if not special_raw:
        return []
    s = special_raw.lower()
    lines = []

    # Social after the run
    if "social after the run" in s or "social" in s:
        lines.append(seeded_choice(EVT_SOCIAL, seed, "ev_social"))

    # Wear it green
    if "wear it green" in s or "mental health awareness" in s:
        lines.append(seeded_choice(EVT_GREEN, seed, "ev_green"))

    # Pride
    if "pride" in s:
        lines.append(seeded_choice(EVT_PRIDE, seed, "ev_pride"))

    # RTR on tour
    if "rtr on tour" in s or "on tour" in s:
        mp = meeting_point or "the listed meet location"
        if maps_link:
            if platform == "Email":
                lines.append(f"We’re on tour – meet at {mp}. Map: {maps_link}")
            else:
                pin = "📍 " if platform != "Email" else ""
                lines.append(f"{pin}We’re on tour! Meet at {mp}. Map: {maps_link}")
        else:
            if platform == "Email":
                lines.append(f"We’re on tour – meet at {mp}.")
            else:
                pin = "📍 " if platform != "Email" else ""
                lines.append(f"{pin}We’re on tour! Meet at {mp}.")

    # If none matched, just echo
    if not lines and special_raw.strip():
        if platform == "Email":
            lines.append(f"This week features: {special_raw}")
        else:
            lines.append(f"🎉 This week features: {special_raw}")

    return lines

# ---------------- Build date options (future only) ----------------
df_dates = df.copy()
if "Date" in df_dates.columns:
    try:
        df_dates["Date"] = pd.to_datetime(df_dates["Date"]).dt.date
    except Exception:
        pass

nt = next_thursday()
mask = (df_dates["Date"] >= nt)
future_df = df_dates.loc[mask].reset_index(drop=True)

if future_df.empty:
    st.warning("No future runs found from next Thursday onwards.")
    st.stop()

date_options = [(date_label_from_cell(d), i) for i, d in enumerate(future_df["Date"])]
labels = [x[0] for x in date_options]
selected_label = st.selectbox("Choose a date", options=labels, index=0, key="date_select")
selected_idx = labels.index(selected_label)
row = future_df.iloc[selected_idx]

# ---------------- Fields ----------------
meeting_point = (
    safe_get(row, "Meeting location")
    or safe_get(row, "Meeting point")
    or "Radcliffe market"
)
maps_link = safe_get(row, "Meeting point google link") or safe_get(row, "Meeting location google link")
surface = (safe_get(row, "Surface") or safe_get(row, "Notes"))
special = safe_get(row, "Special events")

# Extract 8k and 5k routes explicitly
r8_name = safe_get(row, "8k Route"); r8_link = safe_get(row, "8k Strava link")
r5_name = safe_get(row, "5k Route"); r5_link = safe_get(row, "5k Strava link")

routes = []
if r8_name and r8_link:
    routes.append(("8k", r8_name, r8_link))
if r5_name and r5_link:
    routes.append(("5k", r5_name, r5_link))

# ---------------- UI controls ----------------
platform = st.selectbox("Platform", options=["WhatsApp","Facebook","Instagram","Email"], index=0, key="platform_select")

# Shuffle
if "var_seed_offset" not in st.session_state:
    st.session_state["var_seed_offset"] = 0
if st.button("🔀 Shuffle wording", key="shuffle_btn"):
    st.session_state["var_seed_offset"] += 1
seed = f"{selected_label}|{platform}#{st.session_state['var_seed_offset']}"

# ---------------- Build preview (layout preserved) ----------------
cp = platform_copy(platform, seed=seed)
lines = []
lines.append(cp["intro"]); lines.append("")
lines.append(f"{cp['meet_lbl']} {meeting_point}")
lines.append(f"{cp['time_lbl']}"); lines.append("")
lines.append(cp["routes_lbl"])

if routes:
    for label, name, url in routes:
        if label == "5k":
            lines.append(f"• {label} – {name}: {url} (or Jeff it!)")
        else:
            lines.append(f"• {label} – {name}: {url}")
else:
    lines.append("• (Routes not found in spreadsheet)")

# Safety if after dark
if "after dark" in surface.lower():
    lines.append("")
    lines.append(seeded_choice(SAFETY_LINES, seed, "safety"))

# Special events (restored)
ev_lines = special_event_lines(platform, special, meeting_point, maps_link, seed=seed)
if ev_lines:
    lines.append("")
    lines.extend(ev_lines)

# Book/cancel
lines.append("")
lines.append(f"{cp['book_lbl']} https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs")
lines.append(f"{cp['cancel_lbl']} https://groups.runtogether.co.uk/My/BookedRuns")
lines.append("")
lines.append(cp["outro"])
if cp.get("hashtags"):
    lines.append(cp["hashtags"])

preview = "\n".join(lines)

st.subheader("Preview messages")
st.text_area("Generated message", value=preview, height=420, key="preview_text")

st.download_button("Download message as .txt", data=preview, file_name=f"RTR_{selected_label.replace(' ','_')}_{platform}.txt", mime="text/plain", key="download_btn")
