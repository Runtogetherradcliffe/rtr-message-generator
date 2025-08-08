# RTR Message Generator – GPX Fallback Build

Upload GPX per route if Strava isn't returning data. LocationIQ will extract on‑route POIs from GPX coordinates.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
Push this folder to GitHub, set Secrets (STRAVA_CLIENT_ID/SECRET, LOCATIONIQ_API_KEY, ADMIN_PASS; add STRAVA_REFRESH_TOKEN after OAuth), and deploy.
