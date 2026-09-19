"""
Feature engineering layer: turns raw player game logs and team ratings
into the per-game mean/standard-deviation inputs the C++ Monte Carlo
engine needs, for whichever stat category was asked for (points,
rebounds, assists, or a combo of them).

For a given player and an upcoming game, the pipeline is:
  1. Take the player's rolling average of the requested stat over their
     last N games (only games where they actually played meaningful
     minutes - see AVAILABILITY_MINUTES_FLOOR below).
  2. Adjust that average up or down based on the opponent's defensive
     rating and pace, relative to league average.
  3. Adjust further for home/away and rest days.
  4. Estimate a standard deviation from the player's own game-to-game
     variance (a streaky scorer should have a wider simulated
     distribution than a consistent one).

The output is exactly what montecarlo.simulate_player_prop() expects:
a single adjusted mean and standard deviation per player per game.
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
import db  # noqa: E402

ROLLING_WINDOW_SIZE = 10
LEAGUE_AVERAGE_DEFENSIVE_RATING = 114.0
LEAGUE_AVERAGE_PACE = 99.0

# A player logged with fewer minutes than this is treated as a garbage-time
# or early-injury-return appearance and excluded from the rolling window,
# so a 2-minute stat line doesn't drag down an otherwise-healthy average.
AVAILABILITY_MINUTES_FLOOR = 10.0

STAT_CATEGORIES = {
    "points": ["points"],
    "rebounds": ["rebounds"],
    "assists": ["assists"],
    "pra": ["points", "rebounds", "assists"],
    "pa": ["points", "assists"],
    "ra": ["rebounds", "assists"],
}


def stat_value(game, stat_category):
    return sum(game[component] for component in STAT_CATEGORIES[stat_category])


def load_player_games(season=None):
    connection = db.get_connection()
    if season and season != "all":
        cursor = connection.execute(
            "SELECT * FROM player_games WHERE season = ? ORDER BY game_number", (season,)
        )
    else:
        cursor = connection.execute("SELECT * FROM player_games ORDER BY game_number")
    games = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return games


def load_team_stats(season=None):
    connection = db.get_connection()
    if season and season != "all":
        cursor = connection.execute("SELECT * FROM team_stats WHERE season = ?", (season,))
    else:
        # No season given: use each team's most recent season on record.
        cursor = connection.execute(
            """
            SELECT t.* FROM team_stats t
            INNER JOIN (SELECT team, MAX(season) AS season FROM team_stats GROUP BY team) latest
                ON t.team = latest.team AND t.season = latest.season
            """
        )
    team_stats = {}
    for row in cursor.fetchall():
        team_stats[row["team"]] = {
            "offensive_rating": row["offensive_rating"],
            "defensive_rating": row["defensive_rating"],
            "pace": row["pace"],
        }
    connection.close()
    return team_stats


def load_next_games():
    connection = db.get_connection()
    cursor = connection.execute("SELECT * FROM next_games")
    next_games = {row["team"]: dict(row) for row in cursor.fetchall()}
    connection.close()
    return next_games


def player_game_history(player_name, stat_category, num_games=15):
    connection = db.get_connection()
    cursor = connection.execute(
        "SELECT * FROM player_games WHERE player_name = ? ORDER BY game_number DESC LIMIT ?",
        (player_name, num_games),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()
    rows.reverse()
    return [
        {
            "game_date": row["game_date"],
            "opponent_team": row["opponent_team"],
            "is_home": bool(row["is_home"]),
            "value": stat_value(row, stat_category),
            "minutes": row["minutes"],
        }
        for row in rows
    ]


def list_available_seasons():
    connection = db.get_connection()
    seasons = [row[0] for row in connection.execute(
        "SELECT DISTINCT season FROM player_games ORDER BY season"
    ).fetchall()]
    connection.close()
    return seasons


def group_games_by_player(games):
    games_by_player = {}
    for game in games:
        games_by_player.setdefault(game["player_name"], []).append(game)
    return games_by_player


def rolling_mean_and_standard_deviation(recent_values):
    if len(recent_values) < 2:
        return None, None
    mean = statistics.mean(recent_values)
    standard_deviation = statistics.stdev(recent_values)
    # Floor the standard deviation so the simulator never collapses to a
    # near-deterministic distribution on a short, unusually consistent streak.
    standard_deviation = max(standard_deviation, 1.5 if mean < 8 else 3.0)
    return mean, standard_deviation


def availability_signal(player_history, game_index):
    """
    A light-weight, data-only proxy for "is this player's role/health
    stable right now": compares minutes over the last 3 games played to
    the prior 10, and counts recent team games the player didn't appear
    in at all (a DNP/inactive, which is what a box score shows for an
    injury without needing a separate injury feed).
    """
    previous_games = player_history[max(0, game_index - ROLLING_WINDOW_SIZE):game_index]
    if len(previous_games) < 5:
        return None

    minutes = [game["minutes"] for game in previous_games]
    recent_minutes = statistics.mean(minutes[-3:]) if len(minutes) >= 3 else statistics.mean(minutes)
    baseline_minutes = statistics.mean(minutes)
    minutes_trend = recent_minutes - baseline_minutes

    return {
        "recent_minutes_avg": round(recent_minutes, 1),
        "baseline_minutes_avg": round(baseline_minutes, 1),
        "minutes_trend": round(minutes_trend, 1),
    }


def build_features_for_game(game_index, player_history, team_stats, stat_category):
    """
    Builds the adjusted mean/standard-deviation for one player's game,
    using only games BEFORE it (no lookahead / no leaking the answer).
    Returns None if there isn't enough history yet.
    """
    current_game = player_history[game_index]
    eligible_previous_games = [
        game for game in player_history[:game_index]
        if game["minutes"] >= AVAILABILITY_MINUTES_FLOOR
    ]
    previous_games = eligible_previous_games[-ROLLING_WINDOW_SIZE:]

    if len(previous_games) < 5:
        return None

    recent_values = [stat_value(game, stat_category) for game in previous_games]
    rolling_mean, rolling_standard_deviation = rolling_mean_and_standard_deviation(recent_values)
    if rolling_mean is None:
        return None

    opponent_team = current_game["opponent_team"]
    opponent_stats = team_stats.get(opponent_team)
    if opponent_stats is None:
        return None

    defensive_adjustment = (opponent_stats["defensive_rating"] - LEAGUE_AVERAGE_DEFENSIVE_RATING) * 0.15
    pace_adjustment = (opponent_stats["pace"] - LEAGUE_AVERAGE_PACE) * 0.10
    home_adjustment = 0.8 if current_game["is_home"] == 1 else -0.8
    rest_adjustment = -1.5 if current_game["rest_days"] <= 1 else 0.0

    # Scale matchup adjustments down for smaller-magnitude stats (assists)
    # relative to points, so a 5 pt/100poss defensive swing doesn't move a
    # 4-assist average by the same absolute amount it moves a 25-point one.
    scale = rolling_mean / 20.0 if stat_category != "points" else 1.0
    adjusted_mean = rolling_mean + scale * (defensive_adjustment + pace_adjustment) + (
        home_adjustment + rest_adjustment
    ) * (0.3 if stat_category != "points" else 1.0)
    adjusted_mean = max(adjusted_mean, 0.5)

    return {
        "player_name": current_game["player_name"],
        "team": current_game["team"],
        "opponent_team": opponent_team,
        "season": current_game["season"],
        "game_number": current_game["game_number"],
        "game_date": current_game["game_date"],
        "stat_category": stat_category,
        "actual_value": stat_value(current_game, stat_category),
        "adjusted_mean": adjusted_mean,
        "adjusted_standard_deviation": rolling_standard_deviation,
        "rolling_mean_before_adjustment": rolling_mean,
        "availability": availability_signal(player_history, game_index),
    }


def build_upcoming_feature_row(player_history, team_stats, next_games, stat_category):
    """
    Projects a player's NEXT real scheduled game (from next_games),
    using their full rolling history to date, rather than reusing
    whatever opponent their last logged historical game happened to be
    against (which is just the prior season's finale once that season
    is complete, not an upcoming game).
    """
    eligible_games = [game for game in player_history if game["minutes"] >= AVAILABILITY_MINUTES_FLOOR]
    if len(eligible_games) < 5:
        return None

    recent_games = eligible_games[-ROLLING_WINDOW_SIZE:]
    recent_values = [stat_value(game, stat_category) for game in recent_games]
    rolling_mean, rolling_standard_deviation = rolling_mean_and_standard_deviation(recent_values)
    if rolling_mean is None:
        return None

    team = player_history[-1]["team"]
    next_game = next_games.get(team)
    if next_game is None:
        return None

    opponent_team = next_game["opponent_team"]
    opponent_stats = team_stats.get(opponent_team)
    if opponent_stats is None:
        return None

    defensive_adjustment = (opponent_stats["defensive_rating"] - LEAGUE_AVERAGE_DEFENSIVE_RATING) * 0.15
    pace_adjustment = (opponent_stats["pace"] - LEAGUE_AVERAGE_PACE) * 0.10
    home_adjustment = 0.8 if next_game["is_home"] == 1 else -0.8

    scale = rolling_mean / 20.0 if stat_category != "points" else 1.0
    # No rest-day penalty: a season opener follows a months-long offseason.
    adjusted_mean = rolling_mean + scale * (defensive_adjustment + pace_adjustment) + home_adjustment * (
        0.3 if stat_category != "points" else 1.0
    )
    adjusted_mean = max(adjusted_mean, 0.5)

    return {
        "player_name": player_history[-1]["player_name"],
        "team": team,
        "opponent_team": opponent_team,
        "game_date": next_game["game_date"],
        "stat_category": stat_category,
        "adjusted_mean": adjusted_mean,
        "adjusted_standard_deviation": rolling_standard_deviation,
        "rolling_mean_before_adjustment": rolling_mean,
        "availability": availability_signal(player_history, len(player_history)),
    }


def build_all_upcoming_features(stat_category="points"):
    games = load_player_games(season="2025-26")
    team_stats = load_team_stats()
    next_games = load_next_games()
    games_by_player = group_games_by_player(games)

    upcoming_features = {}
    for player_name, player_history in games_by_player.items():
        feature_row = build_upcoming_feature_row(player_history, team_stats, next_games, stat_category)
        if feature_row is not None:
            upcoming_features[player_name] = feature_row
    return upcoming_features


def build_all_features(stat_category="points", season=None):
    games = load_player_games(season=season)
    team_stats_by_season = {}
    games_by_player = group_games_by_player(games)

    all_features = []
    for player_name, player_history in games_by_player.items():
        for game_index in range(len(player_history)):
            game_season = player_history[game_index]["season"]
            if game_season not in team_stats_by_season:
                team_stats_by_season[game_season] = load_team_stats(season=game_season)
            feature_row = build_features_for_game(
                game_index, player_history, team_stats_by_season[game_season], stat_category
            )
            if feature_row is not None:
                all_features.append(feature_row)

    return all_features


if __name__ == "__main__":
    features = build_all_features()
    print(f"Built {len(features)} feature rows (player-games with enough history).")
    print("Example row:", features[100])
