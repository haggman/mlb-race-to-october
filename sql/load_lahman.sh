#!/bin/bash
# Loads Lahman baseball data into BigQuery and applies column descriptions.
#
# Reads load_lahman.sql, splits it into individual statements (LOAD DATA
# blocks for each table, then ALTER TABLE blocks that attach column
# descriptions), and executes each one with progress feedback.
#
# The SQL source is load_lahman.sql in this directory — open it in
# Cloud Shell Editor to examine the load definitions and the column
# descriptions before running.
#
# Prerequisites:
#   - The mlb_race_to_october dataset must exist:
#       bq mk --location=US mlb_race_to_october
#   - PROJECT_ID environment variable must be set:
#       export PROJECT_ID=$(gcloud config get-value project)
#
# Usage: bash sql/load_lahman.sh

set -e

PROJECT_ID=${PROJECT_ID:?"PROJECT_ID environment variable is not set. Run: export PROJECT_ID=\$(gcloud config get-value project)"}
SQL_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="${SQL_DIR}/load_lahman.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "ERROR: SQL file not found at ${SQL_FILE}"
  exit 1
fi

echo "Loading Lahman data into project ${PROJECT_ID}..."
echo ""

# Strip comment-only lines and blank lines so statement boundaries are clean.
CLEAN_SQL=$(sed '/^[[:space:]]*--/d; /^[[:space:]]*$/d' "${SQL_FILE}")

LOAD_COUNT=0
ALTER_COUNT=0
CURRENT=""

while IFS= read -r line; do
  CURRENT="${CURRENT}${line}"$'\n'

  # A semicolon at end-of-line marks the end of a complete statement.
  if [[ "${line}" =~ \;[[:space:]]*$ ]]; then
    # Extract table name: find mlb_race_to_october.<table_name> and strip the prefix.
    TABLE_NAME=$(echo "${CURRENT}" | grep -oE 'mlb_race_to_october\.[a-z_]+' | head -1 | sed 's/.*\.//')

    if [[ "${CURRENT}" == *"LOAD DATA"* ]]; then
      LOAD_COUNT=$((LOAD_COUNT + 1))
      echo -n "  Loading ${TABLE_NAME}... "
      if OUTPUT=$(bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" "${CURRENT}" 2>&1); then
        echo "✓"
      else
        echo "✗"
        echo "${OUTPUT}"
        exit 1
      fi
    elif [[ "${CURRENT}" == *"ALTER TABLE"* ]]; then
      ALTER_COUNT=$((ALTER_COUNT + 1))
      echo -n "  Describing ${TABLE_NAME}... "
      if OUTPUT=$(bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" "${CURRENT}" 2>&1); then
        echo "✓"
      else
        echo "✗"
        echo "${OUTPUT}"
        exit 1
      fi
    fi
    CURRENT=""
  fi
done <<< "${CLEAN_SQL}"

echo ""
echo "Done. Loaded ${LOAD_COUNT} tables and applied descriptions to ${ALTER_COUNT} tables."