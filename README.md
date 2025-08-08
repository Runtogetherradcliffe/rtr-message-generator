# RTR Message Generator (query_params build)

This build updates the Admin OAuth flow to use `st.query_params`.
Includes Strava distance/elevation, LocationIQ POIs, and varied copy.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
## Deploy
Push to Streamlit Cloud, set Secrets, then do the Strava OAuth once on the Admin page.
