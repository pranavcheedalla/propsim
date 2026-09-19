import { useEffect, useState } from "react";
import { fetchTeams, predictGame, fetchLiveOdds } from "../api";
import { underdogOddsFromFavoriteOdds } from "../odds";
import ProbabilityBar from "./ProbabilityBar";
import TeamLogo from "./TeamLogo";
import useLocalStorage from "../hooks/useLocalStorage";
import { getTeamMeta } from "../teamMeta";

export default function GameMoneylineTab() {
  const [teams, setTeams] = useState([]);
  const [teamA, setTeamA] = useLocalStorage("propsim:teamA", "");
  const [teamB, setTeamB] = useLocalStorage("propsim:teamB", "");
  const [favorite, setFavorite] = useState("teamA");
  const [favoriteOdds, setFavoriteOdds] = useState("-150");
  const [totalLine, setTotalLine] = useState("222.5");
  const [liveOdds, setLiveOdds] = useState(null);
  const [isLoadingOdds, setIsLoadingOdds] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchTeams()
      .then((data) => {
        setTeams(data.teams);
        const teamNames = new Set(data.teams.map((team) => team.team));
        if (!teamNames.has(teamA) && data.teams.length > 0) {
          setTeamA(data.teams[0].team);
        }
        if (!teamNames.has(teamB) && data.teams.length > 1) {
          setTeamB(data.teams[1].team);
        }
      })
      .catch((error) => setErrorMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!teamA || !teamB || teamA === teamB) {
      setLiveOdds(null);
      return;
    }
    let isStale = false;
    setIsLoadingOdds(true);
    fetchLiveOdds(teamA, teamB)
      .then((data) => {
        if (isStale) return;
        setLiveOdds(data.available ? data : null);
        if (data.available) {
          setTotalLine(String(data.total_line));
          const teamAIsFavorite = data.team_a_moneyline_odds < data.team_b_moneyline_odds;
          setFavorite(teamAIsFavorite ? "teamA" : "teamB");
          setFavoriteOdds(String(teamAIsFavorite ? data.team_a_moneyline_odds : data.team_b_moneyline_odds));
        }
      })
      .catch(() => {
        if (!isStale) setLiveOdds(null);
      })
      .finally(() => {
        if (!isStale) setIsLoadingOdds(false);
      });
    return () => {
      isStale = true;
    };
  }, [teamA, teamB]);

  async function handlePredict(event) {
    event.preventDefault();
    setErrorMessage("");
    setIsLoading(true);
    try {
      const payload = {
        team_a: teamA,
        team_b: teamB,
        total_line: parseFloat(totalLine),
      };

      const parsedFavoriteOdds = favoriteOdds.trim() !== "" ? parseInt(favoriteOdds, 10) : null;
      if (parsedFavoriteOdds !== null) {
        const underdogOdds = underdogOddsFromFavoriteOdds(parsedFavoriteOdds);
        if (favorite === "teamA") {
          payload.team_a_moneyline_odds = parsedFavoriteOdds;
          payload.team_b_moneyline_odds = underdogOdds;
        } else {
          payload.team_b_moneyline_odds = parsedFavoriteOdds;
          payload.team_a_moneyline_odds = underdogOdds;
        }
      }

      const data = await predictGame(payload);
      setResult(data);
    } catch (error) {
      setErrorMessage(error.message);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  const teamAMeta = getTeamMeta(teamA);
  const teamBMeta = getTeamMeta(teamB);

  return (
    <div className="tab-content">
      <form className="prediction-form" onSubmit={handlePredict}>
        <label>
          Team A
          <div className="select-with-logo">
            <TeamLogo team={teamA} size={24} />
            <select value={teamA} onChange={(e) => setTeamA(e.target.value)}>
              {teams.map((team) => (
                <option key={team.team} value={team.team}>
                  {team.team}
                </option>
              ))}
            </select>
          </div>
        </label>

        <label>
          Team B
          <div className="select-with-logo">
            <TeamLogo team={teamB} size={24} />
            <select value={teamB} onChange={(e) => setTeamB(e.target.value)}>
              {teams.map((team) => (
                <option key={team.team} value={team.team}>
                  {team.team}
                </option>
              ))}
            </select>
          </div>
        </label>

        <label>
          Total line
          <input type="number" step="0.5" value={totalLine} onChange={(e) => setTotalLine(e.target.value)} />
        </label>

        <label>
          Favorite
          <select value={favorite} onChange={(e) => setFavorite(e.target.value)}>
            <option value="teamA">{teamA || "Team A"}</option>
            <option value="teamB">{teamB || "Team B"}</option>
          </select>
        </label>

        <label className="span-2">
          Favorite's moneyline odds (American)
          <input
            type="text"
            value={favoriteOdds}
            onChange={(e) => setFavoriteOdds(e.target.value)}
            placeholder="-150"
          />
        </label>

        <p className="market-note muted span-2">
          {isLoadingOdds
            ? "Checking DraftKings for a posted market line..."
            : liveOdds
            ? `Live market line found (${liveOdds.provider}) — prefilled below, still editable.`
            : "No market line posted yet for this matchup — enter odds manually."}
        </p>

        <button type="submit" className="span-2" disabled={isLoading || !teamA || !teamB}>
          {isLoading ? "Simulating..." : "Predict"}
        </button>
      </form>

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {result && (
        <div
          className="result-card"
          style={{ "--team-a-color": teamAMeta.primary, "--team-b-color": teamBMeta.primary }}
        >
          <div className="matchup-strip matchup-strip--game">
            <div className="matchup-side">
              <TeamLogo team={result.team_a} size={44} />
              <div>
                <h3>{result.team_a}</h3>
                <span className="score-projection">{result.team_a_projected_score}</span>
              </div>
            </div>
            <span className="matchup-vs">vs</span>
            <div className="matchup-side matchup-side--opponent">
              <div className="score-side-text">
                <h3>{result.team_b}</h3>
                <span className="score-projection">{result.team_b_projected_score}</span>
              </div>
              <TeamLogo team={result.team_b} size={44} />
            </div>
          </div>

          <ProbabilityBar
            label={`${result.team_a} win probability`}
            probability={result.probability_team_a_wins}
            color={teamAMeta.primary}
          />
          <ProbabilityBar
            label={`${result.team_b} win probability`}
            probability={result.probability_team_b_wins}
            color={teamBMeta.primary}
          />
          <ProbabilityBar
            label={`P(over ${result.total_line})`}
            probability={result.probability_over_total}
            tone="positive"
          />
          <ProbabilityBar
            label={`P(under ${result.total_line})`}
            probability={result.probability_under_total}
            tone="neutral"
          />

          {result.edge_team_a !== undefined && (
            <p className={`edge-line ${result.edge_team_a >= 0 ? "edge-positive" : "edge-negative"}`}>
              Edge on {result.team_a}: {(result.edge_team_a * 100).toFixed(1)}% (market implies{" "}
              {(result.market_implied_probability_team_a * 100).toFixed(1)}% at {result.team_a_moneyline_odds})
            </p>
          )}
          {result.edge_team_b !== undefined && (
            <p className={`edge-line ${result.edge_team_b >= 0 ? "edge-positive" : "edge-negative"}`}>
              Edge on {result.team_b}: {(result.edge_team_b * 100).toFixed(1)}% (market implies{" "}
              {(result.market_implied_probability_team_b * 100).toFixed(1)}% at {result.team_b_moneyline_odds})
            </p>
          )}
        </div>
      )}
    </div>
  );
}
