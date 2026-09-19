const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function requestJson(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail || `Request to ${path} failed`);
  }
  return response.json();
}

function jsonBody(method, payload) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) };
}

export function fetchPlayers() {
  return requestJson("/api/players");
}

export function fetchPlayerHistory(playerName, stat, games = 15) {
  return requestJson(
    `/api/players/${encodeURIComponent(playerName)}/history?stat=${stat}&games=${games}`
  );
}

export function fetchTeams() {
  return requestJson("/api/teams");
}

export function fetchSeasons() {
  return requestJson("/api/seasons");
}

export function fetchBacktestSummary(stat = "points", season = "all") {
  return requestJson(`/api/backtest?stat=${stat}&season=${encodeURIComponent(season)}`);
}

export function fetchInjuries(team) {
  return requestJson(`/api/injuries/${encodeURIComponent(team)}`);
}

export function fetchLiveOdds(teamA, teamB, gameDate) {
  const params = new URLSearchParams({ team_a: teamA, team_b: teamB });
  if (gameDate) params.set("game_date", gameDate);
  return requestJson(`/api/live-odds?${params.toString()}`);
}

export function predictProp(payload) {
  return requestJson("/api/predict/prop", jsonBody("POST", payload));
}

export function predictGame(payload) {
  return requestJson("/api/predict/game", jsonBody("POST", payload));
}

export function fetchFavorites() {
  return requestJson("/api/favorites");
}

export function addFavorite(playerName) {
  return requestJson("/api/favorites", jsonBody("POST", { player_name: playerName }));
}

export function removeFavorite(playerName) {
  return requestJson(`/api/favorites/${encodeURIComponent(playerName)}`, { method: "DELETE" });
}

export function fetchBets() {
  return requestJson("/api/bets");
}

export function createBet(payload) {
  return requestJson("/api/bets", jsonBody("POST", payload));
}

export function settleBet(betId, payload) {
  return requestJson(`/api/bets/${betId}`, jsonBody("PATCH", payload));
}

export function deleteBet(betId) {
  return requestJson(`/api/bets/${betId}`, { method: "DELETE" });
}
