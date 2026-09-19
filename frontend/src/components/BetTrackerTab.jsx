import { useEffect, useMemo, useState } from "react";
import { fetchBets, createBet, settleBet, deleteBet } from "../api";
import { SkeletonLine, SkeletonStatGrid } from "./Skeleton";
import { useToast } from "./ToastProvider";

const STAT_OPTIONS = ["points", "rebounds", "assists", "pra", "pa", "ra"];

const EMPTY_FORM = {
  bet_type: "prop",
  player_name: "",
  team_a: "",
  team_b: "",
  stat_category: "points",
  selection: "over",
  line: "",
  odds: "-110",
  stake: "10",
  model_probability: "",
  notes: "",
};

const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "stat", label: "Stat category" },
];

const STATUS_FILTERS = ["all", "pending", "won", "lost", "push"];

export default function BetTrackerTab() {
  const showToast = useToast();
  const [bets, setBets] = useState([]);
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  function refresh() {
    fetchBets()
      .then((data) => {
        setBets(data.bets);
        setSummary(data.summary);
      })
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }

  useEffect(refresh, []);

  const visibleBets = useMemo(() => {
    let filtered = statusFilter === "all" ? bets : bets.filter((bet) => bet.status === statusFilter);
    filtered = [...filtered];
    if (sortBy === "newest") {
      filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortBy === "oldest") {
      filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    } else if (sortBy === "stat") {
      filtered.sort((a, b) => (a.stat_category || a.bet_type).localeCompare(b.stat_category || b.bet_type));
    }
    return filtered;
  }, [bets, statusFilter, sortBy]);

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMessage("");
    try {
      const payload = {
        bet_type: form.bet_type,
        selection: form.selection,
        odds: parseInt(form.odds, 10),
        stake: parseFloat(form.stake) || 1,
        notes: form.notes || null,
      };
      if (form.bet_type === "prop") {
        payload.player_name = form.player_name;
        payload.stat_category = form.stat_category;
        payload.line = parseFloat(form.line);
      } else {
        payload.team_a = form.team_a;
        payload.team_b = form.team_b;
        if (form.line) payload.line = parseFloat(form.line);
      }
      if (form.model_probability) {
        payload.model_probability = parseFloat(form.model_probability) / 100;
      }
      await createBet(payload);
      setForm(EMPTY_FORM);
      showToast("Bet logged", "positive");
      refresh();
    } catch (error) {
      setErrorMessage(error.message);
      showToast("Couldn't log bet - try again", "negative");
    }
  }

  async function handleSettle(betId, status) {
    try {
      await settleBet(betId, { status });
      showToast(`Bet marked ${status}`, status === "won" ? "positive" : status === "lost" ? "negative" : "default");
      refresh();
    } catch (error) {
      setErrorMessage(error.message);
      showToast("Couldn't settle bet - try again", "negative");
    }
  }

  async function handleDelete(betId) {
    try {
      await deleteBet(betId);
      showToast("Bet deleted");
      refresh();
    } catch (error) {
      setErrorMessage(error.message);
      showToast("Couldn't delete bet - try again", "negative");
    }
  }

  return (
    <div className="tab-content">
      <form className="prediction-form" onSubmit={handleSubmit}>
        <label>
          Bet type
          <select value={form.bet_type} onChange={(e) => setForm({ ...form, bet_type: e.target.value })}>
            <option value="prop">Player prop</option>
            <option value="moneyline">Moneyline</option>
            <option value="total">Total</option>
          </select>
        </label>

        {form.bet_type === "prop" ? (
          <>
            <label>
              Player
              <input
                type="text"
                value={form.player_name}
                onChange={(e) => setForm({ ...form, player_name: e.target.value })}
                placeholder="Player name"
                required
              />
            </label>
            <label>
              Stat category
              <select value={form.stat_category} onChange={(e) => setForm({ ...form, stat_category: e.target.value })}>
                {STAT_OPTIONS.map((stat) => (
                  <option key={stat} value={stat}>
                    {stat}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Selection
              <select value={form.selection} onChange={(e) => setForm({ ...form, selection: e.target.value })}>
                <option value="over">Over</option>
                <option value="under">Under</option>
              </select>
            </label>
            <label>
              Line
              <input
                type="number"
                step="0.5"
                value={form.line}
                onChange={(e) => setForm({ ...form, line: e.target.value })}
                required
              />
            </label>
          </>
        ) : (
          <>
            <label>
              Team A
              <input type="text" value={form.team_a} onChange={(e) => setForm({ ...form, team_a: e.target.value })} required />
            </label>
            <label>
              Team B
              <input type="text" value={form.team_b} onChange={(e) => setForm({ ...form, team_b: e.target.value })} required />
            </label>
            <label>
              Selection
              <input
                type="text"
                value={form.selection}
                onChange={(e) => setForm({ ...form, selection: e.target.value })}
                placeholder="Team name, or 'over'/'under'"
                required
              />
            </label>
            {form.bet_type === "total" && (
              <label>
                Line
                <input type="number" step="0.5" value={form.line} onChange={(e) => setForm({ ...form, line: e.target.value })} />
              </label>
            )}
          </>
        )}

        <label>
          Odds (American)
          <input type="text" value={form.odds} onChange={(e) => setForm({ ...form, odds: e.target.value })} required />
        </label>
        <label>
          Stake (units)
          <input type="number" step="0.5" value={form.stake} onChange={(e) => setForm({ ...form, stake: e.target.value })} />
        </label>
        <label>
          Model probability % (optional)
          <input
            type="number"
            step="0.1"
            value={form.model_probability}
            onChange={(e) => setForm({ ...form, model_probability: e.target.value })}
            placeholder="from the prediction tab"
          />
        </label>
        <label className="span-2">
          Notes (optional)
          <input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </label>

        <button type="submit" className="span-2">
          Log bet
        </button>
      </form>

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {isLoading && (
        <div className="result-card">
          <SkeletonLine width="30%" height={18} />
          <div style={{ height: 14 }} />
          <SkeletonStatGrid />
        </div>
      )}

      {!isLoading && summary && (
        <div className="result-card">
          <h3>Track record</h3>
          <div className="stat-grid">
            <div>
              <span className="stat-label">Record</span>
              <span className="stat-value">{summary.record}</span>
            </div>
            <div>
              <span className="stat-label">Profit (units)</span>
              <span className={`stat-value ${summary.total_profit_units >= 0 ? "edge-positive" : "edge-negative"}`}>
                {summary.total_profit_units >= 0 ? "+" : ""}
                {summary.total_profit_units}
              </span>
            </div>
            <div>
              <span className="stat-label">ROI</span>
              <span className={`stat-value ${summary.roi_percent >= 0 ? "edge-positive" : "edge-negative"}`}>
                {summary.roi_percent >= 0 ? "+" : ""}
                {summary.roi_percent}%
              </span>
            </div>
          </div>
          {summary.pending > 0 && <p className="muted">{summary.pending} bet(s) still pending settlement.</p>}
        </div>
      )}

      {!isLoading && bets.length > 0 && (
        <>
          <div className="bet-list-controls">
            <div className="status-filter-group" role="group" aria-label="Filter by status">
              {STATUS_FILTERS.map((status) => (
                <button
                  key={status}
                  type="button"
                  className={`pill-button${statusFilter === status ? " pill-button--active" : ""}`}
                  onClick={() => setStatusFilter(status)}
                  aria-pressed={statusFilter === status}
                >
                  {status === "all" ? "All" : status}
                </button>
              ))}
            </div>
            <label className="sort-select">
              Sort
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort bets">
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="result-card bet-list">
            {visibleBets.length === 0 ? (
              <p className="muted">No bets match this filter.</p>
            ) : (
              visibleBets.map((bet) => (
                <div key={bet.id} className={`bet-row bet-row--${bet.status}`}>
                  <div className="bet-row-main">
                    <span className="bet-row-title">
                      {bet.bet_type === "prop"
                        ? `${bet.player_name} ${bet.selection} ${bet.line} ${bet.stat_category}`
                        : `${bet.team_a} vs ${bet.team_b} — ${bet.selection}${bet.line ? ` ${bet.line}` : ""}`}
                    </span>
                    <span className="muted">
                      {bet.odds > 0 ? `+${bet.odds}` : bet.odds} · {bet.stake}u
                      {bet.model_probability != null && ` · model ${(bet.model_probability * 100).toFixed(0)}%`}
                    </span>
                  </div>
                  <div className="bet-row-actions">
                    {bet.status === "pending" ? (
                      <>
                        <button type="button" className="pill-button pill-button--won" onClick={() => handleSettle(bet.id, "won")}>
                          Won
                        </button>
                        <button type="button" className="pill-button pill-button--lost" onClick={() => handleSettle(bet.id, "lost")}>
                          Lost
                        </button>
                        <button type="button" className="pill-button" onClick={() => handleSettle(bet.id, "push")}>
                          Push
                        </button>
                      </>
                    ) : (
                      <span className={`bet-status bet-status--${bet.status}`}>
                        {bet.status} ({bet.profit >= 0 ? "+" : ""}
                        {bet.profit}u)
                      </span>
                    )}
                    <button
                      type="button"
                      className="pill-button pill-button--delete"
                      aria-label="Delete bet"
                      onClick={() => handleDelete(bet.id)}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {!isLoading && bets.length === 0 && (
        <p className="muted">No bets logged yet. Log one above to start tracking your real record against the model.</p>
      )}
    </div>
  );
}
