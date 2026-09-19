export function americanOddsToImpliedProbability(americanOdds) {
  return americanOdds < 0
    ? -americanOdds / (-americanOdds + 100)
    : 100 / (americanOdds + 100);
}

export function impliedProbabilityToAmericanOdds(probability) {
  return probability > 0.5
    ? Math.round((-100 * probability) / (1 - probability))
    : Math.round((100 * (1 - probability)) / probability);
}

// Given the favorite's American odds, derive the underdog's fair (no-vig)
// American odds: the two implied probabilities are complementary.
export function underdogOddsFromFavoriteOdds(favoriteOdds) {
  const favoriteProbability = americanOddsToImpliedProbability(favoriteOdds);
  return impliedProbabilityToAmericanOdds(1 - favoriteProbability);
}
