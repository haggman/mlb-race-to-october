"""MLB Stats API tools — exposed as ADK FunctionTools."""

from google.adk.tools import FunctionTool

from .mlb_stats_api import (
    get_player_stats,
    get_team_info,
    get_team_roster,
    search_player,
    search_team,
)

MLB_STATS_API_TOOLS = [
    FunctionTool(func=search_player),
    FunctionTool(func=search_team),
    FunctionTool(func=get_player_stats),
    FunctionTool(func=get_team_info),
    FunctionTool(func=get_team_roster),
]

__all__ = ["MLB_STATS_API_TOOLS"]
