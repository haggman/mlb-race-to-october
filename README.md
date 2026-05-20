# MLB Race to October — Building AI Agents Across Google Cloud's GenAI Stack

A hands-on lab that builds a four-tier AI platform on Google Cloud's **Gemini Enterprise** stack, using 150 years of Major League Baseball history as the dataset. It runs from a single data foundation — a document retrieval layer plus a BigQuery analytical layer with a trained BQML model — up through four agent surfaces:

| Tier | Audience | Surface | What it does |
| :--- | :--- | :--- | :--- |
| 1 | Front office | Gemini Enterprise app | Grounded chat over documents |
| 2 | Scouts | Agent Designer | Structured, repeatable scouting briefs |
| 3 | Fans | CX Agent Studio | Public, multilingual concierge |
| 4 | Data science | **ADK on Agent Runtime** | A code-first data-controller agent over BigQuery, BQML, and the live MLB Stats API |

The recurring lesson: **an agent's capability is determined by the data architecture it can reach, not by the model.** Tiers 1–3 reach only documents and hit a wall on computation and current-season state. Tier 4 — the **Front Office Analyst** — crosses that wall by composing BigQuery analytics, a BQML playoff-probability model, and live API calls into single answers.

This README covers the part you can stand up fastest: **running the Tier 4 ADK agent locally**. The full instructor-led lab (Tasks 1–5, including the no-code tiers and Agent Runtime deployment) lives in the lab guide.

---

## What you'll run

The ADK demo is the completed **Front Office Analyst** agent in [`solutions/agent/`](solutions/agent/). It answers three kinds of questions and composes across them:

- **Analytical** (BigQuery): *"Who has the most career home runs in the data?"*
- **Predictive** (BQML): *"Predict each team's 2025 playoff probability."*
- **Current state** (MLB Stats API): *"How is Aaron Judge hitting this season?"*
- **Composed**: *"If we trade for Aaron Judge, what happens to the Phillies' playoff probability, and how is he trending right now?"*

Three setup scripts get you from a clean project to a running agent: load the data, train the model, set up the agent.

---

## Prerequisites

- A Google Cloud project with billing enabled, and `Owner` or equivalent rights to enable APIs and create BigQuery resources.
- **Google Cloud Shell** is the path of least resistance — `gcloud`, `bq`, and `python3` are preinstalled and credentials are already wired up. Everything below assumes Cloud Shell.
- Running locally instead? You'll need the `gcloud` CLI, `bq`, Python 3.10+, and `gcloud auth application-default login` for Application Default Credentials.

The scripts enable the APIs they need (`bigquery`, `bigquerystorage`, `aiplatform`), create the dataset, and install dependencies — so there's no manual console setup before you start.

---

## Quick start

Clone the repo, move into the agent directory, and run the three scripts in order:

```bash
git clone https://github.com/haggman/mlb-race-to-october
cd mlb-race-to-october/solutions/agent

. activate.sh            # set env vars (project, dataset, region) + activate venv if built
bash 1_load_data.sh      # enable APIs, create the dataset, load the Lahman tables
bash 2_train_model.sh    # train the BQML playoff-probability model + verify (ROC AUC ~0.97)
bash 3_setup_agent.sh    # build the Python venv and install ADK + dependencies

adk web --allow_origins "*"
```

`3_setup_agent.sh` leaves the virtualenv active in your shell, so `adk web` runs immediately after. In a **fresh** shell, just `cd solutions/agent && . activate.sh` to restore the environment and re-activate the venv before launching.

> **Note:** `activate.sh` must be **sourced** (`. activate.sh`) so its environment variables persist. The numbered scripts can be sourced or run with `bash` — running them keeps any failure isolated from your shell.

Once `adk web` prints a local URL (e.g. `http://127.0.0.1:8000`), open it, pick **front_office_analyst** from the app dropdown, and start asking questions. The `--allow_origins "*"` flag is a Cloud Shell requirement (the web preview proxy serves the UI from a different origin); you don't need it when running on your own machine.

