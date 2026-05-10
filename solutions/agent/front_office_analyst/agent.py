"""Front Office Analyst — root agent definition.

Hello-world phase: just BigQueryToolset, no MLB Stats API yet. This file
gets exercised by `adk web` from the parent directory.
"""

import os

from dotenv import load_dotenv
import google.auth
from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

from .prompts import get_agent_instructions
from .tools import MLB_STATS_API_TOOLS

# Load .env if present. In Cloud Shell, students typically `export` env vars
# directly, but a .env file works too. ADC handles credentials automatically.
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
BQ_DATASET = os.environ.get("BQ_DATASET", "mlb_race_to_october")
MODEL = os.environ.get("AGENT_MODEL", "gemini-3-flash-preview")

if not PROJECT_ID:
    raise RuntimeError(
        "GOOGLE_CLOUD_PROJECT is not set. In Cloud Shell, run:\n"
        "  export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)\n"
        "Or add it to a .env file in this directory."
    )


# --- BigQuery toolset --------------------------------------------------------
# Application Default Credentials (ADC). In Cloud Shell, this is automatic.
# Locally, run: gcloud auth application-default login
credentials, _ = google.auth.default()

bigquery_toolset = BigQueryToolset(
    credentials_config=BigQueryCredentialsConfig(credentials=credentials),
    bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
)


# --- Root agent --------------------------------------------------------------
root_agent = Agent(
    model=MODEL,
    name="front_office_analyst",
    description=(
        "Data analyst for an MLB front office during the trade deadline. "
        "Answers analytical, predictive, and current-state questions by "
        "composing BigQuery queries, BQML model predictions, and live MLB "
        "Stats API calls."
    ),
    instruction=get_agent_instructions(PROJECT_ID, BQ_DATASET),
    tools=[bigquery_toolset, *MLB_STATS_API_TOOLS],
)
