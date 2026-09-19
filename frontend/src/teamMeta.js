// Team identity: official logo (NBA's own CDN, by team id) plus each
// team's real brand colors. `primary` is chosen to read clearly on our
// dark background (the more saturated/lighter of a team's colors);
// `secondary` is the complementary color, used sparingly (chip text,
// gradient stop) since several teams' secondary is black or near-black.
const TEAMS = {
  "Atlanta Hawks": { id: 1610612737, abbreviation: "ATL", primary: "#E03A3E", secondary: "#C1D32F" },
  "Boston Celtics": { id: 1610612738, abbreviation: "BOS", primary: "#007A33", secondary: "#BA9653" },
  "Brooklyn Nets": { id: 1610612751, abbreviation: "BKN", primary: "#CCCCCC", secondary: "#000000" },
  "Charlotte Hornets": { id: 1610612766, abbreviation: "CHA", primary: "#00788C", secondary: "#1D1160" },
  "Chicago Bulls": { id: 1610612741, abbreviation: "CHI", primary: "#CE1141", secondary: "#000000" },
  "Cleveland Cavaliers": { id: 1610612739, abbreviation: "CLE", primary: "#FDBB30", secondary: "#860038" },
  "Dallas Mavericks": { id: 1610612742, abbreviation: "DAL", primary: "#00538C", secondary: "#B8C4CA" },
  "Denver Nuggets": { id: 1610612743, abbreviation: "DEN", primary: "#FEC524", secondary: "#0E2240" },
  "Detroit Pistons": { id: 1610612765, abbreviation: "DET", primary: "#1D42BA", secondary: "#C8102E" },
  "Golden State Warriors": { id: 1610612744, abbreviation: "GSW", primary: "#FFC72C", secondary: "#1D428A" },
  "Houston Rockets": { id: 1610612745, abbreviation: "HOU", primary: "#CE1141", secondary: "#C4CED4" },
  "Indiana Pacers": { id: 1610612754, abbreviation: "IND", primary: "#FDBB30", secondary: "#002D62" },
  "LA Clippers": { id: 1610612746, abbreviation: "LAC", primary: "#1D428A", secondary: "#C8102E" },
  "Los Angeles Lakers": { id: 1610612747, abbreviation: "LAL", primary: "#FDB927", secondary: "#552583" },
  "Memphis Grizzlies": { id: 1610612763, abbreviation: "MEM", primary: "#5D76A9", secondary: "#F5B112" },
  "Miami Heat": { id: 1610612748, abbreviation: "MIA", primary: "#F9A01B", secondary: "#98002E" },
  "Milwaukee Bucks": { id: 1610612749, abbreviation: "MIL", primary: "#00471B", secondary: "#EEE1C6" },
  "Minnesota Timberwolves": { id: 1610612750, abbreviation: "MIN", primary: "#78BE20", secondary: "#0C2340" },
  "New Orleans Pelicans": { id: 1610612740, abbreviation: "NOP", primary: "#C8102E", secondary: "#85714D" },
  "New York Knicks": { id: 1610612752, abbreviation: "NYK", primary: "#F58426", secondary: "#006BB6" },
  "Oklahoma City Thunder": { id: 1610612760, abbreviation: "OKC", primary: "#007AC1", secondary: "#EF3B24" },
  "Orlando Magic": { id: 1610612753, abbreviation: "ORL", primary: "#0077C0", secondary: "#C4CED4" },
  "Philadelphia 76ers": { id: 1610612755, abbreviation: "PHI", primary: "#006BB6", secondary: "#ED174C" },
  "Phoenix Suns": { id: 1610612756, abbreviation: "PHX", primary: "#E56020", secondary: "#1D1160" },
  "Portland Trail Blazers": { id: 1610612757, abbreviation: "POR", primary: "#E03A3E", secondary: "#000000" },
  "Sacramento Kings": { id: 1610612758, abbreviation: "SAC", primary: "#5A2D81", secondary: "#63727A" },
  "San Antonio Spurs": { id: 1610612759, abbreviation: "SAS", primary: "#C4CED4", secondary: "#000000" },
  "Toronto Raptors": { id: 1610612761, abbreviation: "TOR", primary: "#CE1141", secondary: "#B4975A" },
  "Utah Jazz": { id: 1610612762, abbreviation: "UTA", primary: "#F9A01B", secondary: "#002B5C" },
  "Washington Wizards": { id: 1610612764, abbreviation: "WAS", primary: "#E31837", secondary: "#002B5C" },
};

const FALLBACK = { id: null, abbreviation: "NBA", primary: "#4f8cff", secondary: "#9aa1ac" };

export function getTeamMeta(teamName) {
  return TEAMS[teamName] || FALLBACK;
}

export function getTeamLogoUrl(teamName) {
  const meta = getTeamMeta(teamName);
  return meta.id ? `https://cdn.nba.com/logos/nba/${meta.id}/global/L/logo.svg` : null;
}

// Picks black or white text over a team color so the fallback badge
// (used when the real logo image fails to load) stays legible for
// lighter brand colors like gold/silver, not just dark ones.
export function getReadableTextColor(hexColor) {
  const hex = hexColor.replace("#", "");
  const r = parseInt(hex.substring(0, 2), 16) / 255;
  const g = parseInt(hex.substring(2, 4), 16) / 255;
  const b = parseInt(hex.substring(4, 6), 16) / 255;
  const linear = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
  return luminance > 0.45 ? "#14161b" : "#ffffff";
}

export default TEAMS;
