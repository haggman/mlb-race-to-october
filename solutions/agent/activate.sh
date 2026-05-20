#!/usr/bin/env bash
# MLB Race to October — demo environment setup (lives in solutions/agent/).
#
# Replaces the original solutions/agent/activate.sh with a superset: same
# project + .env + venv behavior, plus the variables the 1/2/3 setup scripts
# need. SOURCE it from inside solutions/agent/ (don't execute):
#     . activate.sh

# --- sourced-vs-executed guard (env only persists when sourced) ------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Please SOURCE this script so the env vars stick:"
  echo "    . activate.sh"
  exit 1
fi

# --- project ---------------------------------------------------------------
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value core/project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: no active project. Run: gcloud config set project <PROJECT_ID>" >&2
  return 1
fi
export PROJECT_ID
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"   # agent.py reads this exact name

# --- agent runtime env (from .env, exported so child procs inherit it) ------
[[ -f .env ]] && . .env
export BQ_DATASET="${BQ_DATASET:-mlb_race_to_october}"
export BQ_LOCATION="${BQ_LOCATION:-US}"        # must match the gs://class-demo parquet (US)
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-True}"

# --- deploy defaults (only used by the optional Task 5 deploy) -------------
export REGION="${REGION:-us-central1}"
export STAGING_BUCKET="${STAGING_BUCKET:-gs://${PROJECT_ID}-agent-staging}"

# --- activate venv if 3_setup_agent.sh has already built it ----------------
if [[ -f venv/bin/activate ]]; then
  source venv/bin/activate
  VENV_STATUS="active"
else
  VENV_STATUS="not built yet (run: bash 3_setup_agent.sh, then re-source this)"
fi

echo "✓ Environment configured:"
echo "  PROJECT_ID : ${PROJECT_ID}"
echo "  BQ_DATASET : ${BQ_DATASET} (${BQ_LOCATION})"
echo "  REGION     : ${REGION}"
echo "  venv       : ${VENV_STATUS}"
