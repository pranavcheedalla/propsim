"""
Shared SQLite layer for PropSim. Replaces the old player_games.csv /
team_stats.csv / next_games.csv files with one database so the app can
hold multiple seasons and stat categories, and so the backend has
somewhere durable to write favorites and logged bets (previously there
was nowhere to write anything - everything was read-only CSVs plus an
in-memory cache).

Schema:
  player_games(season, game_number, player_name, team, opponent_team,
               is_home, rest_days, minutes, points, rebounds, assists)
  team_stats(season, team, offensive_rating, defensive_rating, pace)
  next_games(team, opponent_team, is_home, game_date)
  favorites(player_name, added_at)
  bets(... see CREATE TABLE below)
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "propsim.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS player_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season TEXT NOT NULL,
    game_number INTEGER NOT NULL,
    game_date TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent_team TEXT NOT NULL,
    is_home INTEGER NOT NULL,
    rest_days INTEGER NOT NULL,
    minutes REAL NOT NULL,
    points INTEGER NOT NULL,
    rebounds INTEGER NOT NULL,
    assists INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_player_games_player ON player_games(player_name, game_number);
CREATE INDEX IF NOT EXISTS idx_player_games_season ON player_games(season);

CREATE TABLE IF NOT EXISTS team_stats (
    season TEXT NOT NULL,
    team TEXT NOT NULL,
    offensive_rating REAL NOT NULL,
    defensive_rating REAL NOT NULL,
    pace REAL NOT NULL,
    PRIMARY KEY (season, team)
);

CREATE TABLE IF NOT EXISTS next_games (
    team TEXT PRIMARY KEY,
    opponent_team TEXT NOT NULL,
    is_home INTEGER NOT NULL,
    game_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    player_name TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    player_name TEXT,
    team_a TEXT,
    team_b TEXT,
    stat_category TEXT,
    selection TEXT NOT NULL,
    line REAL,
    odds INTEGER NOT NULL,
    stake REAL NOT NULL DEFAULT 1,
    model_probability REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    actual_value REAL,
    settled_at TEXT,
    notes TEXT
);
"""


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()


def replace_player_games(rows):
    """Rows already carry `season`, so this only clears those seasons before reinserting (safe to re-run per season without wiping others)."""
    if not rows:
        return
    seasons = {row["season"] for row in rows}
    connection = get_connection()
    connection.executemany("DELETE FROM player_games WHERE season = ?", [(s,) for s in seasons])
    connection.executemany(
        """
        INSERT INTO player_games
            (season, game_number, game_date, player_name, team, opponent_team, is_home, rest_days, minutes, points, rebounds, assists)
        VALUES (:season, :game_number, :game_date, :player_name, :team, :opponent_team, :is_home, :rest_days, :minutes, :points, :rebounds, :assists)
        """,
        rows,
    )
    connection.commit()
    connection.close()


def replace_team_stats(rows):
    if not rows:
        return
    seasons = {row["season"] for row in rows}
    connection = get_connection()
    connection.executemany("DELETE FROM team_stats WHERE season = ?", [(s,) for s in seasons])
    connection.executemany(
        """
        INSERT INTO team_stats (season, team, offensive_rating, defensive_rating, pace)
        VALUES (:season, :team, :offensive_rating, :defensive_rating, :pace)
        """,
        rows,
    )
    connection.commit()
    connection.close()


def replace_next_games(rows):
    connection = get_connection()
    connection.execute("DELETE FROM next_games")
    connection.executemany(
        """
        INSERT INTO next_games (team, opponent_team, is_home, game_date)
        VALUES (:team, :opponent_team, :is_home, :game_date)
        """,
        rows,
    )
    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