---

## Try these prompts

Each one exercises a different data path; watch the reasoning trace to see which tool the agent reaches for.

```
Who has the most career home runs in the data?
Which pitcher has given up the most home runs in his career?
Predict each MLB team's playoff probability for the 2025 season. Sort highest to lowest.
How is Aaron Judge hitting this season?
Where do the Phillies sit in the NL East right now?
If we trade for Aaron Judge, what happens to the Phillies' playoff probability, and how is he trending right now?
```

The "home runs given up" prompt is worth a close look — the agent routes to `pitching.home_runs_allowed` rather than `batting.home_runs` purely because of the column descriptions attached during the data load. Schema clarity is what makes the natural-language-to-SQL work.

---

## What each script does

**`activate.sh`** — Sourced. Exports `PROJECT_ID` / `GOOGLE_CLOUD_PROJECT`, the BigQuery dataset and location, the agent's runtime env (`GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`), and deploy defaults. Activates the agent venv if it has already been built.

**`1_load_data.sh`** — Enables the required APIs, creates the `mlb_race_to_october` dataset (US), then runs the repo's loader at [`sql/load_lahman.sh`](sql/load_lahman.sh), which loads nine Lahman tables from public Parquet and attaches a description to every column.

**`2_train_model.sh`** — Trains `mlb_race_to_october.playoff_probability`, a logistic-regression model over `winning_pct`, `run_differential`, and `earned_run_avg` (team-seasons 1994–2024, 2025 held out), then runs `ML.EVALUATE` so you can confirm it trained before demoing.

**`3_setup_agent.sh`** — Creates a Python virtualenv in `solutions/agent/`, installs ADK and the supporting libraries from `requirements.txt`, and prints the installed ADK version.

---

## Repository layout

```
mlb-race-to-october/
├── README.md
├── sql/
│   ├── load_lahman.sql        # 9 LOAD DATA + 9 ALTER TABLE (column descriptions)
│   ├── load_lahman.sh         # runner for the load
│   └── train_playoff_model.sql
├── agent/                     # starter agent with TODOs (the lab exercise)
│   └── front_office_analyst/
├── solutions/
│   └── agent/                 # completed agent + demo scripts (run from here)
│       ├── activate.sh
│       ├── 1_load_data.sh
│       ├── 2_train_model.sh
│       ├── 3_setup_agent.sh
│       ├── requirements.txt
│       └── front_office_analyst/
│           ├── agent.py        # root agent: BigQuery toolset + MLB Stats API tools
│           ├── prompts.py      # persona, surface descriptions, routing rules
│           └── tools/          # MLB Stats API FunctionTools
└── fan-page/                  # sample fan site for the Tier 3 (CX Studio) embed
```

`agent/` is the starter version learners work through in the lab — it has unfinished TODOs and deliberately fails on current-season questions. `solutions/agent/` is the finished agent the demo runs.

---

## Notes

- **Model.** The agent defaults to `gemini-3.5-flash` (set in `agent.py`, overridable via the `AGENT_MODEL` env var). Model IDs change over time, so if `adk web` errors on startup, that's the first thing to check for your project and region.
- **Cost.** Loading the data, training the model, and running the agent all incur Google Cloud charges (BigQuery storage/queries, Vertex AI calls). Clean up the `mlb_race_to_october` dataset when you're done if you don't need it.
- **Deploying to Agent Runtime.** This README covers the local `adk web` demo. To run the agent as a managed service and register it in a Gemini Enterprise app, follow Task 5 of the lab guide — that path adds the `agent_engines` dependency, a staging bucket, and service-agent IAM bindings.
- **The data is public.** The Lahman Parquet files and profile/rulebook documents are served from a public Cloud Storage bucket, so the load works in any project without extra access setup.

---

*Built by [Patrick Haggerty](https://github.com/haggman). Clone it, fork it, or use it as a reference for building story-driven, data-grounded agents in your own organization.*