# PropSim — Player Prop & Moneyline Prediction App

A full-stack player-prop and game-outcome prediction system: a C++ Monte
Carlo simulation engine, a Python feature/backtest pipeline, a FastAPI
backend backed by SQLite, live odds/injuries from ESPN, and a React
dashboard — all wired together and deployable with Docker.

## Architecture

```
propsim/
├── cpp/                    # C++ Monte Carlo engine (pybind11 module)
│   ├── montecarlo.cpp
│   └── CMakeLists.txt
├── data/                   # Data layer
│   ├── db.py                    # SQLite schema + read/write helpers
│   ├── fetch_real_data.py       # Pulls player game logs + team ratings (nba_api)
│   ├── fetch_next_games.py      # Pulls each team's next scheduled game (nba_api)
│   └── propsim.db               # SQLite database (generated, not committed)
├── python/                 # Feature engineering
│   ├── features.py               # rolling averages, matchup adjustment, availability
│   └── tests/                    # pytest suite for features.py + the C++ engine
├── backtest/                # Standalone CLI backtest + prediction scripts
│   └── backtest.py
├── backend/                 # FastAPI REST API (wraps cpp/ + python/ + data/)
│   ├── main.py
│   ├── espn.py                   # live odds + injury reports (ESPN's public API)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React (Vite) dashboard
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml        # Runs backend + frontend together
```

**Data flow:** `data/` (real game logs, team ratings, schedule — SQLite)
→ `python/features.py` (rolling averages + matchup + availability
adjustments) → `cpp/montecarlo.cpp` (Monte Carlo simulation) →
`backend/main.py` (REST API, also calls ESPN for live odds/injuries) →
`frontend/` (dashboard).

## Features

- **Player props** across 6 stat categories (points, rebounds, assists,
  and the PRA/PA/RA combos), searchable across ~650 real players with a
  favorites watchlist, a last-12-games trend chart, and an availability
  signal (flags a declining minutes trend that might mean a role change
  or a return from injury).
- **Game moneyline/totals**, with real DraftKings lines auto-filled from
  ESPN when a market is posted (falls back to manual entry otherwise —
  player PROP odds specifically aren't available from any free source,
  so those stay manual).
- **Bet tracker**: log real bets against the model's prediction, settle
  them win/loss/push, and see your actual record and ROI over time.
- **Backtest**, multi-season (2023-24 through 2025-26) and per-stat, with
  hit rate, ROI, and calibration, plus a season-by-season breakdown to
  check whether an edge is consistent or one good year carrying the
  average.

## Running it — Docker

Requires Docker, Docker Compose, and internet access (to pull base
images from Docker Hub).

```bash
docker compose up --build
```

Then open:
- Frontend dashboard: http://localhost:5173
- Backend API docs (Swagger UI): http://localhost:8000/docs

The backend Dockerfile compiles the C++ engine from source and bundles
the committed `data/propsim.db` snapshot (three real NBA seasons + the
upcoming schedule) rather than pulling from nba_api at build time:
`stats.nba.com` is known to block requests from cloud/datacenter IP
ranges, which would make builds fail unpredictably on most hosts. To
refresh the snapshot, run the two scripts below from a normal network
connection and commit the updated `data/propsim.db`.

## Running it — without Docker

**Backend:**
```bash
pip install pybind11 fastapi "uvicorn[standard]" nba_api

cd cpp && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4

cd ../../data
python3 fetch_real_data.py        # ~1-2 min: 3 seasons, points/rebounds/assists/minutes
python3 fetch_next_games.py       # each team's next scheduled game

cd ../backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dashboard has four tabs:
- **Player Props** — search a player, pick a stat category, set a line
  and odds, see the model's simulated over/under probability, its edge
  against the market, a recent-form chart, and an availability flag.
- **Game Moneyline** — pick two teams; a real market line auto-fills if
  ESPN has one posted, or set the favorite and odds manually.
- **Bet Tracker** — log bets, settle them, track your real record/ROI.
- **Backtest Stats** — hit rate, ROI, and calibration, by stat category
  and by season, across ~70,000 historical player-games.

## Tests

```bash
python3 -m pytest python/tests/ -v
```

Covers the feature pipeline (rolling averages, the no-lookahead
guarantee, availability detection, matchup adjustment direction) and
the compiled C++ engine (probability sanity checks, odds conversion).

## API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/players` | GET | List players with enough history to predict |
| `/api/players/{name}` | GET | A player's current rolling stats + availability (`?stat=`) |
| `/api/players/{name}/history` | GET | Last N games of a stat, for a trend chart |
| `/api/teams` | GET | Team offensive/defensive ratings and pace |
| `/api/seasons` | GET | Seasons available for backtesting |
| `/api/injuries/{team}` | GET | Live ESPN injury report for a team |
| `/api/live-odds` | GET | Real moneyline/spread/total from ESPN, if posted |
| `/api/predict/prop` | POST | Predict a player prop over/under (`stat_category`) |
| `/api/predict/game` | POST | Predict a game's moneyline and total |
| `/api/backtest` | GET | Cached hit rate / ROI / calibration (`?stat=&season=`) |
| `/api/favorites` | GET/POST/DELETE | Player watchlist |
| `/api/bets` | GET/POST/PATCH/DELETE | Logged-bet tracker with ROI |
| `/api/health` | GET | Health check |

Full interactive docs at `/docs` once the backend is running (FastAPI's
built-in Swagger UI).

## The Monte Carlo engine

Rather than deriving probabilities with a closed-form formula, the
engine draws tens of thousands of random samples from a player's fitted
scoring distribution (mean/std adjusted for opponent defense, pace,
home/away, and rest) and counts how often the simulated total clears
the prop line. The same approach simulates full games by drawing each
team's score independently and comparing them. Benchmarked at **~30
million simulations/second** on a single core (see `cpp/montecarlo.cpp`).

## Data

`data/fetch_real_data.py` pulls real player game logs (points, rebounds,
assists, minutes) and team advanced stats for three seasons from
`nba_api`, and `data/fetch_next_games.py` pulls each team's next real
scheduled game — both write into `data/propsim.db` (SQLite). Live
moneyline/spread/total odds and injury reports come from ESPN's public
site API at request time (`backend/espn.py`), cached for 15 minutes;
no API key required for any of this. Genuine player PROP odds aren't
available from any free source — every provider charges for that
specific data — so those stay manual entry in the UI.

## Backtest results (3 real seasons, 2023-24 through 2025-26)

- **~51.6% hit rate** across ~70,000 graded player-game point
  predictions, with lines set at each player's own pre-game rolling
  average — consistent within about a point across all three
  independent seasons (51.2% / 52.1% / 51.5%), so the edge is real but
  thin, not one good season carrying the average.
- Calibration trends the right way: 50-60% confidence bucket → ~51%
  actual, 90-100% confidence bucket → ~56% actual.
- Flat-bet ROI at -110 is slightly negative (~-1.4%) — an honest result:
  the matchup adjustment beats a naive "expect their average" line, but
  not by enough to clear the standard sportsbook vig.

## Resume bullet

> Built a full-stack sports betting analytics platform: a C++ Monte
> Carlo simulation engine (~30M simulations/sec) across 6 stat
> categories, a Python matchup/availability feature pipeline over 3
> seasons of real NBA data, a FastAPI + SQLite backend integrating live
> odds and injury data, a bet-tracking ledger with real ROI, and a React
> dashboard — backtested at ~51.6% hit rate across ~70,000 historical
> player-games, consistent across three independent seasons.
