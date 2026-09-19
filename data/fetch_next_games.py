"""
Pulls each team's next scheduled regular-season game from the real NBA
schedule (nba_api's ScheduleLeagueV2) and writes next_games.csv
(team, opponent_team, is_home, game_date).

The player-prop feature pipeline uses this so a prediction reflects
each player's actual next opponent, instead of whatever team they
happened to play last in the historical game log (which becomes a
real problem once that log is a completed season: the "last opponent"
is just the season finale, not an upcoming game).

Usage:
    python3 fetch_next_games.py [season]

season defaults to the next unplayed season (e.g. "2026-27"). Team
ratings for matchup adjustment still come from team_stats.csv (last
completed season), since no games have been played yet to rate teams on.
"""

import sys
from datetime import datetime, timezone

from nba_api.stats.endpoints import scheduleleaguev2

import db

DEFAULT_SEASON = "2026-27"
REGULAR_SEASON_GAME_ID_PREFIX = "002"


def fetch_next_games(season):
    response = scheduleleaguev2.ScheduleLeagueV2(season=season, timeout=30)
    data_frame = response.get_data_frames()[0]
    data_frame = data_frame[data_frame["gameId"].str.startswith(REGULAR_SEASON_GAME_ID_PREFIX)]
    data_frame = data_frame.dropna(subset=["homeTeam_teamName", "awayTeam_teamName"])

    data_frame["game_datetime"] = data_frame["gameDateEst"].apply(
        lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    now = datetime.now(timezone.utc)
    upcoming_games = data_frame[data_frame["game_datetime"] >= now].sort_values("game_datetime")

    next_game_by_team = {}
    for _, row in upcoming_games.iterrows():
        home_team = f"{row['homeTeam_teamCity']} {row['homeTeam_teamName']}"
        away_team = f"{row['awayTeam_teamCity']} {row['awayTeam_teamName']}"
        game_date = row["game_datetime"].date().isoformat()

        if home_team not in next_game_by_team:
            next_game_by_team[home_team] = {
                "team": home_team, "opponent_team": away_team,
                "is_home": 1, "game_date": game_date,
            }
        if away_team not in next_game_by_team:
            next_game_by_team[away_team] = {
                "team": away_team, "opponent_team": home_team,
                "is_home": 0, "game_date": game_date,
            }

    return list(next_game_by_team.values())


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEASON
    print(f"Fetching next scheduled game per team for season {season}...")
    db.init_db()
    next_games = fetch_next_games(season)
    db.replace_next_games(next_games)
    print(f"Wrote {len(next_games)} rows to {db.DB_PATH}")


if __name__ == "__main__":
    main()
