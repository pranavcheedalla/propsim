// Monte Carlo simulation engine for player prop and game outcome predictions.
//
// The idea: instead of deriving probabilities with a closed-form formula,
// simulate the player's game (or the full game) thousands of times using
// random draws from a fitted distribution, then just count outcomes.
//
// Exposed to Python via pybind11 as the "montecarlo" module.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <random>
#include <cmath>

using namespace std;
namespace py = pybind11;

// Simulates a player's stat total (points, rebounds, yards, etc.) for a
// single game many times, drawing from a normal distribution with the
// given mean and standard deviation, and reports:
//   - probability the total exceeds the betting line ("over")
//   - the simulated mean and standard deviation (sanity check on the draws)
//
// mean and standardDeviation should already reflect matchup adjustments
// (opponent defensive rank, pace, home/away, rest) computed in Python
// before calling this function.
py::dict simulatePlayerProp(double mean, double standardDeviation, double line,
                             int numSimulations, unsigned int seed) {
    mt19937 randomEngine(seed);
    normal_distribution<double> statDistribution(mean, standardDeviation);

    int overCount = 0;
    double sum = 0.0;
    double sumOfSquares = 0.0;

    for (int simulation = 0; simulation < numSimulations; simulation++) {
        double simulatedValue = statDistribution(randomEngine);
        if (simulatedValue < 0.0) {
            simulatedValue = 0.0;
        }

        if (simulatedValue > line) {
            overCount = overCount + 1;
        }

        sum = sum + simulatedValue;
        sumOfSquares = sumOfSquares + simulatedValue * simulatedValue;
    }

    double simulatedMean = sum / numSimulations;
    double variance = (sumOfSquares / numSimulations) - (simulatedMean * simulatedMean);
    if (variance < 0.0) {
        variance = 0.0;
    }
    double simulatedStandardDeviation = sqrt(variance);

    double probabilityOver = static_cast<double>(overCount) / numSimulations;

    py::dict result;
    result["probability_over"] = probabilityOver;
    result["probability_under"] = 1.0 - probabilityOver;
    result["simulated_mean"] = simulatedMean;
    result["simulated_standard_deviation"] = simulatedStandardDeviation;
    result["num_simulations"] = numSimulations;
    return result;
}

// Simulates a full game between two teams by drawing each team's final
// score from its own normal distribution (fitted in Python from offensive
// rating, opponent defensive rating, and pace), then compares the two
// simulated scores to estimate:
//   - probability team A wins (moneyline win probability)
//   - probability the combined score exceeds a given total line
py::dict simulateGame(double teamAMean, double teamAStandardDeviation,
                       double teamBMean, double teamBStandardDeviation,
                       double totalLine, int numSimulations, unsigned int seed) {
    mt19937 randomEngine(seed);
    normal_distribution<double> teamADistribution(teamAMean, teamAStandardDeviation);
    normal_distribution<double> teamBDistribution(teamBMean, teamBStandardDeviation);

    int teamAWinCount = 0;
    int overCount = 0;
    double marginSum = 0.0;

    for (int simulation = 0; simulation < numSimulations; simulation++) {
        double teamAScore = teamADistribution(randomEngine);
        double teamBScore = teamBDistribution(randomEngine);
        if (teamAScore < 0.0) {
            teamAScore = 0.0;
        }
        if (teamBScore < 0.0) {
            teamBScore = 0.0;
        }

        if (teamAScore > teamBScore) {
            teamAWinCount = teamAWinCount + 1;
        }

        double combinedScore = teamAScore + teamBScore;
        if (combinedScore > totalLine) {
            overCount = overCount + 1;
        }

        marginSum = marginSum + (teamAScore - teamBScore);
    }

    double probabilityTeamAWins = static_cast<double>(teamAWinCount) / numSimulations;
    double probabilityOverTotal = static_cast<double>(overCount) / numSimulations;
    double averageMargin = marginSum / numSimulations;

    py::dict result;
    result["probability_team_a_wins"] = probabilityTeamAWins;
    result["probability_team_b_wins"] = 1.0 - probabilityTeamAWins;
    result["probability_over_total"] = probabilityOverTotal;
    result["probability_under_total"] = 1.0 - probabilityOverTotal;
    result["average_margin_team_a"] = averageMargin;
    result["num_simulations"] = numSimulations;
    return result;
}

// Converts American moneyline/prop odds (e.g. -110, +150) into the
// breakeven probability implied by the sportsbook, so a model probability
// can be compared directly against the market.
double impliedProbabilityFromAmericanOdds(int americanOdds) {
    if (americanOdds < 0) {
        double positiveOdds = static_cast<double>(-americanOdds);
        return positiveOdds / (positiveOdds + 100.0);
    } else {
        double odds = static_cast<double>(americanOdds);
        return 100.0 / (odds + 100.0);
    }
}

PYBIND11_MODULE(montecarlo, module) {
    module.doc() = "C++ Monte Carlo engine for player prop and moneyline simulation";
    module.def("simulate_player_prop", &simulatePlayerProp,
               py::arg("mean"), py::arg("standard_deviation"), py::arg("line"),
               py::arg("num_simulations") = 10000, py::arg("seed") = 42,
               "Simulate a player's stat total against a prop line");
    module.def("simulate_game", &simulateGame,
               py::arg("team_a_mean"), py::arg("team_a_standard_deviation"),
               py::arg("team_b_mean"), py::arg("team_b_standard_deviation"),
               py::arg("total_line"), py::arg("num_simulations") = 10000,
               py::arg("seed") = 42,
               "Simulate a full game to estimate moneyline and total probabilities");
    module.def("implied_probability_from_american_odds", &impliedProbabilityFromAmericanOdds,
               py::arg("american_odds"),
               "Convert American odds to the sportsbook's implied breakeven probability");
}
