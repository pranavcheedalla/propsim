import { useState } from "react";

const WIDTH = 640;
const HEIGHT = 160;
const PADDING_LEFT = 28;
const PADDING_BOTTOM = 22;
const PADDING_TOP = 12;

export default function TrendChart({ games, color, line }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!games || games.length === 0) {
    return <p className="muted">Not enough recent games to chart.</p>;
  }

  const values = games.map((game) => game.value);
  const maxValue = Math.max(...values, line || 0) * 1.15 || 1;
  const plotWidth = WIDTH - PADDING_LEFT - 8;
  const plotHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const barGap = 6;
  const barWidth = Math.max((plotWidth - barGap * (games.length - 1)) / games.length, 4);

  function xForIndex(index) {
    return PADDING_LEFT + index * (barWidth + barGap);
  }

  function yForValue(value) {
    return PADDING_TOP + plotHeight * (1 - value / maxValue);
  }

  const hovered = hoverIndex !== null ? games[hoverIndex] : null;

  return (
    <div className="trend-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} width="100%" height={HEIGHT} role="img" aria-label="Recent game trend">
        <line
          x1={PADDING_LEFT}
          y1={HEIGHT - PADDING_BOTTOM}
          x2={WIDTH}
          y2={HEIGHT - PADDING_BOTTOM}
          className="trend-chart-axis"
        />
        {line != null && (
          <>
            <line
              x1={PADDING_LEFT}
              x2={WIDTH}
              y1={yForValue(line)}
              y2={yForValue(line)}
              className="trend-chart-line-marker"
              strokeDasharray="4 4"
            />
            <text x={WIDTH - 4} y={yForValue(line) - 4} textAnchor="end" className="trend-chart-line-label">
              line {line}
            </text>
          </>
        )}
        {games.map((game, index) => {
          const barHeight = plotHeight * (game.value / maxValue);
          return (
            <rect
              key={`${game.game_date}-${index}`}
              x={xForIndex(index)}
              y={HEIGHT - PADDING_BOTTOM - barHeight}
              width={barWidth}
              height={Math.max(barHeight, 2)}
              rx={3}
              fill={hoverIndex === index ? color : `${color}cc`}
              onMouseEnter={() => setHoverIndex(index)}
              onMouseLeave={() => setHoverIndex(null)}
            />
          );
        })}
        {games.map((game, index) => {
          if (index !== 0 && index !== games.length - 1 && games.length > 6) return null;
          const label = game.game_date.slice(5).replace("-", "/");
          return (
            <text
              key={`label-${index}`}
              x={xForIndex(index) + barWidth / 2}
              y={HEIGHT - 6}
              textAnchor="middle"
              className="trend-chart-axis-label"
            >
              {label}
            </text>
          );
        })}
      </svg>
      <div className="trend-chart-tooltip" style={{ visibility: hovered ? "visible" : "hidden" }}>
        {hovered && (
          <>
            <strong>{hovered.value}</strong> on {hovered.game_date} {hovered.is_home ? "vs" : "@"}{" "}
            {hovered.opponent_team} <span className="muted">({hovered.minutes.toFixed(0)} min)</span>
          </>
        )}
      </div>
    </div>
  );
}
