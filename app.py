
# RTR Message Generator — Platform-specific wording + Tone + Shuffle
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

# ---- Variation helpers & copy pools ----
def seeded_choice(options, seed_str, tag):
    rnd = random.Random(f"{seed_str}:{tag}")
    return rnd.choice(options)

FB_INTROS = [
    "👋 {date} run is nearly here!",
    "Hey team — {date} plans are set!",
    "Hiya! Ready for {date}?",
    "Evening crew — here’s {date} at a glance:",
]
FB_OUTROS = [
    "👟 See you Thursday!",
    "Bring a mate and let’s go!",
    "Happy miles — see you soon!",
]

IG_INTROS = [
    "Let’s go • {date}",
    "Thursday vibes • {date}",
    "We run • {date}",
    "Ready to roll • {date}",
]
IG_OUTROS = [
    "See you out there ✌️",
    "Let’s move 🏃",
    "Good vibes only ✨",
]

EMAIL_INTROS = [
    "Thursday run – {date}",
    "Plan for Thursday – {date}",
    "This week’s run – {date}",
]
EMAIL_OUTROS = [
    "See you Thursday,",
    "Thanks and see you soon,",
    "All the best,",
]

SAFETY_VARIATIONS = [
    "If you’re able to join us, please ensure you have your lights with you and wear hi-vis clothing.",
    "Please bring a headtorch and wear hi-vis so we can all be seen.",
    "Pack your lights and pop on some hi-vis for the darker miles, please.",
]

# Tone options
TONE_OPTIONS = ["Friendly", "Energetic", "Understated"]

FB_TONE = {
    "Energetic": {
        "intros": [
            "🔥 Let’s go — {date}!",
            "Big energy for {date} — who’s in?",
            "We’re buzzing for {date} — lace up!",
        ],
        "outros": [
            "Let’s make it a good one! 💥",
            "Bring the energy — see you there!",
        ],
    },
    "Understated": {
        "intros": [
            "{date} run details below.",
            "Plans for {date}.",
            "A steady one on {date}.",
        ],
        "outros": [
            "See you then.",
            "Nice and steady — see you there.",
        ],
    },
}

IG_TONE = {
    "Energetic": {
        "intros": [
            "We move • {date} 🔥",
            "Let’s fly • {date} 💨",
            "Hype mode • {date} ⚡",
        ],
        "outros": [
            "Full send 🚀",
            "Let’s roll 🏃",
        ],
    },
    "Understated": {
        "intros": [
            "Run day • {date}",
            "Thursday • {date}",
            "Easy miles • {date}",
        ],
        "outros": [
            "See you there.",
            "Nice and easy.",
        ],
    },
}

EMAIL_TONE = {
    "Energetic": {
        "intros": [
            "Thursday run – {date} (let’s go!)",
            "This week’s run – {date} (ready to move?)",
        ],
        "outros": [
            "Let’s make it a good one,",
            "See you on the start line,",
        ],
    },
    "Understated": {
        "intros": [
            "Run details for {date}",
            "Plan for {date}",
        ],
        "outros": [
            "See you then,",
            "Thanks,",
        ],
    },
}

