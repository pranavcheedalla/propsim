import { useEffect, useState } from "react";
import { fetchBacktestSummary, fetchSeasons } from "../api";
import { SkeletonLine, SkeletonStatGrid, SkeletonTable } from "./Skeleton";

const STAT_OPTIONS = [
  { value: "points", label: "Points" },
  { value: "rebounds", label: "Rebounds" },
  { value: "assists", label: "Assists" },
  { value: "pra", label: "PRA" },
  { value: "pa", label: "PA" },
  { value: "ra", label: "RA" },
];

export default function BacktestTab() {
  const [seasons, setSeasons] = useState([]);
  const [statCategory, setStatCategory] = useState("points");
  const [season, setSeason] = useState("all");
  const [summary, setSummary] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchSeasons()
      .then((data) => setSeasons(data.seasons))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setIsLoading(true);
    fetchBacktestSummary(statCategory, season)
      .then((data) => setSummary(data))
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false));
  }, [statCategory, season]);

  return (
    <div className="tab-content">
      <div className="prediction-form backtest-controls">
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
          Season
          <select value={season} onChange={(e) => setSeason(e.target.value)}>
            <option value="all">All seasons combined</option>
            {seasons.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && (
        <div className="result-card">
          <SkeletonLine width="45%" height={18} />
          <div style={{ height: 8 }} />
          <SkeletonLine width="80%" height={12} />
          <div style={{ height: 16 }} />
          <SkeletonStatGrid />
          <div style={{ height: 8 }} />
          <SkeletonTable rows={4} />
        </div>
      )}

      {!isLoading && errorMessage && (
        <p className="error-message">{errorMessage}</p>
      )}

      {!isLoading && summary && (
        <div className="result-card">
          <h3>Backtest summary</h3>
          <p className="muted">
            Model graded against {summary.total_predictions.toLocaleString()} historical player-games, with the
            prop line set at each player's own pre-game rolling average.
          </p>

          <div className="stat-grid">
            <div>
              <span className="stat-label">Total predictions</span>
              <span className="stat-value">{summary.total_predictions.toLocaleString()}</span>
            </div>
            <div>
              <span className="stat-label">Hit rate</span>
              <span className="stat-value">{(summary.hit_rate * 100).toFixed(1)}%</span>
            </div>
            <div>
              <span className="stat-label">Flat-bet ROI at -110</span>
              <span className={`stat-value ${summary.roi_percent >= 0 ? "edge-positive" : "edge-negative"}`}>
                {summary.roi_percent >= 0 ? "+" : ""}
                {summary.roi_percent.toFixed(1)}%
              </span>
            </div>
          </div>

          {summary.by_season && summary.by_season.length > 1 && (
            <>
              <h4>By season</h4>
              <p className="muted">Is the edge consistent, or did one good season carry the average?</p>
              <table className="calibration-table">
                <thead>
                  <tr>
                    <th>Season</th>
                    <th>Hit rate</th>
                    <th>Predictions</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_season.map((row) => (
                    <tr key={row.season}>
                      <td>{row.season}</td>
                      <td>{(row.hit_rate * 100).toFixed(1)}%</td>
                      <td>{row.total_predictions.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h4>Calibration</h4>
          <p className="muted">When the model says it's X% confident, how often is it actually right?</p>
          <table className="calibration-table">
            <thead>
              <tr>
                <th>Model confidence</th>
                <th>Actual hit rate</th>
                <th>Predictions</th>
              </tr>
            </thead>
            <tbody>
              {summary.calibration.map((bucket) => (
                <tr key={bucket.confidence_low}>
                  <td>
                    {(bucket.confidence_low * 100).toFixed(0)}%-{(bucket.confidence_high * 100).toFixed(0)}%
                  </td>
                  <td>{(bucket.actual_hit_rate * 100).toFixed(1)}%</td>
                  <td>{bucket.num_predictions.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
