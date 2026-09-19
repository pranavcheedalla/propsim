import pytest

montecarlo = pytest.importorskip("montecarlo", reason="C++ extension not built - run cmake/make in cpp/build first")

NUM_SIMULATIONS = 200_000
TOLERANCE = 0.01


def test_probabilities_sum_to_one():
    result = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=5.0, line=18.5, num_simulations=NUM_SIMULATIONS)
    assert result["probability_over"] + result["probability_under"] == pytest.approx(1.0, abs=1e-6)


def test_line_at_mean_is_roughly_a_coin_flip():
    result = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=5.0, line=20.0, num_simulations=NUM_SIMULATIONS)
    assert result["probability_over"] == pytest.approx(0.5, abs=TOLERANCE)


def test_probability_over_decreases_as_line_rises():
    low_line = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=5.0, line=15.0, num_simulations=NUM_SIMULATIONS)
    high_line = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=5.0, line=25.0, num_simulations=NUM_SIMULATIONS)
    assert low_line["probability_over"] > high_line["probability_over"]


def test_tighter_distribution_is_more_confident_away_from_mean():
    tight = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=2.0, line=25.0, num_simulations=NUM_SIMULATIONS)
    wide = montecarlo.simulate_player_prop(mean=20.0, standard_deviation=10.0, line=25.0, num_simulations=NUM_SIMULATIONS)
    # A tighter distribution should be MORE confident the total stays
    # under a line that's well above the mean (lower P(over)).
    assert tight["probability_over"] < wide["probability_over"]


def test_simulate_game_favors_the_higher_mean_team():
    result = montecarlo.simulate_game(
        team_a_mean=118.0, team_a_standard_deviation=10.0,
        team_b_mean=105.0, team_b_standard_deviation=10.0,
        total_line=220.0, num_simulations=NUM_SIMULATIONS,
    )
    assert result["probability_team_a_wins"] > result["probability_team_b_wins"]
    assert result["probability_team_a_wins"] + result["probability_team_b_wins"] == pytest.approx(1.0, abs=1e-3)


def test_simulate_game_total_probabilities_sum_to_one():
    result = montecarlo.simulate_game(
        team_a_mean=112.0, team_a_standard_deviation=10.0,
        team_b_mean=110.0, team_b_standard_deviation=10.0,
        total_line=222.5, num_simulations=NUM_SIMULATIONS,
    )
    assert result["probability_over_total"] + result["probability_under_total"] == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("odds,expected_probability", [
    (-110, 110 / 210),
    (-200, 200 / 300),
    (100, 0.5),
    (150, 100 / 250),
])
def test_implied_probability_from_american_odds(odds, expected_probability):
    assert montecarlo.implied_probability_from_american_odds(odds) == pytest.approx(expected_probability, abs=1e-6)
