"""MLB Stats API tools — exposed as ADK FunctionTools."""

from google.adk.tools import FunctionTool
 
from .mlb_stats_api import (
    get_player_stats,
    get_team_info,
    get_team_roster,
    search_player,
    search_team,
    # TODO 2: After implementing get_standings() in mlb_stats_api.py,
    # uncomment the import below to make it available here:
    #
    get_standings,
)
 
MLB_STATS_API_TOOLS = [
    FunctionTool(func=search_player),
    FunctionTool(func=search_team),
    FunctionTool(func=get_player_stats),
    FunctionTool(func=get_team_info),
    FunctionTool(func=get_team_roster),
    # TODO 2: Once get_standings is implemented and imported above,
    # register it as a FunctionTool by adding this line:
    #
    FunctionTool(func=get_standings),
]
 
__all__ = ["MLB_STATS_API_TOOLS"]
