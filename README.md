# Fantasy Agent

A Claude-powered assistant for two ESPN fantasy football leagues: draft prep,
season-long roster management, injury/waiver monitoring, and trade evaluation.

## Status
🚧 Step 1 of the build: connection layer only. This proves we can pull data
from both leagues before we build any intelligence on top of it.

## Setup (run this locally on your Mac)

1. Install Python 3.10+ if you don't have it: `python3 --version` to check.
2. From this folder, install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy the env template and fill in your real values:
   ```
   cp .env.example .env
   ```
   Then open `.env` in a text editor and paste in your actual `ESPN_SWID`
   and `ESPN_S2` values (the ones you pulled from your browser cookies).
   League IDs are already filled in for you.
4. Run the connection test:
   ```
   python3 test_connection.py
   ```
   If it works, you'll see both league names, scoring types, and team
   rosters printed out. If it fails, the error message will usually tell
   you whether it's a bad cookie value or a wrong league ID.

## Draft Dashboard

A live dashboard to have open in your browser during the actual draft,
alongside ESPN's draft room.

1. Get a Claude API key from console.anthropic.com (Anthropic's developer
   console — separate from a claude.ai login) and paste it into `.env`
   as `ANTHROPIC_API_KEY`.
2. Run: `python3 -m pip install -r requirements.txt` (picks up Streamlit)
3. Run: `streamlit run draft_dashboard.py`
4. Your browser will open automatically to the dashboard. Pick which
   league you're drafting from the sidebar dropdown.
5. It auto-detects which team is yours by matching your SWID.
6. Click "🔄 Refresh draft data" in the sidebar after each pick (yours
   or anyone else's) to pull the latest state.
7. Use the "Ask for advice" box any time you want a recommendation —
   it factors in your current roster and who's still available.

## Season-Long Monitoring (in progress)

`monitor.py` checks your current-week matchup in both leagues for starter
injuries — yours and your opponent's — and drafts a waiver suggestion when
there's a clearly better replacement (bench swap or free-agent pickup).

**Not yet wired up:** Twilio texting (needs your Twilio credentials in
`.env` first) and trade evaluation (needs more work — pending offers use
a different ESPN endpoint than what we've built so far).

**To test the logic without texting yourself:** open `monitor.py` and
temporarily comment out the `send_text(message)` line — it'll print
what it *would* have sent instead. Run with:
```
python3 monitor.py
```

## What's next
- ~~Draft-day assistant for League 2~~ ✅ built and tested
- Trade evaluation (pending offers + proactive suggestions)
- Twilio setup so alerts actually text you
- GitHub Actions so this runs automatically a few times a day

## Project structure
```
fantasy-agent/
├── src/
│   ├── config.py       # loads league IDs & credentials from .env
│   └── connectors.py   # wraps espn_api to connect to each league
├── test_connection.py  # run this first to verify everything works
├── requirements.txt
├── .env.example         # template — copy to .env, never commit .env
└── .gitignore           # makes sure .env never gets committed
```
