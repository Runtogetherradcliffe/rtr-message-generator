
# RTR Message Generator — platform-specific wording + shuffle
# Tweaks:
# - Only show dates from NEXT THURSDAY onward
# - Label routes as 8k / 5k from the spreadsheet
# - Append "(or Jeff it!)" to the 5k route text
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
    # If today is Thursday, we still want *next* Thursday
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)

def date_label_from_cell(val):
    try:
        return val.strftime('%A %d %B %Y') if pd.notnull(val) else ""
    except Exception:
        return str(val) or ""

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
        }

# ---------------- Build date options (future only) ----------------
# Convert Date column to date (if it's datetime)
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
location = (
    row.get("Meeting location")
    or row.get("Meeting point")
    or "Radcliffe market"
)
surface = (row.get("Surface") or row.get("Notes") or "").strip()

# Extract 8k and 5k routes explicitly so we can label bullets
def safe_get(col): 
    try:
        v = row.get(col)
        return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v).strip()
    except Exception:
        return ""

r8_name = safe_get("8k Route"); r8_link = safe_get("8k Strava link")
r5_name = safe_get("5k Route"); r5_link = safe_get("5k Strava link")

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
lines.append(f"{cp['meet_lbl']} {location}")
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

if "after dark" in surface.lower():
    lines.append("")
    lines.append(seeded_choice(SAFETY_LINES, seed, "safety"))

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
