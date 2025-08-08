
# RTR Message Generator — Platform-specific wording (layout preserved) + Shuffle (fixed keys)
import streamlit as st
import pandas as pd
import random
import os

# ---- Load spreadsheet (expects data/RTR route schedule.xlsx) ----
DATA_PATH = os.path.join("data", "RTR route schedule.xlsx")
try:
    df = pd.read_excel(DATA_PATH)
except Exception as e:
    st.error(f"Could not load spreadsheet at {DATA_PATH}. Please ensure the file exists in the repo. Error: {e}")
    st.stop()

st.title("RTR Message Generator")

# ---------------- Variation helpers & copy pools ----------------
def seeded_choice(options, seed_str, tag):
    rnd = random.Random(f"{seed_str}:{tag}")
    return rnd.choice(options)

INTRO_WA = [
    "Evening crew! Fancy a Thursday run? Here's the plan…",
    "Ready for Thursday miles? Here’s what’s happening…",
    "Hiya! Plan for this Thursday…",
]
INTRO_FB = [
    "Evening crew! Fancy a Thursday run? Here's the plan…",
    "Hey team — it’s nearly Thursday night run time!",
    "Hello runners! Here’s what we’ve got lined up…",
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

def date_label_from_cell(val):
    try:
        return val.strftime('%A %d %B %Y') if pd.notnull(val) else ""
    except Exception:
        return str(val) or ""

# ---- Build date options ----
date_options = []
for idx, row in df.iterrows():
    date_label = date_label_from_cell(row.get("Date"))
    if date_label:
        date_options.append((date_label, idx))

if not date_options:
    st.warning("No runs found in the spreadsheet.")
    st.stop()

labels = [x[0] for x in date_options]
selected_label = st.selectbox("Choose a date", options=labels, index=0, key="date_select")
selected_idx = dict(date_options)[selected_label]
row = df.iloc[selected_idx]

# ---- Fields ----
location = (
    row.get("Meeting location")
    or row.get("Meeting point")
    or "Radcliffe market"
)
surface = (row.get("Surface") or row.get("Notes") or "").strip()

# Extract routes
routes = []
def safe_get(col): 
    try:
        v = row.get(col)
        return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v).strip()
    except Exception:
        return ""
pairs = [("8k Route","8k Strava link"), ("5k Route","5k Strava link")]
for name_col, url_col in pairs:
    name, url = safe_get(name_col), safe_get(url_col)
    if name and url:
        routes.append((name, url))

platform = st.selectbox("Platform", options=["WhatsApp","Facebook","Instagram","Email"], index=0, key="platform_select")

# Shuffle
if "var_seed_offset" not in st.session_state:
    st.session_state["var_seed_offset"] = 0
if st.button("🔀 Shuffle wording", key="shuffle_btn"):
    st.session_state["var_seed_offset"] += 1
seed = f"{selected_label}|{platform}#{st.session_state['var_seed_offset']}"

# Build preview (layout preserved)
cp = platform_copy(platform, seed=seed)
lines = []
lines.append(cp["intro"]); lines.append("")
lines.append(f"{cp['meet_lbl']} {location}")
lines.append(f"{cp['time_lbl']}"); lines.append("")
lines.append(cp["routes_lbl"])
if routes:
    for name, url in routes:
        lines.append(f"• {name}: {url}")
else:
    lines.append("• (Routes not found in spreadsheet)")
if "after dark" in surface.lower():
    lines.append(""); lines.append(seeded_choice(SAFETY_LINES, seed, "safety"))
lines.append("")
lines.append(f"{cp['book_lbl']} https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs")
lines.append(f"{cp['cancel_lbl']} https://groups.runtogether.co.uk/My/BookedRuns")
lines.append("")
lines.append(cp["outro"])
if cp.get("hashtags"):
    lines.append(cp["hashtags"])

preview = "\n".join(lines)

st.subheader("Preview messages")
# Show the selected platform as a disabled widget with a UNIQUE KEY to avoid duplicate IDs
st.selectbox("Platform", options=["WhatsApp","Facebook","Instagram","Email"], index=["WhatsApp","Facebook","Instagram","Email"].index(platform), disabled=True, key="platform_preview_ro")
st.text_area("Generated message", value=preview, height=420, key="preview_text")

st.download_button("Download message as .txt", data=preview, file_name=f"RTR_{selected_label.replace(' ','_')}_{platform}.txt", mime="text/plain", key="download_btn")
