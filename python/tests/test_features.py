import features


def make_game(game_number, minutes=30.0, points=20, rebounds=5, assists=5, is_home=1, rest_days=2,
              team="Team A", opponent_team="Team B", season="2025-26", player_name="Test Player"):
    return {
        "season": season,
        "game_number": game_number,
        "game_date": f"2025-11-{game_number:02d}",
        "player_name": player_name,
        "team": team,
        "opponent_team": opponent_team,
        "is_home": is_home,
        "rest_days": rest_days,
        "minutes": minutes,
        "points": points,
        "rebounds": rebounds,
        "assists": assists,
    }


LEAGUE_AVERAGE_TEAM_STATS = {
    "Team B": {"offensive_rating": 114.0, "defensive_rating": 114.0, "pace": 99.0},
}


def test_stat_value_combos():
    game = make_game(1, points=25, rebounds=10, assists=5)
    assert features.stat_value(game, "points") == 25
    assert features.stat_value(game, "rebounds") == 10
    assert features.stat_value(game, "assists") == 5
    assert features.stat_value(game, "pra") == 40
    assert features.stat_value(game, "pa") == 30
    assert features.stat_value(game, "ra") == 15


def test_rolling_mean_and_standard_deviation_needs_two_values():
    assert features.rolling_mean_and_standard_deviation([10]) == (None, None)


def test_rolling_mean_and_standard_deviation_floors_low_scorers():
    # A very consistent low-volume rebounder shouldn't collapse to a
    # near-zero standard deviation - the floor keeps the simulation honest.
    mean, standard_deviation = features.rolling_mean_and_standard_deviation([4, 4, 4, 4])
    assert mean == 4
    assert standard_deviation == 1.5


def test_rolling_mean_and_standard_deviation_floors_high_scorers():
    mean, standard_deviation = features.rolling_mean_and_standard_deviation([20, 20, 20, 20])
    assert mean == 20
    assert standard_deviation == 3.0


def test_build_features_for_game_requires_five_prior_games():
    history = [make_game(i) for i in range(1, 5)] + [make_game(5, opponent_team="Team B")]
    result = features.build_features_for_game(4, history, LEAGUE_AVERAGE_TEAM_STATS, "points")
    assert result is None


def test_build_features_for_game_excludes_low_minute_appearances():
    # Ten prior games, but half are garbage-time cameos that should be
    # excluded from the rolling window, not silently drag the average down.
    history = [make_game(i, minutes=5.0, points=2) for i in range(1, 6)]
    history += [make_game(i, minutes=30.0, points=20) for i in range(6, 11)]
    history += [make_game(11, opponent_team="Team B")]

    result = features.build_features_for_game(10, history, LEAGUE_AVERAGE_TEAM_STATS, "points")
    assert result is not None
    assert result["rolling_mean_before_adjustment"] == 20


def test_build_features_for_game_no_lookahead():
    # The feature for game index N must never see game N's own stat line.
    history = [make_game(i, points=10) for i in range(1, 6)]
    history += [make_game(6, points=999, opponent_team="Team B")]

    result = features.build_features_for_game(5, history, LEAGUE_AVERAGE_TEAM_STATS, "points")
    assert result["rolling_mean_before_adjustment"] == 10
    assert result["actual_value"] == 999


def test_build_features_for_game_missing_opponent_stats_returns_none():
    history = [make_game(i) for i in range(1, 6)] + [make_game(6, opponent_team="Unknown Team")]
    result = features.build_features_for_game(5, history, LEAGUE_AVERAGE_TEAM_STATS, "points")
    assert result is None


def test_build_features_for_game_home_adjustment_direction():
    history = [make_game(i, points=20) for i in range(1, 6)]
    home_game = make_game(6, is_home=1, opponent_team="Team B", rest_days=3)
    away_game = make_game(6, is_home=0, opponent_team="Team B", rest_days=3)

    home_result = features.build_features_for_game(5, history + [home_game], LEAGUE_AVERAGE_TEAM_STATS, "points")
    away_result = features.build_features_for_game(5, history + [away_game], LEAGUE_AVERAGE_TEAM_STATS, "points")

    assert home_result["adjusted_mean"] > away_result["adjusted_mean"]


def test_availability_signal_needs_five_games():
    history = [make_game(i) for i in range(1, 4)]
    assert features.availability_signal(history, 3) is None


def test_availability_signal_detects_declining_minutes():
    history = [make_game(i, minutes=35.0) for i in range(1, 8)]
    history += [make_game(i, minutes=15.0) for i in range(8, 11)]

    signal = features.availability_signal(history, 10)
    assert signal["recent_minutes_avg"] == 15.0
    assert signal["minutes_trend"] < 0


def test_build_upcoming_feature_row_uses_next_game_opponent():
    history = [make_game(i, points=20, team="Team A") for i in range(1, 8)]
    next_games = {"Team A": {"opponent_team": "Team B", "is_home": 1, "game_date": "2026-10-20"}}

    result = features.build_upcoming_feature_row(history, LEAGUE_AVERAGE_TEAM_STATS, next_games, "points")
    assert result["opponent_team"] == "Team B"
    assert result["game_date"] == "2026-10-20"


def test_build_upcoming_feature_row_none_without_scheduled_game():
    history = [make_game(i, team="Team A") for i in range(1, 8)]
    result = features.build_upcoming_feature_row(history, LEAGUE_AVERAGE_TEAM_STATS, {}, "points")
    assert result is None
