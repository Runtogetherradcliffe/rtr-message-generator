import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import random
from bs4 import BeautifulSoup

# --- Load spreadsheet (latest version) ---
data_path = os.path.join("data", "RTR route schedule.xlsx")
try:
    df = pd.read_excel(data_path)
except Exception as e:
    st.error(f"Could not load spreadsheet at {data_path}: {e}")
    st.stop()

# --- Tabs ---
tab1, tab2 = st.tabs(["Thursday Run Messages", "Parkrun Shout-outs"])

# ======================================================
# TAB 1 – THURSDAY RUN MESSAGES (kept as your current behaviour)
# ======================================================
with tab1:
    st.title("RTR Message Generator")
    st.write("## Upcoming Runs")

    for idx, row in df.iterrows():
        date_val = row.get('Date')
        try:
            date_str = date_val.strftime('%A %d %B %Y') if pd.notnull(date_val) else ""
        except AttributeError:
            date_str = str(date_val) or ""
        location = row.get('Meeting location') or "Radcliffe Market"
        surface = row.get('Surface') or ""

        st.subheader(date_str)
        st.write(f"**Meeting at:** {location}")
        if "after dark" in str(surface).lower():
            st.warning("If you’re able to join us, please ensure you have your lights with you and wear hi-vis clothing")

    st.write("\n---\n")
    st.write("📲 Book now: https://groups.runtogether.co.uk/RunTogetherRadcliffe/Runs")
    st.write("❌ Can’t make it? Cancel at least 1 hour before: https://groups.runtogether.co.uk/My/BookedRuns")

# ======================================================
# TAB 2 – PARKRUN SHOUT-OUTS
# ======================================================
with tab2:
    st.header("Parkrun Shout-outs")

    # Default to last Saturday
    today = datetime.today()
    days_since_sat = (today.weekday() - 5) % 7
    last_sat = today - timedelta(days=days_since_sat)
    date_choice = st.date_input("Select parkrun date", value=last_sat, key="pr_date")

    check_course_pbs = st.checkbox("Check course PBs", value=False, key="pr_course_pb")

    platform = st.selectbox("Platform", ["WhatsApp", "Facebook", "Instagram", "Email"], key="pr_platform")
    if "shuffle_seed" not in st.session_state:
        st.session_state.shuffle_seed = random.randint(0, 1_000_000)
    if st.button("Shuffle wording", key="pr_shuffle"):
        st.session_state.shuffle_seed = random.randint(0, 1_000_000)

    if st.button("Fetch shout-outs", key="pr_fetch"):
        try:
            results = fetch_parkrun_data(date_choice, check_course_pbs)
            if results:
                message = generate_parkrun_message(results, platform, st.session_state.get("shuffle_seed"))
                st.text_area("Preview message", message, height=420, key="pr_preview")
            else:
                st.info("No results found for that date.")
        except Exception as e:
            st.error(f"Error fetching parkrun data: {e}")


# ======================================================
# FUNCTIONS
# ======================================================
def fetch_parkrun_data(date_choice, check_course_pbs=False):
    """Fetch Run Together Radcliffe consolidated club report (clubNum=49581) for a given date.

    Note: Uses the public consolidated report page and parses the HTML table.

    """
    url = f"https://www.parkrun.com/results/consolidatedclub/?clubNum=49581&eventDate={date_choice.strftime('%Y-%m-%d')}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    table = soup.find("table", class_="Results")
    if not table:
        return []

    results = []
    rows = table.find_all("tr")[1:]  # skip header
    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 7:
            continue

        def cell_text(i):
            try:
                return cols[i].get_text(strip=True)
            except Exception:
                return ""

        name = cell_text(0)
        event = cell_text(1)
        time = cell_text(3)
        note = cell_text(6)

        if not name or not event:
            continue

        achievements = []
        # parkrun PB is typically flagged in the notes column
        if "PB" in note:
            achievements.append("parkrun PB")
        # First timer at the event is also flagged in the notes
        if "First timer" in note:
            achievements.append("First time at this event")

        # Optional: course PB deep check (placeholder)
        if check_course_pbs:
            # Implement additional fetch per runner/event if later required
            pass

        results.append({
            "name": name,
            "event": event,
            "time": time or "—",
            "achievements": achievements
        })

    return results


def generate_parkrun_message(results, platform, seed=None):
    random.seed(seed or 0)
    intros = {
        "Facebook": [
            "🌟 Huge congrats to our parkrunners this week!",
            "👏 Another Saturday, another set of cracking runs!"
        ],
        "Instagram": [
            "💥 Saturday vibes from the RTR crew!",
            "🏃‍♀️ Weekend miles, big smiles!"
        ],
        "WhatsApp": [
            "*Shout‑out time!* 🏆 Here’s what our parkrunners got up to:",
            "*Saturday success stories* 👏"
        ],
        "Email": [
            "Here are this week's parkrun highlights:",
            "Celebrating our runners' parkrun achievements this week:"
        ]
    }
    outro_by_platform = {
        "Facebook": "\n\nGot a photo? Drop it below! 📸",
        "Instagram": "\n\nTag us and share your snaps 📸 #RunTogetherRadcliffe",
        "WhatsApp": "\n\nGot pics? Share them in the chat!",        "Email": "\n\nSee you next Saturday,"
    }

    intro = random.choice(intros.get(platform, intros["Facebook"]))

    lines = [intro, ""]
    for r in results:
        ach = ", ".join(r["achievements"]) if r["achievements"] else "completed the course"
        lines.append(f"- {r['name']} at {r['event']} in {r['time']} ({ach})")

    lines.append(outro_by_platform.get(platform, ""))
    return "\n".join(lines)
