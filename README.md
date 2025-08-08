# RunTogether Radcliffe – Weekly Message Generator

Generates varied, friendly messages for the weekly running group, pulling distance/elevation from Strava and on‑route place names from LocationIQ.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud deploy (free)
1. Push this folder to GitHub.
2. Create a new app on Streamlit Community Cloud.
3. Add **Secrets**:
```toml
STRAVA_CLIENT_ID = "…"
STRAVA_CLIENT_SECRET = "…"
LOCATIONIQ_API_KEY = "…"
ADMIN_PASS = "choose-a-password"
# STRAVA_REFRESH_TOKEN = "…"  # add after doing OAuth in the Admin page
```
4. Set your Strava **callback URL** to your Streamlit app root (e.g. `https://your-app.streamlit.app`).
5. In the app → **Admin** → do the OAuth, copy the refresh token into Secrets as `STRAVA_REFRESH_TOKEN`, then rerun.

## File layout
```
.
├── app.py
├── requirements.txt
├── README.md
└── data/
    └── RTR route schedule.xlsx
```
