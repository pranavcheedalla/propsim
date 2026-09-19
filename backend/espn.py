"""
Live data from ESPN's public site API: no key required, but it's an
unofficial API (not documented/guaranteed by ESPN), so every call here
degrades to an empty result on any failure rather than raising - this
is a nice-to-have enrichment layer, not something predictions depend on.

Two things it gives us that nba_api doesn't:
  - Real sportsbook lines (moneyline/spread/total) for a matchup, via
    ESPN's "pickcenter" widget data.
  - Current injury report per team.

Genuine player PROP odds (a specific point/rebound/assist line with
odds) aren't available from any free/no-key source - that's licensed
data every provider charges for - so player props stay manual entry.
"""

import time
import urllib.request
import json
from datetime import datetime, timedelta

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
CACHE_TTL_SECONDS = 15 * 60
_cache = {}

ESPN_TEAM_IDS = {
    "Atlanta Hawks": 1, "Boston Celtics": 2, "Brooklyn Nets": 17, "Charlotte Hornets": 30,
    "Chicago Bulls": 4, "Cleveland Cavaliers": 5, "Dallas Mavericks": 6, "Denver Nuggets": 7,
    "Detroit Pistons": 8, "Golden State Warriors": 9, "Houston Rockets": 10, "Indiana Pacers": 11,
    "LA Clippers": 12, "Los Angeles Lakers": 13, "Memphis Grizzlies": 29, "Miami Heat": 14,
    "Milwaukee Bucks": 15, "Minnesota Timberwolves": 16, "New Orleans Pelicans": 3,
    "New York Knicks": 18, "Oklahoma City Thunder": 25, "Orlando Magic": 19,
    "Philadelphia 76ers": 20, "Phoenix Suns": 21, "Portland Trail Blazers": 22,
    "Sacramento Kings": 23, "San Antonio Spurs": 24, "Toronto Raptors": 28, "Utah Jazz": 26,
    "Washington Wizards": 27,
}


def _fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read())


def _cached(key, loader):
    cached_entry = _cache.get(key)
    if cached_entry and time.time() - cached_entry["fetched_at"] < CACHE_TTL_SECONDS:
        return cached_entry["value"]
    try:
        value = loader()
    except Exception:
        value = cached_entry["value"] if cached_entry else None
    _cache[key] = {"value": value, "fetched_at": time.time()}
    return value


def _find_event_id(team_a, team_b, around_date=None):
    team_a_id = ESPN_TEAM_IDS.get(team_a)
    team_b_id = ESPN_TEAM_IDS.get(team_b)
    if team_a_id is None or team_b_id is None:
        return None

    search_dates = [around_date] if around_date else []
    base_date = datetime.strptime(around_date, "%Y-%m-%d") if around_date else datetime.utcnow()
    search_dates += [(base_date + timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(-1, 8)]

    for date_string in dict.fromkeys(search_dates):
        date_param = date_string.replace("-", "")
        try:
            scoreboard = _fetch_json(f"{BASE_URL}/scoreboard?dates={date_param}")
        except Exception:
            continue
        for event in scoreboard.get("events", []):
            competitors = event.get("competitions", [{}])[0].get("competitors", [])
            team_ids = {int(c["team"]["id"]) for c in competitors if "team" in c}
            if {team_a_id, team_b_id} <= team_ids:
                return event["id"]
    return None


def get_live_game_odds(team_a, team_b, game_date=None):
    """Real moneyline/spread/total for team_a vs team_b, or None if ESPN has no market posted yet (common far out from game day, e.g. during the offseason)."""
    def loader():
        event_id = _find_event_id(team_a, team_b, game_date)
        if event_id is None:
            return None
        summary = _fetch_json(f"{BASE_URL}/summary?event={event_id}")
        pickcenter = summary.get("pickcenter") or []
        if not pickcenter:
            return None
        market = pickcenter[0]
        home_is_team_a = ESPN_TEAM_IDS.get(team_a) == int(
            market.get("homeTeamOdds", {}).get("teamId", -1)
        )
        team_a_odds = market.get("homeTeamOdds" if home_is_team_a else "awayTeamOdds", {})
        team_b_odds = market.get("awayTeamOdds" if home_is_team_a else "homeTeamOdds", {})
        return {
            "provider": market.get("provider", {}).get("name"),
            "total_line": market.get("overUnder"),
            "team_a_moneyline_odds": team_a_odds.get("moneyLine"),
            "team_b_moneyline_odds": team_b_odds.get("moneyLine"),
        }

    return _cached(f"odds:{team_a}:{team_b}", loader)


def get_team_injuries(team_name):
    """Current injury report for a team: list of {player_name, status, detail}. Empty list if ESPN has nothing (also true for a healthy team)."""
    def loader():
        team_id = ESPN_TEAM_IDS.get(team_name)
        if team_id is None:
            return []
        schedule = _fetch_json(f"{BASE_URL}/teams/{team_id}/schedule")
        events = schedule.get("events", [])
        if not events:
            return []
        now = datetime.utcnow()
        events_sorted = sorted(
            events, key=lambda e: abs((datetime.strptime(e["date"][:10], "%Y-%m-%d") - now).days)
        )
        for event in events_sorted[:1]:
            summary = _fetch_json(f"{BASE_URL}/summary?event={event['id']}")
            for team_injuries in summary.get("injuries", []):
                if team_injuries.get("team", {}).get("displayName") == team_name:
                    return [
                        {
                            "player_name": entry.get("athlete", {}).get("displayName"),
                            "status": entry.get("status"),
                        }
                        for entry in team_injuries.get("injuries", [])
                    ]
        return []

    return _cached(f"injuries:{team_name}", loader) or []
