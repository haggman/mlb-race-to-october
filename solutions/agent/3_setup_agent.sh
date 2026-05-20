#!/usr/bin/env bash
# Step 3 — build the Python venv for the ADK agent and install dependencies.
#
# Run from inside solutions/agent/ (the venv is created here, where the
# front_office_analyst package and requirements.txt live). Safe to source
# or run.

if [[ ! -f requirements.txt ]]; then
  echo "ERROR: requirements.txt not found — run this from inside solutions/agent/." >&2
  return 1 2>/dev/null || exit 1
fi

echo "Building venv and installing dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

echo ""
echo "ADK version: $(adk --version)"
echo ""
echo "✓ Step 3 complete. The venv is active in this shell."
echo "  Start the demo with:  adk web --allow_origins \"*\""
echo "  (In a fresh shell, '. activate.sh' re-activates the venv for you.)"
