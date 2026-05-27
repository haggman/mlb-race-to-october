"""MLB Stats API tools for the Front Office Analyst agent.

A hand-curated set of FunctionTool wrappers around the public MLB Stats API
(https://statsapi.mlb.com). No auth required, just HTTPS GET.

The tools here handle CURRENT-SEASON state — what BigQuery's historical
tables can't answer. The agent should reach for these when a question is
about this season, this week, today, or right now.

Adapted from prior lab tooling; preseason auto-fallback preserved so the
lab works correctly January-March when the current season hasn't started
and the most recent complete season is the prior year.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

MLB_API_BASE = "https://statsapi.mlb.com"


# --- Internal helpers --------------------------------------------------------

def _get_season_info() -> Dict[str, Any]:
    """Determine current effective season and whether we're in preseason.

    MLB regular season starts late March / early April. During Jan-Mar we
    default to the prior year's stats so questions about "this season" still
    get answered with the most recent complete data.
    """
    now = datetime.now()
    current_year = now.year
    is_preseason = now.month < 4
    effective_season = current_year - 1 if is_preseason else current_year

    return {
        "current_year": current_year,
        "effective_season": effective_season,
        "is_preseason": is_preseason,
        "season_note": (
            f"Showing {effective_season} season data (preseason {current_year})"
            if is_preseason else None
        ),
    }


def _make_api_call(endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an MLB Stats API call with timeout and graceful error handling.

    Returns either the parsed JSON response or {"error": "..."}. The agent
    treats {"error": ...} as a signal to report honestly and try a different
    approach rather than fabricate data.
    """
    try:
        response = requests.get(
            f"{MLB_API_BASE}{endpoint}",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed for {endpoint}: {e}")
        return {"error": f"API call failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error for {endpoint}: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


# --- Player lookup -----------------------------------------------------------

def search_player(name: str, only_active: bool = True) -> Dict[str, Any]:
    """Look up an MLB player by name to get their integer player ID and current team.

    Call this FIRST whenever a user mentions a player by name and you need
    current-season data — most other player tools take an integer player_id
    that you don't have until you do this lookup. (For historical analysis
    against BigQuery's `people` table, use a SQL lookup on name_first /
    name_last instead — the MLB API's integer IDs don't match Lahman's
    string playerIDs.)

    Args:
        name: Player name to search for (e.g., "Aaron Judge").
        only_active: If True (default), filter to currently active players.

    Returns:
        Dict with `found` count and a `players` list. Each player includes
        `id` (integer, use this for other API calls), `full_name`, current
        `team` and `team_id`, `position`, plus biographical metadata.
    """
    data = _make_api_call(
        "/api/v1/people/search",
        params={"names": name},
    )

    if "error" in data:
        return data

    players = []
    for person in data.get("people", []):
        if only_active and not person.get("active", False):
            continue

        players.append({
            "id": person["id"],
            "full_name": person.get("fullName"),
            "position": person.get("primaryPosition", {}).get("name", "Unknown"),
            "position_abbr": person.get("primaryPosition", {}).get("abbreviation", ""),
            "team": person.get("currentTeam", {}).get("name", "Free Agent"),
            "team_id": person.get("currentTeam", {}).get("id"),
            "jersey_number": person.get("primaryNumber", ""),
            "birth_date": person.get("birthDate"),
            "age": person.get("currentAge"),
            "height": person.get("height"),
            "weight": person.get("weight"),
            "bat_side": person.get("batSide", {}).get("description", "Unknown"),
            "throw_hand": person.get("pitchHand", {}).get("description", "Unknown"),
            "nickname": person.get("nickName"),
            "is_player": person.get("isPlayer", False),
            "is_verified": person.get("isVerified", False),
            "mlb_debut": person.get("mlbDebutDate"),
        })

    return {
        "found": len(players),
        "players": players,
        "search_term": name,
        "active_only": only_active,
    }


# --- Team lookup -------------------------------------------------------------

def search_team(name: str) -> Dict[str, Any]:
    """Look up an MLB team by name, city, or abbreviation to get its integer team ID.

    Call this when a user mentions a team and you need current-season data
    via the MLB Stats API — `get_team_info` and `get_team_roster` need the
    integer team_id this returns.

    Args:
        name: Team identifier — "Yankees", "New York", "NYY", "Dodgers", etc.

    Returns:
        Dict with `found` count and a `teams` list. Each team includes `id`
        (integer, use this for other API calls), `name`, `abbreviation`,
        `league`, `division`, and which field matched the search.
    """
    data = _make_api_call(
        "/api/v1/teams",
        params={"sportId": 1, "activeStatus": "ACTIVE"},
    )

    if "error" in data:
        return data

    search_term = name.strip().lower()
    matches = []

    for team in data.get("teams", []):
        match_field = None
        fields = {
            "name": team.get("name", ""),
            "team_name": team.get("teamName", ""),
            "abbreviation": team.get("abbreviation", ""),
            "location": team.get("locationName", ""),
            "short_name": team.get("shortName", ""),
            "franchise_name": team.get("franchiseName", ""),
        }

        for field_name, field_value in fields.items():
            if search_term in field_value.lower():
                match_field = field_name
                break

        if match_field:
            matches.append({
                "id": team["id"],
                "name": team["name"],
                "team_name": team["teamName"],
                "abbreviation": team["abbreviation"],
                "location": team["locationName"],
                "short_name": team.get("shortName", ""),
                "franchise_name": team.get("franchiseName", ""),
                "first_year": team.get("firstYearOfPlay", ""),
                "venue": team.get("venue", {}).get("name", ""),
                "league": team.get("league", {}).get("name", ""),
                "division": team.get("division", {}).get("name", ""),
                "match_field": match_field,
            })

    return {
        "found": len(matches),
        "teams": matches,
        "search_term": name,
    }


# --- Player stats ------------------------------------------------------------

def get_player_stats(
    player_id: int,
    season: Optional[int] = None,
    include: Optional[List[str]] = None,
    groups: Optional[List[str]] = None,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """Get a player's current-season, career, or recent-game stats via the live MLB API.

    Use this for "how is player X doing this season" / "what are X's
    current numbers" questions. For historical or cross-season analysis
    (e.g., "X's stats in 2018", "compare X's career to Y's"), use BigQuery
    against the `batting` and `pitching` tables instead — BigQuery has the
    full historical depth and is faster for analytical queries.

    Auto-falls-back to the prior year during preseason (Jan-Mar) when the
    current season's data isn't available yet; this is surfaced in the
    response as `is_preseason` and a `season_note`.

    Args:
        player_id: MLB integer player ID (get this from `search_player`).
        season: Optional four-digit year. OMIT this for current/this-season
            data — the tool fills in the current season automatically (and
            falls back to the most recent completed season in the offseason).
            Only pass it when the user explicitly names a past year. Do not
            infer or guess the current year yourself.
        include: Which stat windows to return. Subset of ["season", "career",
            "recent"]. Defaults to all three.
        groups: Which stat groups. Subset of ["hitting", "pitching"].
            Defaults to both.
        include_raw: If True, include the raw API payload for debugging.
            Off by default to keep the response compact for the agent.

    Returns:
        Dict with `full_name`, `team`, `position`, `season`, plus nested
        `stats` keyed by stat window (season/career/recent) and group
        (hitting/pitching). Hitting summary: avg, ops, home_runs, rbi,
        hits, stolen_bases, games. Pitching summary: era, whip, wins,
        losses, saves, strikeouts, innings.
    """
    if include is None:
        include = ["season", "career", "recent"]
    if groups is None:
        groups = ["hitting", "pitching"]

    season_info = _get_season_info()
    query_season = season if season is not None else season_info["effective_season"]

    # Build hydration string for stats sub-resources
    hydrations = ["currentTeam"]
    stat_types = []
    if "season" in include:
        stat_types.append("season")
    if "career" in include:
        stat_types.append("career")
    if "recent" in include:
        stat_types.append("last10Games")

    if stat_types:
        hydrations.append(
            f"stats(group=[{','.join(groups)}],type=[{','.join(stat_types)}],season={query_season})"
        )

    data = _make_api_call(
        f"/api/v1/people/{player_id}",
        params={"hydrate": ",".join(hydrations)},
    )

    if "error" in data:
        return data
    if not data.get("people"):
        return {"error": f"Player with ID {player_id} not found"}

    player = data["people"][0]

    result = {
        "player_id": player_id,
        "full_name": player.get("fullName", "Unknown"),
        "team": player.get("currentTeam", {}).get("name", "Free Agent"),
        "team_id": player.get("currentTeam", {}).get("id"),
        "position": player.get("primaryPosition", {}).get("abbreviation", ""),
        "position_full": player.get("primaryPosition", {}).get("name", ""),
        "jersey_number": player.get("primaryNumber", ""),
        "season": query_season,
        "is_preseason": season_info["is_preseason"],
        "stats": {"season": {}, "career": {}, "recent": {}},
        "stat_source": "MLB StatsAPI",
    }

    if season_info["is_preseason"] and season is None:
        result["season_note"] = (
            f"Showing {query_season} season stats "
            f"(the {season_info['current_year']} season hasn't started yet)"
        )

    def _parse_stat_block(stat_group: Dict[str, Any]) -> None:
        stat_type = stat_group.get("type", {}).get("displayName", "").lower()
        group_name = stat_group.get("group", {}).get("displayName", "").lower()
        splits = stat_group.get("splits", [])

        if not splits or stat_type not in include or group_name not in groups:
            return

        stats = splits[0].get("stat", {})
        summary: Dict[str, Any] = {}

        if group_name == "hitting":
            summary = {
                "avg": stats.get("avg", ".000"),
                "ops": stats.get("ops", ".000"),
                "home_runs": stats.get("homeRuns", 0),
                "rbi": stats.get("rbi", 0),
                "hits": stats.get("hits", 0),
                "stolen_bases": stats.get("stolenBases", 0),
                "games": stats.get("gamesPlayed", 0),
            }
        elif group_name == "pitching":
            summary = {
                "era": stats.get("era", "0.00"),
                "whip": stats.get("whip", "0.00"),
                "wins": stats.get("wins", 0),
                "losses": stats.get("losses", 0),
                "saves": stats.get("saves", 0),
                "strikeouts": stats.get("strikeOuts", 0),
                "innings": stats.get("inningsPitched", "0.0"),
            }

        if summary:
            result["stats"][stat_type][group_name] = summary

    for stat_group in player.get("stats", []):
        _parse_stat_block(stat_group)

    if include_raw:
        result["raw"] = data

    return result


# --- Team data ---------------------------------------------------------------

def get_team_info(team_id: int, season: Optional[int] = None) -> Dict[str, Any]:
    """Get a team's current-season metadata, standings, recent form, and hitting stats.

    Use this for "where do the Yankees sit right now" / "how are the Phillies
    doing this season" / "what's our division rank" questions. Returns the
    team's record, division/league rank, last-10-games record, and team-level
    season hitting stats in one call.

    For BigQuery-historical team analysis (multi-season, cross-team, or
    franchise history), query the `teams` table directly instead — it has
    every team-season since 1871.

    Auto-falls-back to the prior year during preseason.

    Args:
        team_id: MLB integer team ID (get this from `search_team`).
        season: Optional four-digit year. OMIT this for current/this-season
            data — the tool fills in the current season automatically (and
            falls back to the most recent completed season in the offseason).
            Only pass it when the user explicitly names a past year. Do not
            infer or guess the current year yourself.

    Returns:
        Dict with team metadata (name, league, division, venue), `standings`
        (wins, losses, pct, division_rank, league_rank, games_back),
        `recent_form` (last_10_wins/losses/pct), and team `stats`
        (avg, home_runs, runs, hits, ops, games_played).
    """
    season_info = _get_season_info()
    query_season = season if season is not None else season_info["effective_season"]

    result: Dict[str, Any] = {
        "team_id": team_id,
        "season": query_season,
        "is_preseason": season_info["is_preseason"],
    }

    if season_info["is_preseason"] and season is None:
        result["season_note"] = (
            f"Showing {query_season} season stats "
            f"(the {season_info['current_year']} season hasn't started yet)"
        )

    # 1. Basic team metadata
    team_data = _make_api_call(f"/api/v1/teams/{team_id}")
    if "error" in team_data:
        return team_data
    if not team_data.get("teams"):
        return {"error": f"Team with ID {team_id} not found"}

    team = team_data["teams"][0]
    result.update({
        "name": team.get("name", "Unknown"),
        "team_name": team.get("teamName", ""),
        "abbreviation": team.get("abbreviation", ""),
        "location": team.get("locationName", ""),
        "league": team.get("league", {}).get("name", ""),
        "league_id": team.get("league", {}).get("id"),
        "division": team.get("division", {}).get("name", ""),
        "division_id": team.get("division", {}).get("id"),
        "venue": team.get("venue", {}).get("name", ""),
        "established": team.get("firstYearOfPlay", ""),
    })

    # 2. Standings + recent form
    standings_data = _make_api_call(
        "/api/v1/standings",
        params={
            "leagueId": team.get("league", {}).get("id"),
            "season": query_season,
            "standingsTypes": "regularSeason",
            "hydrate": "team",
        },
    )

    standings: Dict[str, Any] = {}
    recent_form: Dict[str, Any] = {}

    if "error" not in standings_data:
        for record in standings_data.get("records", []):
            for team_record in record.get("teamRecords", []):
                if team_record.get("team", {}).get("id") == team_id:
                    standings = {
                        "wins": team_record.get("wins", 0),
                        "losses": team_record.get("losses", 0),
                        "pct": team_record.get("winningPercentage", ".000"),
                        "division_rank": team_record.get("divisionRank", "?"),
                        "league_rank": team_record.get("leagueRank", "?"),
                        "games_back": team_record.get("gamesBack", "?"),
                    }
                    for split in team_record.get("records", {}).get("splitRecords", []):
                        if split.get("type") == "lastTen":
                            recent_form = {
                                "last_10_wins": split.get("wins", 0),
                                "last_10_losses": split.get("losses", 0),
                                "last_10_pct": split.get("pct", ".000"),
                            }
                    break

    result["standings"] = standings
    result["recent_form"] = recent_form

    # 3. Season hitting stats
    stat_data = _make_api_call(
        f"/api/v1/teams/{team_id}/stats",
        params={
            "stats": "season",
            "group": "hitting",
            "season": query_season,
        },
    )

    if "error" in stat_data:
        result["stats"] = {"error": "Could not fetch stats"}
    else:
        splits = stat_data.get("stats", [{}])[0].get("splits", [])
        if splits:
            stats = splits[0].get("stat", {})
            result["stats"] = {
                "avg": stats.get("avg", ".000"),
                "home_runs": stats.get("homeRuns", 0),
                "runs": stats.get("runs", 0),
                "hits": stats.get("hits", 0),
                "ops": stats.get("ops", ".000"),
                "games_played": stats.get("gamesPlayed", 0),
            }
        else:
            result["stats"] = {"note": f"No stats available for {query_season} season"}

    return result


def get_team_roster(team_id: int) -> Dict[str, Any]:
    """Get a team's current active roster, organized by position group.

    Use this for "who's on the Phillies right now" / "who's the starting
    pitcher tonight" / "show me the active roster" questions — anything
    where the current player list matters.

    Args:
        team_id: MLB integer team ID (get this from `search_team`).

    Returns:
        Dict with `team_id`, `total` count, and lists `pitchers`,
        `catchers`, `infielders`, `outfielders`, `designated_hitters`.
        Each player has `id`, `name`, `jersey`, and `position`. Players
        are sorted by jersey number within each group.
    """
    data = _make_api_call(f"/api/v1/teams/{team_id}/roster/active")

    if "error" in data:
        return data

    roster: Dict[str, Any] = {
        "team_id": team_id,
        "pitchers": [],
        "catchers": [],
        "infielders": [],
        "outfielders": [],
        "designated_hitters": [],
        "total": 0,
    }

    for player in data.get("roster", []):
        player_info = {
            "id": player["person"]["id"],
            "name": player["person"]["fullName"],
            "jersey": player.get("jerseyNumber", ""),
            "position": player["position"]["abbreviation"],
        }

        position_type = player["position"]["type"]
        if position_type == "Pitcher":
            roster["pitchers"].append(player_info)
        elif position_type == "Catcher":
            roster["catchers"].append(player_info)
        elif position_type == "Infielder":
            roster["infielders"].append(player_info)
        elif position_type == "Outfielder":
            roster["outfielders"].append(player_info)
        elif position_type == "Hitter":
            roster["designated_hitters"].append(player_info)
        elif player["position"]["abbreviation"] == "DH":
            roster["designated_hitters"].append(player_info)
        else:
            roster.setdefault("other", []).append(player_info)

    for key in ["pitchers", "catchers", "infielders", "outfielders", "designated_hitters"]:
        roster[key].sort(
            key=lambda x: int(x["jersey"]) if x["jersey"].isdigit() else 999
        )

    roster["total"] = len(data.get("roster", []))

    return roster


# --- League standings (TODO 2: implement this function) ---------------------

def get_standings(season: Optional[int] = None) -> Dict[str, Any]:
    """Get current MLB standings across all divisions, organized by league.

    Use this for "what are the AL East standings" / "show me the wild card
    race" — questions where the user wants to see multiple teams' records
    together. For a single team's standing, `get_team_info` returns the
    same data plus team metadata in one call.

    Auto-falls-back to the prior year during preseason.

    Args:
        season: Optional four-digit year. OMIT this for current/this-season
            standings — the tool fills in the current season automatically
            (and falls back to the most recent completed season in the
            offseason). Only pass it when the user explicitly names a past
            year. Do not infer or guess the current year yourself.

    Returns:
        Dict with `season`, `is_preseason`, and `divisions` (a list of
        dicts each with `league`, `division`, and `teams`). Each team
        entry has `team_id`, `name`, `wins`, `losses`, `pct`,
        `division_rank`, `league_rank`, and `games_back`.
    """
    season_info = _get_season_info()
    query_season = season if season is not None else season_info["effective_season"]

    result: Dict[str, Any] = {
        "season": query_season,
        "is_preseason": season_info["is_preseason"],
        "divisions": [],
    }

    if season_info["is_preseason"] and season is None:
        result["season_note"] = (
            f"Showing {query_season} standings "
            f"(the {season_info['current_year']} season hasn't started yet)"
        )

    # TODO 2: Fetch and parse the MLB standings.
    #
    # Replace the raise statement below with code that:
    #
    # 1. Calls the /api/v1/standings endpoint via _make_api_call() with:
    #        leagueId:        "103,104"        # AL=103, NL=104
    #        season:          query_season
    #        standingsTypes:  "regularSeason"
    #        hydrate:         "team"
    #
    # 2. Returns the response immediately if it contains an "error" key.
    #
    # 3. Walks the response's "records" array — each entry is one division.
    #    Each record has:
    #        - division.id, division.name        (e.g. "American League East")
    #        - league.id                         (103=AL, 104=NL)
    #        - teamRecords[]                     list of team standings
    #
    #    Each entry in teamRecords[] has:
    #        - team.id, team.name
    #        - wins, losses, winningPercentage
    #        - divisionRank, leagueRank, gamesBack
    #
    #    See get_team_info() above (around line 380) for a working
    #    example of consuming this same endpoint.
    #
    # 4. For each record, builds a division dict like:
    #        {
    #            "league":   "AL" if league_id == 103 else "NL",
    #            "division": division name,
    #            "teams":    [list of {team_id, name, wins, losses, pct,
    #                                  division_rank, league_rank, games_back}],
    #        }
    #    and appends it to result["divisions"].
    #
    # 5. Finally, returns result.

    data = _make_api_call(
        "/api/v1/standings",
        params={
            "leagueId": "103,104",
            "season": query_season,
            "standingsTypes": "regularSeason",
            "hydrate": "team",
        },
    )
    if "error" in data:
        return data

    for record in data.get("records", []):
        league_id = record.get("league", {}).get("id")
        division_name = record.get("division", {}).get("name", "")
        teams = []
        for team_record in record.get("teamRecords", []):
            teams.append({
                "team_id": team_record.get("team", {}).get("id"),
                "name": team_record.get("team", {}).get("name", ""),
                "wins": team_record.get("wins", 0),
                "losses": team_record.get("losses", 0),
                "pct": team_record.get("winningPercentage", ".000"),
                "division_rank": team_record.get("divisionRank", "?"),
                "league_rank": team_record.get("leagueRank", "?"),
                "games_back": team_record.get("gamesBack", "?"),
            })
        result["divisions"].append({
            "league": "AL" if league_id == 103 else "NL",
            "division": division_name,
            "teams": teams,
        })

    return result

__all__ = [
    "search_player",
    "search_team",
    "get_player_stats",
    "get_team_info",
    "get_team_roster",
    "get_standings",
]
