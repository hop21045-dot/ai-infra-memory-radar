# AI Infra Memory Radar

Streamlit dashboard for memory semiconductor investors tracking public AI infrastructure indicators.

## What It Tracks

- Hyperscaler capex: MSFT, GOOGL, META, AMZN, ORCL
- AI server OEMs: DELL, HPE
- AI silicon/networking: AVGO, NVDA
- Memory read-through: MU plus capex/revenue/inventory signals
- Latest SEC filings from EDGAR submissions
- Optional manually structured AI backlog/order commentary in `manual_indicators.csv`

## Live Data Behavior

The app uses the SEC EDGAR JSON APIs:

- `data.sec.gov/submissions/CIK##########.json`
- `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

Streamlit caches metric data for 15 minutes and filing data for 5 minutes. Press **Refresh now** in the sidebar to clear the cache.

If SEC access fails because of network/rate limits, the app falls back to bundled seed data so the UI still works.

Backlog/order commentary is not always standardized in XBRL. Put company-disclosed AI server orders, backlog, RPO commentary, or earnings-call notes in `manual_indicators.csv` with source links.

## Run Locally

Recommended on Windows:

```powershell
.\run_local.cmd
```

Then open:

```text
http://127.0.0.1:8501
```

Keep the terminal window open while using the dashboard. Closing the terminal stops the local web server.

Alternative:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Push these files to GitHub and deploy the repo from Streamlit Community Cloud. No API key is required for the SEC data source.

## Limits

This is a public-data dashboard, not an internal order book. Some AI backlog items are not XBRL-tagged and must come from company commentary, IR decks, earnings-call transcripts, or manually maintained structured notes.