def platform_message(platform: str, date_str: str, location: str, surface: str, *, seed: str, tone: str) -> str:
    is_trail = "trail" in surface.lower()
    after_dark = "after dark" in surface.lower()

    meet_line = f"Meeting at: {location}"
    time_line = "We set off at 7:00pm"
    safety = seeded_choice(SAFETY_VARIATIONS, seed, "safety") if after_dark else ""
    booking = "📲 Book now: https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs"
    cancel  = "❌ Can’t make it? Cancel at least 1 hour before: https://groups.runtogether.co.uk/My/BookedRuns"

    if platform == "Facebook":
        intro_pool = FB_INTROS + FB_TONE.get(tone, {}).get("intros", [])
        outro_pool = FB_OUTROS + FB_TONE.get(tone, {}).get("outros", [])
        intro = seeded_choice(intro_pool, seed, "fb_intro").format(date=date_str)
        outro = seeded_choice(outro_pool, seed, "fb_outro")
        vibe = "🌿 Trail night" if is_trail else "🛣️ Road run"
        lines = [f"{intro}", "", f"📍 {meet_line}", f"🕖 {time_line}", f"{vibe}"]
        if safety: lines += ["", safety]
        lines += ["", booking, cancel, "", outro]
        return "\n".join(lines)

    elif platform == "Instagram":
        intro_pool = IG_INTROS + IG_TONE.get(tone, {}).get("intros", [])
        outro_pool = IG_OUTROS + IG_TONE.get(tone, {}).get("outros", [])
        intro = seeded_choice(intro_pool, seed, "ig_intro").format(date=date_str)
        outro = seeded_choice(outro_pool, seed, "ig_outro")
        vibe = "🌿 Trails tonight" if is_trail else "🛣️ Roads tonight"
        body = [f"{intro}", f"{vibe}", f"📍 {location}", f"🕖 7:00pm start"]
        if safety: body.append("💡 Bring lights + wear hi-vis")
        tags = ["#RunTogetherRadcliffe", "#RadcliffeRunners", "#ThursdayRun", "#TrailRun" if is_trail else "#RoadRun"]
        footer = ["", "Book now:", "https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs",
                  "Can’t make it? Cancel at least 1 hour before:", "https://groups.runtogether.co.uk/My/BookedRuns",
                  "", " ".join(tags), outro]
        return "\n".join(body + [""] + footer)

    else:  # Email
        intro_pool = EMAIL_INTROS + EMAIL_TONE.get(tone, {}).get("intros", [])
        outro_pool = EMAIL_OUTROS + EMAIL_TONE.get(tone, {}).get("outros", [])
        intro = seeded_choice(intro_pool, seed, "em_intro").format(date=date_str)
        outro = seeded_choice(outro_pool, seed, "em_outro")
        lines = [f"{intro}", "", f"Meeting at: {location}", "We set off at 7:00pm"]
        if is_trail: lines.append("Surface: Trail")
        elif after_dark: lines.append("Surface: Road (after dark)")
        elif surface: lines.append(f"Surface: {surface}")
        if safety: lines += ["", safety]
        lines += ["", "Book now:", "https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs",
                  "Can’t make it? Cancel at least 1 hour before:", "https://groups.runtogether.co.uk/My/BookedRuns",
                  "", f"{outro}"]
        return "\n".join(lines)

# ---- UI ----
st.write("## Upcoming Runs")

date_options = []
for idx, row in df.iterrows():
    date_val = row.get('Date')
    try:
        label = date_val.strftime('%A %d %B %Y') if pd.notnull(date_val) else ""
    except Exception:
        label = str(date_val) or ""
    date_options.append((label, idx))

if not date_options:
    st.warning("No runs found in the spreadsheet.")
    st.stop()

label_list = [d[0] for d in date_options]
selected_label = st.selectbox("Choose a date", options=label_list, index=0)
selected_idx = dict(date_options)[selected_label]
row = df.iloc[selected_idx]

location = row.get('Meeting location') or "Radcliffe Market"
surface  = (row.get('Surface') or "").strip()

col1, col2 = st.columns(2)
with col1:
    platform = st.selectbox("Platform", options=["Facebook", "Instagram", "Email"], index=0)
with col2:
    tone = st.selectbox("Tone", options=TONE_OPTIONS, index=0)

if "var_seed_offset" not in st.session_state:
    st.session_state["var_seed_offset"] = 0
if st.button("🔀 Shuffle wording"):
    st.session_state["var_seed_offset"] += 1
seed = f"{selected_label}|{platform}|{tone}|{location}|{surface}#{st.session_state['var_seed_offset']}"

preview = platform_message(platform, selected_label, location, surface, seed=seed, tone=tone)

st.subheader("Preview")
st.text_area("Generated message", value=preview, height=380)

st.download_button(
    label="Download message as .txt",
    data=preview,
    file_name=f"RTR_{selected_label.replace(' ','_')}_{platform}.txt",
    mime="text/plain",
)

st.write("\\n---\\n")
st.write("📲 Book now: https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs")
st.write("❌ Can’t make it? Cancel at least 1 hour before: https://groups.runtogether.co.uk/My/BookedRuns")
