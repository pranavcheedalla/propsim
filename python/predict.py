"""
Ties the feature layer to the C++ Monte Carlo engine to produce a
prop prediction for a given player, plus a comparison against a
sportsbook line if American odds are supplied.

Usage:
    python3 predict.py --player "Kings Player 1" --line 24.5
    python3 predict.py --player "Kings Player 1" --line 24.5 --over-odds -115 --under-odds -105
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cpp", "build"))
sys.path.insert(0, os.path.dirname(__file__))

import montecarlo
from features import build_all_features


def most_recent_feature_row_for_player(all_features, player_name):
    matching_rows = [row for row in all_features if row["player_name"] == player_name]
    if len(matching_rows) == 0:
        return None
    matching_rows.sort(key=lambda row: row["game_number"])
    return matching_rows[-1]


def predict_prop(player_name, line, num_simulations=100000, over_odds=None, under_odds=None):
    all_features = build_all_features()
    feature_row = most_recent_feature_row_for_player(all_features, player_name)
    if feature_row is None:
        print(f"No data found for player '{player_name}'. Run data/fetch_real_data.py first, "
              f"or check the spelling (diacritics matter, e.g. 'Nikola Jokić').")
        return

    simulation_result = montecarlo.simulate_player_prop(
        mean=feature_row["adjusted_mean"],
        standard_deviation=feature_row["adjusted_standard_deviation"],
        line=line,
        num_simulations=num_simulations,
    )

    print(f"Player:              {player_name} ({feature_row['team']})")
    print(f"Opponent:            {feature_row['opponent_team']}")
    print(f"Rolling avg (raw):   {feature_row['rolling_mean_before_adjustment']:.1f} points")
    print(f"Matchup-adjusted:    {feature_row['adjusted_mean']:.1f} points "
          f"(std dev {feature_row['adjusted_standard_deviation']:.1f})")
    print(f"Prop line:           {line}")
    print(f"Model P(over):       {simulation_result['probability_over']:.1%}")
    print(f"Model P(under):      {simulation_result['probability_under']:.1%}")
    print(f"Simulations run:     {simulation_result['num_simulations']:,}")

    if over_odds is not None:
        market_probability_over = montecarlo.implied_probability_from_american_odds(over_odds)
        edge = simulation_result["probability_over"] - market_probability_over
        print(f"\nMarket over odds:    {over_odds:+d}  (implied {market_probability_over:.1%})")
        print(f"Model edge on over:  {edge:+.1%}")

    if under_odds is not None:
        market_probability_under = montecarlo.implied_probability_from_american_odds(under_odds)
        edge = simulation_result["probability_under"] - market_probability_under
        print(f"Market under odds:   {under_odds:+d}  (implied {market_probability_under:.1%})")
        print(f"Model edge on under: {edge:+.1%}")


def main():
    parser = argparse.ArgumentParser(description="Predict a player prop over/under using the Monte Carlo engine")
    parser.add_argument("--player", required=True, help="Player name, exactly as nba_api spells it (diacritics matter)")
    parser.add_argument("--line", required=True, type=float, help="Sportsbook prop line, e.g. 24.5")
    parser.add_argument("--simulations", type=int, default=100000)
    parser.add_argument("--over-odds", type=int, default=None, help="American odds for the over, e.g. -110")
    parser.add_argument("--under-odds", type=int, default=None, help="American odds for the under, e.g. -110")
    arguments = parser.parse_args()

    predict_prop(
        player_name=arguments.player,
        line=arguments.line,
        num_simulations=arguments.simulations,
        over_odds=arguments.over_odds,
        under_odds=arguments.under_odds,
    )


if __name__ == "__main__":
    main()
