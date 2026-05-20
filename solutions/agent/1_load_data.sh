#!/usr/bin/env bash
# Step 1 — enable APIs, create the BigQuery dataset, load the Lahman data.
#
# Run from inside solutions/agent/. Safe to source (. 1_load_data.sh) or
# run (bash 1_load_data.sh).

if [[ -z "${PROJECT_ID:-}" ]]; then
  echo "Run '. activate.sh' first." >&2
  return 1 2>/dev/null || exit 1
fi

LOADER="../../sql/load_lahman.sh"
if [[ ! -f "${LOADER}" ]]; then
  echo "ERROR: ${LOADER} not found — run this from inside solutions/agent/." >&2
  return 1 2>/dev/null || exit 1
fi

echo "Enabling required APIs (first run can take a minute)..."
gcloud services enable \
  bigquery.googleapis.com \
  bigquerystorage.googleapis.com \
  aiplatform.googleapis.com \
  --project="${PROJECT_ID}"

echo ""
echo "Creating dataset ${BQ_DATASET} in ${BQ_LOCATION}..."
bq --location="${BQ_LOCATION}" mk --dataset \
  --description "MLB Race to October — historical Lahman data + BQML model" \
  "${PROJECT_ID}:${BQ_DATASET}" || echo "  (dataset already exists — continuing)"

echo ""
echo "Loading Lahman tables + column descriptions..."
# Reuses the repo's tested loader (9 LOAD DATA + 9 ALTER TABLE blocks). It
# resolves its own SQL path and reads PROJECT_ID from the environment.
bash "${LOADER}"

echo ""
echo "✓ Step 1 complete — data is in BigQuery."
