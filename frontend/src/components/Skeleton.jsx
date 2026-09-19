export function SkeletonLine({ width = "100%", height = 14 }) {
  return <div className="skeleton" style={{ width, height }} />;
}

export function SkeletonStatGrid() {
  return (
    <div className="stat-grid">
      {[0, 1, 2].map((i) => (
        <div key={i}>
          <SkeletonLine width="60%" height={10} />
          <SkeletonLine width="45%" height={18} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 4 }) {
  return (
    <div className="skeleton-table">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonLine key={i} height={16} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="result-card">
      <SkeletonLine width="40%" height={18} />
      <div style={{ height: 14 }} />
      <SkeletonStatGrid />
      <SkeletonLine height={10} />
      <div style={{ height: 10 }} />
      <SkeletonLine height={10} />
    </div>
  );
}
