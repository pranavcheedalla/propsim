"""
Pulls real NBA player game logs (points, rebounds, assists, minutes) and
team advanced stats for one or more seasons from nba_api, and writes them
into propsim.db (see db.py). Multiple seasons let the backtest measure
whether the model's edge holds up across different years instead of one
(the whole point of "is 52% signal or noise").

Usage:
    pip install nba_api
    python3 fetch_real_data.py [season ...]

With no arguments, pulls the last three completed seasons.
"""

import sys
from datetime import datetime

from nba_api.stats.endpoints import leaguedashteamstats, leaguegamelog

import db

DEFAULT_SEASONS = ["2023-24", "2024-25", "2025-26"]


def fetch_team_stats(season):
    response = leaguedashteamstats.LeagueDashTeamStats(
        season=season, measure_type_detailed_defense="Advanced", timeout=30
    )
    data_frame = response.get_data_frames()[0]

    rows = []
    for _, row in data_frame.iterrows():
        rows.append({
            "season": season,
            "team": row["TEAM_NAME"],
            "offensive_rating": round(float(row["OFF_RATING"]), 1),
            "defensive_rating": round(float(row["DEF_RATING"]), 1),
            "pace": round(float(row["PACE"]), 1),
        })
    return rows


def compute_rest_days_by_team_and_date(data_frame):
    team_games = (
        data_frame[["TEAM_ABBREVIATION", "GAME_DATE"]]
        .drop_duplicates()
        .sort_values(["TEAM_ABBREVIATION", "GAME_DATE"])
    )

    rest_days_by_team_and_date = {}
    previous_date_by_team = {}
    for _, row in team_games.iterrows():
        team = row["TEAM_ABBREVIATION"]
        game_date = row["GAME_DATE"]
        previous_date = previous_date_by_team.get(team)
        rest_days = (game_date - previous_date).days if previous_date is not None else 3
        rest_days_by_team_and_date[(team, game_date)] = rest_days
        previous_date_by_team[team] = game_date

    return rest_days_by_team_and_date


def fetch_player_games(season, starting_game_number):
    response = leaguegamelog.LeagueGameLog(
        season=season, player_or_team_abbreviation="P", timeout=30
    )
    data_frame = response.get_data_frames()[0]
    data_frame["GAME_DATE"] = data_frame["GAME_DATE"].apply(
        lambda value: datetime.strptime(value, "%Y-%m-%d")
    )

    # Built from the game log itself (not nba_api's static teams module,
    # whose "Los Angeles Clippers" full name disagrees with the stats
    # endpoints' own "LA Clippers") so names always match team_stats.
    abbreviation_to_full_name = dict(
        zip(data_frame["TEAM_ABBREVIATION"], data_frame["TEAM_NAME"])
    )
    rest_days_by_team_and_date = compute_rest_days_by_team_and_date(data_frame)

    data_frame = data_frame.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)

    rows = []
    for index, row in data_frame.iterrows():
        matchup = row["MATCHUP"]
        is_home = 1 if "vs." in matchup else 0
        opponent_abbreviation = matchup.split()[-1]
        opponent_team = abbreviation_to_full_name.get(opponent_abbreviation, opponent_abbreviation)

        rows.append({
            "season": season,
            "game_number": starting_game_number + index,
            "game_date": row["GAME_DATE"].date().isoformat(),
            "player_name": row["PLAYER_NAME"],
            "team": row["TEAM_NAME"],
            "opponent_team": opponent_team,
            "is_home": is_home,
            "rest_days": rest_days_by_team_and_date[(row["TEAM_ABBREVIATION"], row["GAME_DATE"])],
            "minutes": float(row["MIN"]) if row["MIN"] is not None else 0.0,
            "points": int(row["PTS"]),
            "rebounds": int(row["REB"]),
            "assists": int(row["AST"]),
        })
    return rows, starting_game_number + len(rows)


def main():
    seasons = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SEASONS
    db.init_db()

    game_number_cursor = 1
    for season in seasons:
        print(f"Fetching {season}...")
        player_games, game_number_cursor = fetch_player_games(season, game_number_cursor)
        db.replace_player_games(player_games)
        print(f"  {len(player_games)} player-game rows")

        team_stats_rows = fetch_team_stats(season)
        db.replace_team_stats(team_stats_rows)
        print(f"  {len(team_stats_rows)} team rows")

    print(f"Done. Database at {db.DB_PATH}")


if __name__ == "__main__":
    main()
