export default function ProbabilityBar({ label, probability, tone = "default", color, emphasized = false, muted = false }) {
  const percent = Math.max(0, Math.min(100, probability * 100));
  const stateClass = emphasized ? " probability-bar--emphasized" : muted ? " probability-bar--muted" : "";
  return (
    <div className={`probability-bar${stateClass}`}>
      <div className="probability-bar-header">
        <span>
          {label}
          {emphasized && <span className="your-bet-badge">Your bet</span>}
        </span>
        <span className="probability-bar-value">{percent.toFixed(1)}%</span>
      </div>
      <div className="probability-bar-track">
        <div
          className={`probability-bar-fill${color ? "" : ` probability-bar-fill--${tone}`}`}
          style={{ width: `${percent}%`, background: color }}
        />
      </div>
    </div>
  );
}
