#!/usr/bin/env bash
# Step 2 — train the BQML playoff-probability model.
#
# The CREATE MODEL below mirrors Step 1 of sql/train_playoff_model.sql, kept
# inline so this script is self-contained for the demo. Dataset name matches
# the canonical SQL (mlb_race_to_october); project comes from --project_id.
# Safe to source or run.

if [[ -z "${PROJECT_ID:-}" ]]; then
  echo "Run '. activate.sh' first." >&2
  return 1 2>/dev/null || exit 1
fi

echo "Training mlb_race_to_october.playoff_probability (about a minute)..."
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" <<'SQL'
CREATE OR REPLACE MODEL `mlb_race_to_october.playoff_probability`
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['played_postseason'],
  auto_class_weights = TRUE
) AS
SELECT
  COALESCE(won_division, FALSE)
    OR COALESCE(won_wild_card, FALSE)
    OR COALESCE(won_league, FALSE)
    OR COALESCE(won_world_series, FALSE) AS played_postseason,
  wins / games AS winning_pct,
  runs_scored - runs_allowed AS run_differential,
  earned_run_avg
FROM `mlb_race_to_october.teams`
WHERE yearID BETWEEN 1994 AND 2024;
SQL

echo ""
echo "Verifying the trained model..."
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" <<'SQL'
SELECT
  ROUND(roc_auc, 3)  AS roc_auc,
  ROUND(accuracy, 3) AS accuracy
FROM ML.EVALUATE(MODEL `mlb_race_to_october.playoff_probability`);
SQL

echo ""
echo "✓ Step 2 complete — expect ROC AUC around 0.97."
