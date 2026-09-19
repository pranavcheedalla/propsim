"""
Backtests the model against historical games: for every player-game with
enough prior history, build the feature (adjusted mean/std) using ONLY
games before it, simulate a prop line set at that game's actual rolling
average (standing in for a realistic sportsbook line), and check whether
the model's predicted side actually happened.

Reports:
  - Hit rate: how often the model's predicted over/under side was correct
  - Calibration: when the model says "70% confident", does it actually
    land around 70% of the time?
  - A simple flat-bet ROI at -110 odds, for context

This is what turns "a model that runs" into "a model with a number behind
it" for a resume bullet.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cpp", "build"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import montecarlo
from features import build_all_features

NUM_SIMULATIONS_PER_PREDICTION = 20000
AMERICAN_ODDS_FOR_ROI = -110
CALIBRATION_BUCKET_WIDTH = 0.10


def implied_line_from_rolling_average(feature_row):
    # Stand-in for a sportsbook line: real sportsbooks set lines close to
    # their own projection of a player's average, so using the player's
    # OWN rolling average (before matchup adjustment) as the line gives a
    # fair, non-cherry-picked test of whether the matchup adjustment adds
    # real predictive signal on top of a naive "expect their average" line.
    return round(feature_row["rolling_mean_before_adjustment"] * 2) / 2.0


def run_backtest(stat_category="points", season=None):
    all_features = build_all_features(stat_category=stat_category, season=season)
    print(f"Backtesting on {len(all_features)} player-games...\n")

    correct_predictions = 0
    total_predictions = 0
    calibration_buckets = {}
    profit_in_units = 0.0
    by_season = {}

    for feature_row in all_features:
        line = implied_line_from_rolling_average(feature_row)

        simulation_result = montecarlo.simulate_player_prop(
            mean=feature_row["adjusted_mean"],
            standard_deviation=feature_row["adjusted_standard_deviation"],
            line=line,
            num_simulations=NUM_SIMULATIONS_PER_PREDICTION,
        )

        probability_over = simulation_result["probability_over"]
        predicted_side = "over" if probability_over >= 0.5 else "under"
        model_confidence = probability_over if predicted_side == "over" else (1.0 - probability_over)

        actual_value = feature_row["actual_value"]
        actual_side = "over" if actual_value > line else "under"
        # A push (actual value exactly equal to the line) is excluded,
        # same as a real sportsbook would void the bet.
        if actual_value == line:
            continue

        was_correct = predicted_side == actual_side
        total_predictions += 1
        if was_correct:
            correct_predictions += 1
            profit_in_units += 100.0 / abs(AMERICAN_ODDS_FOR_ROI)
        else:
            profit_in_units -= 1.0

        season_bucket = by_season.setdefault(feature_row["season"], {"count": 0, "correct": 0})
        season_bucket["count"] += 1
        if was_correct:
            season_bucket["correct"] += 1

        bucket_index = min(int(model_confidence / CALIBRATION_BUCKET_WIDTH), 9)
        if bucket_index not in calibration_buckets:
            calibration_buckets[bucket_index] = {"count": 0, "correct": 0}
        calibration_buckets[bucket_index]["count"] += 1
        if was_correct:
            calibration_buckets[bucket_index]["correct"] += 1

    hit_rate = correct_predictions / total_predictions if total_predictions > 0 else 0.0
    roi_percent = (profit_in_units / total_predictions) * 100.0 if total_predictions > 0 else 0.0

    print(f"Total graded predictions: {total_predictions}")
    print(f"Correct predictions:      {correct_predictions}")
    print(f"Hit rate:                 {hit_rate:.1%}")
    print(f"Flat-bet ROI at {AMERICAN_ODDS_FOR_ROI}:      {roi_percent:+.1f}%")
    print()
    print("Calibration (model confidence bucket -> actual hit rate):")
    for bucket_index in sorted(calibration_buckets.keys()):
        bucket = calibration_buckets[bucket_index]
        bucket_low = bucket_index * CALIBRATION_BUCKET_WIDTH
        bucket_high = bucket_low + CALIBRATION_BUCKET_WIDTH
        actual_rate = bucket["correct"] / bucket["count"]
        print(f"  {bucket_low:.0%}-{bucket_high:.0%} confidence: "
              f"{actual_rate:.1%} actual hit rate ({bucket['count']} predictions)")

    calibration = [
        {
            "confidence_low": bucket_index * CALIBRATION_BUCKET_WIDTH,
            "confidence_high": bucket_index * CALIBRATION_BUCKET_WIDTH + CALIBRATION_BUCKET_WIDTH,
            "actual_hit_rate": bucket["correct"] / bucket["count"],
            "num_predictions": bucket["count"],
        }
        for bucket_index, bucket in sorted(calibration_buckets.items())
    ]

    by_season_summary = [
        {
            "season": season_name,
            "total_predictions": bucket["count"],
            "hit_rate": bucket["correct"] / bucket["count"] if bucket["count"] else 0.0,
        }
        for season_name, bucket in sorted(by_season.items())
    ]

    return {
        "stat_category": stat_category,
        "total_predictions": total_predictions,
        "correct_predictions": correct_predictions,
        "hit_rate": hit_rate,
        "roi_percent": roi_percent,
        "calibration": calibration,
        "by_season": by_season_summary,
    }


if __name__ == "__main__":
    run_backtest()
