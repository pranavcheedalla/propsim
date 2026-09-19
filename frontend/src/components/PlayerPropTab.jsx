import { useEffect, useState } from "react";
import { fetchPlayers, fetchFavorites, addFavorite, removeFavorite, fetchPlayerHistory, predictProp, createBet } from "../api";
import ProbabilityBar from "./ProbabilityBar";
import TeamLogo from "./TeamLogo";
import TrendChart from "./TrendChart";
import PlayerSearch from "./PlayerSearch";
import { SkeletonLine, SkeletonCard } from "./Skeleton";
import { useToast } from "./ToastProvider";
import useLocalStorage from "../hooks/useLocalStorage";
import { getTeamMeta } from "../teamMeta";

const STAT_OPTIONS = [
  { value: "points", label: "Points" },
  { value: "rebounds", label: "Rebounds" },
  { value: "assists", label: "Assists" },
  { value: "pra", label: "PRA (Pts+Reb+Ast)" },
  { value: "pa", label: "PA (Pts+Ast)" },
  { value: "ra", label: "RA (Reb+Ast)" },
];

export default function PlayerPropTab() {
  const showToast = useToast();
  const [players, setPlayers] = useState([]);
  const [isLoadingPlayers, setIsLoadingPlayers] = useState(true);
  const [favorites, setFavorites] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useLocalStorage("propsim:selectedPlayer", "");
  const [statCategory, setStatCategory] = useLocalStorage("propsim:statCategory", "points");
  const [line, setLine] = useState("24.5");
  const [overOdds, setOverOdds] = useState("-110");
  const [underOdds, setUnderOdds] = useState("-110");
  const [side, setSide] = useLocalStorage("propsim:side", "over");
  const [stake, setStake] = useState("10");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggingBet, setIsLoggingBet] = useState(false);

  useEffect(() => {
    fetchPlayers()
      .then((data) => {
        setPlayers(data.players);
        const storedPlayerStillExists = data.players.some((player) => player.player_name === selectedPlayer);
        if (!storedPlayerStillExists && data.players.length > 0) {
          setSelectedPlayer(data.players[0].player_name);
        }
      })
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setIsLoadingPlayers(false));
    fetchFavorites()
      .then((data) => setFavorites(data.favorites))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedPlayer) return;
    setIsLoadingHistory(true);
    fetchPlayerHistory(selectedPlayer, statCategory, 12)
      .then((data) => setHistory(data))
      .catch(() => setHistory(null))
      .finally(() => setIsLoadingHistory(false));
  }, [selectedPlayer, statCategory]);

  async function handleToggleFavorite(playerName) {
    const isFavorite = favorites.includes(playerName);
    setFavorites((current) =>
      isFavorite ? current.filter((name) => name !== playerName) : [...current, playerName]
    );
    try {
      if (isFavorite) {
        await removeFavorite(playerName);
        showToast(`Removed ${playerName} from favorites`);
      } else {
        await addFavorite(playerName);
        showToast(`Added ${playerName} to favorites`, "positive");
      }
    } catch {
      setFavorites((current) =>
        isFavorite ? [...current, playerName] : current.filter((name) => name !== playerName)
      );
      showToast("Couldn't update favorites - try again", "negative");
    }
  }

  async function handlePredict(event) {
    event.preventDefault();
    setErrorMessage("");
    setIsLoading(true);
    try {
      const payload = {
        player_name: selectedPlayer,
        line: parseFloat(line),
        stat_category: statCategory,
      };
      if (overOdds.trim() !== "") {
        payload.over_odds = parseInt(overOdds, 10);
      }
      if (underOdds.trim() !== "") {
        payload.under_odds = parseInt(underOdds, 10);
      }
      const data = await predictProp(payload);
      setResult(data);
    } catch (error) {
      setErrorMessage(error.message);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLogBet() {
    if (!result) return;
    setIsLoggingBet(true);
    try {
      const sideOdds = side === "over" ? overOdds : underOdds;
      await createBet({
        bet_type: "prop",
        player_name: result.player_name,
        stat_category: result.stat_category,
        selection: side,
        line: result.line,
        odds: parseInt(sideOdds, 10),
        stake: parseFloat(stake) || 1,
        model_probability: side === "over" ? result.probability_over : result.probability_under,
      });
      showToast(`Logged ${result.player_name} ${side} ${result.line} ${result.stat_category}`, "positive");
    } catch (error) {
      showToast(error.message || "Couldn't log bet - try again", "negative");
    } finally {
      setIsLoggingBet(false);
    }
  }

  const resultTeamMeta = result ? getTeamMeta(result.team) : null;
  const parsedLine = parseFloat(line);

  return (
    <div className="tab-content">
      <form className="prediction-form" onSubmit={handlePredict}>
        <label className="span-2">
          Player
          {isLoadingPlayers ? (
            <SkeletonLine height={38} />
          ) : (
            <PlayerSearch
              players={players}
              favorites={favorites}
              selectedPlayer={selectedPlayer}
              onSelect={setSelectedPlayer}
              onToggleFavorite={handleToggleFavorite}
            />
          )}
        </label>

        <label>
          Stat category
          <select value={statCategory} onChange={(e) => setStatCategory(e.target.value)}>
            {STAT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Prop line
          <input type="number" step="0.5" value={line} onChange={(e) => setLine(e.target.value)} />
        </label>

        <label>
          Your bet
          <div className="side-toggle" role="radiogroup" aria-label="Which side are you betting">
            <button
              type="button"
              role="radio"
              aria-checked={side === "over"}
              className={`side-toggle-button${side === "over" ? " side-toggle-button--active" : ""}`}
              onClick={() => setSide("over")}
            >
              Over
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={side === "under"}
              className={`side-toggle-button${side === "under" ? " side-toggle-button--active" : ""}`}
              onClick={() => setSide("under")}
            >
              Under
            </button>
          </div>
        </label>

        <label>
          Over odds (American)
          <input type="text" value={overOdds} onChange={(e) => setOverOdds(e.target.value)} placeholder="-110" />
        </label>

        <label>
          Under odds (American)
          <input type="text" value={underOdds} onChange={(e) => setUnderOdds(e.target.value)} placeholder="-110" />
        </label>

        <button type="submit" className="span-2" disabled={isLoading || !selectedPlayer}>
          {isLoading ? "Simulating..." : "Predict"}
        </button>
      </form>

      {isLoadingHistory && (
        <div className="result-card">
          <SkeletonLine width="35%" height={16} />
          <div style={{ height: 12 }} />
          <SkeletonLine height={140} />
        </div>
      )}

      {!isLoadingHistory && history && history.games.length > 0 && (
        <div className="result-card">
          <h4 className="trend-title">
            Last {history.games.length} games — {STAT_OPTIONS.find((o) => o.value === statCategory)?.label}
          </h4>
          <TrendChart
            games={history.games}
            color={getTeamMeta(players.find((p) => p.player_name === selectedPlayer)?.team).primary}
            line={Number.isFinite(parsedLine) ? parsedLine : null}
          />
        </div>
      )}

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {isLoading && !result && <SkeletonCard />}

      {result && (
        <div className="result-card" style={{ "--team-color": resultTeamMeta.primary }}>
          <div className="matchup-strip">
            <div className="matchup-side">
              <TeamLogo team={result.team} size={44} />
              <div>
                <h3>{result.player_name}</h3>
                <span className="muted">{result.team}</span>
              </div>
            </div>
            <span className="matchup-vs">vs</span>
            <div className="matchup-side matchup-side--opponent">
              <div>
                <span className="muted">{result.opponent_team}</span>
                {result.game_date && <span className="muted game-date">{result.game_date}</span>}
              </div>
              <TeamLogo team={result.opponent_team} size={44} />
            </div>
          </div>

          {result.availability && result.availability.minutes_trend <= -5 && (
            <p className="availability-chip">
              ⚠ Minutes trending down: {result.availability.recent_minutes_avg} min last 3 games vs{" "}
              {result.availability.baseline_minutes_avg} min average — role or health may be in flux.
            </p>
          )}

          <div className="stat-grid">
            <div>
              <span className="stat-label">Rolling average</span>
              <span className="stat-value">{result.rolling_average.toFixed(1)}</span>
            </div>
            <div>
              <span className="stat-label">Matchup-adjusted</span>
              <span className="stat-value">{result.matchup_adjusted_mean.toFixed(1)}</span>
            </div>
            <div>
              <span className="stat-label">Simulations run</span>
              <span className="stat-value">{result.num_simulations.toLocaleString()}</span>
            </div>
          </div>

          <ProbabilityBar
            label={`P(over ${result.line})`}
            probability={result.probability_over}
            tone="positive"
            emphasized={side === "over"}
            muted={side === "under"}
          />
          <ProbabilityBar
            label={`P(under ${result.line})`}
            probability={result.probability_under}
            tone="neutral"
            emphasized={side === "under"}
            muted={side === "over"}
          />

          {result.edge_over !== undefined && (
            <p className={`edge-line ${result.edge_over >= 0 ? "edge-positive" : "edge-negative"}`}>
              Edge on over: {(result.edge_over * 100).toFixed(1)}% (market implies{" "}
              {(result.market_implied_probability_over * 100).toFixed(1)}% at {result.over_odds})
            </p>
          )}
          {result.edge_under !== undefined && (
            <p className={`edge-line ${result.edge_under >= 0 ? "edge-positive" : "edge-negative"}`}>
              Edge on under: {(result.edge_under * 100).toFixed(1)}% (market implies{" "}
              {(result.market_implied_probability_under * 100).toFixed(1)}% at {result.under_odds})
            </p>
          )}

          <div className="log-bet-row">
            <label className="log-bet-stake">
              Stake
              <input type="number" step="0.5" value={stake} onChange={(e) => setStake(e.target.value)} />
            </label>
            <button type="button" className="log-bet-button" onClick={handleLogBet} disabled={isLoggingBet}>
              {isLoggingBet ? "Logging..." : `Log ${side} ${result.line} bet`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
