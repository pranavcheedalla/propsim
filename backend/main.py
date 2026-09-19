"""
FastAPI backend for PropSim.

Wraps the C++ Monte Carlo engine (cpp/), the Python feature pipeline
(python/), and the SQLite store (data/db.py) behind a REST API.

Endpoints:
    GET    /api/players                        players with enough history to predict
    GET    /api/players/{player_name}          a player's current rolling stats + availability
    GET    /api/players/{player_name}/history  last N games of a stat, for a trend chart
    GET    /api/teams                          team ratings
    GET    /api/seasons                        seasons available for backtesting
    GET    /api/injuries/{team_name}           current ESPN injury report for a team
    GET    /api/live-odds                      real moneyline/spread/total from ESPN, if posted
    POST   /api/predict/prop                    predict a player prop over/under
    POST   /api/predict/game                    predict a game moneyline/total
    GET    /api/backtest                        cached backtest summary (hit rate, ROI, calibration)
    GET    /api/favorites, POST, DELETE          a personal watchlist
    GET    /api/bets, POST, PATCH, DELETE        a logged-bet tracker with ROI
    GET    /api/health                          health check
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "cpp", "build"))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "python"))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "backtest"))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "data"))

import montecarlo
import features
import db
import espn
from backtest import run_backtest

app = FastAPI(title="PropSim API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

_cached_features = {}
_cached_upcoming_features = {}
_cached_team_stats = None
_cached_backtest = {}


def get_features(stat_category="points"):
    if stat_category not in _cached_features:
        _cached_features[stat_category] = features.build_all_features(stat_category=stat_category)
    return _cached_features[stat_category]


def get_upcoming_features(stat_category="points"):
    if stat_category not in _cached_upcoming_features:
        _cached_upcoming_features[stat_category] = features.build_all_upcoming_features(stat_category=stat_category)
    return _cached_upcoming_features[stat_category]


def get_team_stats():
    global _cached_team_stats
    if _cached_team_stats is None:
        _cached_team_stats = features.load_team_stats()
    return _cached_team_stats


def most_recent_feature_row(player_name: str, stat_category: str):
    matching_rows = [row for row in get_features(stat_category) if row["player_name"] == player_name]
    if len(matching_rows) == 0:
        return None
    matching_rows.sort(key=lambda row: row["game_number"])
    return matching_rows[-1]


def feature_row_for_prediction(player_name: str, stat_category: str):
    """
    Prefers the player's next real scheduled game over their last
    historical game, so "vs {opponent}" reflects an actual upcoming
    matchup. Falls back to the historical row if there's no schedule
    data for their team.
    """
    upcoming_row = get_upcoming_features(stat_category).get(player_name)
    if upcoming_row is not None:
        return upcoming_row
    return most_recent_feature_row(player_name, stat_category)


class PropPredictionRequest(BaseModel):
    player_name: str
    line: float
    stat_category: str = "points"
    num_simulations: int = 100000
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None


class GamePredictionRequest(BaseModel):
    team_a: str
    team_b: str
    total_line: float
    num_simulations: int = 100000
    team_a_moneyline_odds: Optional[int] = None
    team_b_moneyline_odds: Optional[int] = None


class FavoriteRequest(BaseModel):
    player_name: str


class BetRequest(BaseModel):
    bet_type: str  # "prop" | "moneyline" | "total"
    player_name: Optional[str] = None
    team_a: Optional[str] = None
    team_b: Optional[str] = None
    stat_category: Optional[str] = None
    selection: str  # "over" | "under" | a team name
    line: Optional[float] = None
    odds: int
    stake: float = 1.0
    model_probability: Optional[float] = None
    notes: Optional[str] = None


class BetSettleRequest(BaseModel):
    status: str  # "won" | "lost" | "push"
    actual_value: Optional[float] = None


@app.get("/api/players")
def list_players():
    players_seen = {}
    for row in get_features("points"):
        players_seen[row["player_name"]] = row["team"]
    players = [{"player_name": name, "team": team} for name, team in sorted(players_seen.items())]
    return {"players": players, "count": len(players)}


@app.get("/api/players/{player_name}")
def get_player(player_name: str, stat: str = "points"):
    if stat not in features.STAT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown stat category '{stat}'")
    feature_row = feature_row_for_prediction(player_name, stat)
    if feature_row is None:
        raise HTTPException(status_code=404, detail=f"No data for player '{player_name}'")
    return feature_row


@app.get("/api/players/{player_name}/history")
def get_player_history(player_name: str, stat: str = "points", games: int = 15):
    if stat not in features.STAT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown stat category '{stat}'")
    history = features.player_game_history(player_name, stat, num_games=games)
    if not history:
        raise HTTPException(status_code=404, detail=f"No game history for player '{player_name}'")
    return {"player_name": player_name, "stat_category": stat, "games": history}


@app.get("/api/teams")
def list_teams():
    team_stats = get_team_stats()
    teams = [{"team": team, **ratings} for team, ratings in sorted(team_stats.items())]
    return {"teams": teams, "count": len(teams)}


@app.get("/api/seasons")
def list_seasons():
    return {"seasons": features.list_available_seasons()}


@app.get("/api/injuries/{team_name}")
def get_injuries(team_name: str):
    return {"team": team_name, "injuries": espn.get_team_injuries(team_name)}


@app.get("/api/live-odds")
def get_live_odds(team_a: str, team_b: str, game_date: Optional[str] = None):
    odds = espn.get_live_game_odds(team_a, team_b, game_date)
    if odds is None:
        return {"available": False}
    return {"available": True, **odds}


@app.post("/api/predict/prop")
def predict_prop(request: PropPredictionRequest):
    if request.stat_category not in features.STAT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown stat category '{request.stat_category}'")

    feature_row = feature_row_for_prediction(request.player_name, request.stat_category)
    if feature_row is None:
        raise HTTPException(status_code=404, detail=f"No data for player '{request.player_name}'")

    simulation_result = montecarlo.simulate_player_prop(
        mean=feature_row["adjusted_mean"],
        standard_deviation=feature_row["adjusted_standard_deviation"],
        line=request.line,
        num_simulations=request.num_simulations,
    )

    response = {
        "player_name": request.player_name,
        "team": feature_row["team"],
        "opponent_team": feature_row["opponent_team"],
        "stat_category": request.stat_category,
        "rolling_average": feature_row["rolling_mean_before_adjustment"],
        "matchup_adjusted_mean": feature_row["adjusted_mean"],
        "matchup_adjusted_standard_deviation": feature_row["adjusted_standard_deviation"],
        "line": request.line,
        "probability_over": simulation_result["probability_over"],
        "probability_under": simulation_result["probability_under"],
        "num_simulations": simulation_result["num_simulations"],
        "availability": feature_row.get("availability"),
    }
    if "game_date" in feature_row:
        response["game_date"] = feature_row["game_date"]

    if request.over_odds is not None:
        market_probability_over = montecarlo.implied_probability_from_american_odds(request.over_odds)
        response["over_odds"] = request.over_odds
        response["market_implied_probability_over"] = market_probability_over
        response["edge_over"] = simulation_result["probability_over"] - market_probability_over

    if request.under_odds is not None:
        market_probability_under = montecarlo.implied_probability_from_american_odds(request.under_odds)
        response["under_odds"] = request.under_odds
        response["market_implied_probability_under"] = market_probability_under
        response["edge_under"] = simulation_result["probability_under"] - market_probability_under

    return response


@app.post("/api/predict/game")
def predict_game(request: GamePredictionRequest):
    team_stats = get_team_stats()
    if request.team_a not in team_stats:
        raise HTTPException(status_code=404, detail=f"Unknown team '{request.team_a}'")
    if request.team_b not in team_stats:
        raise HTTPException(status_code=404, detail=f"Unknown team '{request.team_b}'")

    team_a_stats = team_stats[request.team_a]
    team_b_stats = team_stats[request.team_b]

    team_a_mean = team_a_stats["offensive_rating"] - (team_b_stats["defensive_rating"] - 114.0) * 0.3
    team_b_mean = team_b_stats["offensive_rating"] - (team_a_stats["defensive_rating"] - 114.0) * 0.3
    team_a_standard_deviation = 10.0
    team_b_standard_deviation = 10.0

    simulation_result = montecarlo.simulate_game(
        team_a_mean=team_a_mean,
        team_a_standard_deviation=team_a_standard_deviation,
        team_b_mean=team_b_mean,
        team_b_standard_deviation=team_b_standard_deviation,
        total_line=request.total_line,
        num_simulations=request.num_simulations,
    )

    response = {
        "team_a": request.team_a,
        "team_b": request.team_b,
        "team_a_projected_score": round(team_a_mean, 1),
        "team_b_projected_score": round(team_b_mean, 1),
        "total_line": request.total_line,
        "probability_team_a_wins": simulation_result["probability_team_a_wins"],
        "probability_team_b_wins": simulation_result["probability_team_b_wins"],
        "probability_over_total": simulation_result["probability_over_total"],
        "probability_under_total": simulation_result["probability_under_total"],
        "num_simulations": simulation_result["num_simulations"],
    }

    if request.team_a_moneyline_odds is not None:
        market_probability = montecarlo.implied_probability_from_american_odds(request.team_a_moneyline_odds)
        response["team_a_moneyline_odds"] = request.team_a_moneyline_odds
        response["market_implied_probability_team_a"] = market_probability
        response["edge_team_a"] = simulation_result["probability_team_a_wins"] - market_probability

    if request.team_b_moneyline_odds is not None:
        market_probability = montecarlo.implied_probability_from_american_odds(request.team_b_moneyline_odds)
        response["team_b_moneyline_odds"] = request.team_b_moneyline_odds
        response["market_implied_probability_team_b"] = market_probability
        response["edge_team_b"] = simulation_result["probability_team_b_wins"] - market_probability

    return response


@app.get("/api/backtest")
def get_backtest_summary(stat: str = "points", season: str = "all"):
    if stat not in features.STAT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown stat category '{stat}'")
    cache_key = (stat, season)
    if cache_key not in _cached_backtest:
        _cached_backtest[cache_key] = run_backtest(stat_category=stat, season=None if season == "all" else season)
    return _cached_backtest[cache_key]


@app.get("/api/favorites")
def list_favorites():
    connection = db.get_connection()
    rows = connection.execute("SELECT player_name FROM favorites ORDER BY added_at DESC").fetchall()
    connection.close()
    return {"favorites": [row["player_name"] for row in rows]}


@app.post("/api/favorites")
def add_favorite(request: FavoriteRequest):
    connection = db.get_connection()
    connection.execute(
        "INSERT OR IGNORE INTO favorites (player_name, added_at) VALUES (?, ?)",
        (request.player_name, datetime.now(timezone.utc).isoformat()),
    )
    connection.commit()
    connection.close()
    return {"status": "ok"}


@app.delete("/api/favorites/{player_name}")
def remove_favorite(player_name: str):
    connection = db.get_connection()
    connection.execute("DELETE FROM favorites WHERE player_name = ?", (player_name,))
    connection.commit()
    connection.close()
    return {"status": "ok"}


def _bet_payout_multiplier(odds: int) -> float:
    return (odds / 100.0) if odds > 0 else (100.0 / abs(odds))


def _row_to_bet(row) -> dict:
    bet = dict(row)
    bet["potential_profit"] = round(bet["stake"] * _bet_payout_multiplier(bet["odds"]), 2)
    if bet["status"] == "won":
        bet["profit"] = bet["potential_profit"]
    elif bet["status"] == "lost":
        bet["profit"] = -bet["stake"]
    else:
        bet["profit"] = 0.0
    return bet


@app.get("/api/bets")
def list_bets():
    connection = db.get_connection()
    rows = connection.execute("SELECT * FROM bets ORDER BY created_at DESC").fetchall()
    connection.close()
    bets = [_row_to_bet(row) for row in rows]

    settled = [bet for bet in bets if bet["status"] != "pending"]
    wins = sum(1 for bet in settled if bet["status"] == "won")
    losses = sum(1 for bet in settled if bet["status"] == "lost")
    pushes = sum(1 for bet in settled if bet["status"] == "push")
    total_staked = sum(bet["stake"] for bet in settled if bet["status"] != "push")
    total_profit = sum(bet["profit"] for bet in settled)
    roi_percent = (total_profit / total_staked * 100.0) if total_staked > 0 else 0.0

    return {
        "bets": bets,
        "summary": {
            "pending": sum(1 for bet in bets if bet["status"] == "pending"),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "record": f"{wins}-{losses}" + (f"-{pushes}" if pushes else ""),
            "total_profit_units": round(total_profit, 2),
            "roi_percent": round(roi_percent, 1),
        },
    }


@app.post("/api/bets")
def create_bet(request: BetRequest):
    connection = db.get_connection()
    cursor = connection.execute(
        """
        INSERT INTO bets
            (created_at, bet_type, player_name, team_a, team_b, stat_category, selection, line, odds, stake, model_probability, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            datetime.now(timezone.utc).isoformat(), request.bet_type, request.player_name, request.team_a,
            request.team_b, request.stat_category, request.selection, request.line, request.odds,
            request.stake, request.model_probability,
        ),
    )
    connection.commit()
    bet_id = cursor.lastrowid
    row = connection.execute("SELECT * FROM bets WHERE id = ?", (bet_id,)).fetchone()
    connection.close()
    return _row_to_bet(row)


@app.patch("/api/bets/{bet_id}")
def settle_bet(bet_id: int, request: BetSettleRequest):
    if request.status not in ("won", "lost", "push"):
        raise HTTPException(status_code=400, detail="status must be 'won', 'lost', or 'push'")
    connection = db.get_connection()
    existing = connection.execute("SELECT id FROM bets WHERE id = ?", (bet_id,)).fetchone()
    if existing is None:
        connection.close()
        raise HTTPException(status_code=404, detail=f"No bet with id {bet_id}")
    connection.execute(
        "UPDATE bets SET status = ?, actual_value = ?, settled_at = ? WHERE id = ?",
        (request.status, request.actual_value, datetime.now(timezone.utc).isoformat(), bet_id),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM bets WHERE id = ?", (bet_id,)).fetchone()
    connection.close()
    return _row_to_bet(row)


@app.delete("/api/bets/{bet_id}")
def delete_bet(bet_id: int):
    connection = db.get_connection()
    connection.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
    connection.commit()
    connection.close()
    return {"status": "ok"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
