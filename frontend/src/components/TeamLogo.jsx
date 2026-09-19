import { useState } from "react";
import { getTeamLogoUrl, getTeamMeta, getReadableTextColor } from "../teamMeta";

export default function TeamLogo({ team, size = 32 }) {
  const [failed, setFailed] = useState(false);
  const meta = getTeamMeta(team);
  const logoUrl = getTeamLogoUrl(team);

  if (!logoUrl || failed) {
    return (
      <span
        className="team-badge"
        style={{
          width: size,
          height: size,
          background: meta.primary,
          color: getReadableTextColor(meta.primary),
          fontSize: size * 0.34,
        }}
        title={team}
      >
        {meta.abbreviation}
      </span>
    );
  }

  return (
    <img
      className="team-logo"
      src={logoUrl}
      alt={team}
      width={size}
      height={size}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
