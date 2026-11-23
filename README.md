# FitGuide AI

An AI fitness and nutrition coach demo. It builds a weekly workout and meal plan from your body and goal, lets you log meals by text or photo, answers questions from a small knowledge base, and renews the plan each week from your real progress.

> Portfolio demo. It gives general guidance and is not medical advice.

## The problem

Generic plans are copied from the internet and never change. Calorie counts guessed from a photo come with no way to check them. People stop following the plan and nothing adapts.

## The solution

| Need | How FitGuide handles it |
| --- | --- |
| Personal targets | Calories, protein and water are calculated in code (Mifflin-St Jeor), not guessed by a chatbot |
| A plan that adapts | Every week you log progress and a new plan is built by clear rules (progress, deload every 4th week) |
| Checkable calories | The AI finds foods and amounts. Calories come from a food table (101 foods), shown as a range, and you confirm before anything is logged |
| Trustworthy answers | RAG: a search over a 19-document knowledge base gives the model facts, and sources are shown |
| Safe changes | After you approve a plan, it only changes through the chat. The AI proposes a change, code validates it |

## User flow

1. Landing page explains the problem and lets you try the target calculator.
2. Onboarding (3 short steps). No login, no database. Data lives in the browser tab only.
3. A draft plan appears (workout + diet). You approve it. After approval it is locked.
4. Chat with the coach: ask questions, log meals or water, send a meal photo, request changes (Arabic or English).
5. Check off workouts day by day, see the same schedule in the Calendar.
6. At the end of the week, enter how it felt and renew. A new draft is created and you approve it again.

## Architecture

```
React + TypeScript (Vite)  --->  Python FastAPI  --->  free LLM (Gemini, OpenAI-compatible API)
 pages, session in browser        |-- calc/      calorie and macro maths
                                  |-- rag/       BM25 search over data/kb/*.md
                                  |-- planner/   workout + diet + weekly renewal + validated changes
                                  |-- vision/    photo -> foods -> calories from table
                                  |-- agent/     chat: retrieve -> prompt -> JSON -> validate -> act
                                  `-- llm/       client with model fallback and JSON retry
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). If you want to learn how each part works: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## Run it locally (VS Code)

You need Python 3.10+ and Node.js 20+. Open the project folder in VS Code and use two terminals.

### 1. Get a free API key (optional but needed for the AI chat and photos)

1. Open https://aistudio.google.com/apikey and create a key (free tier).
2. Copy `.env.example` to `backend/.env` and paste the key after `LLM_API_KEY=`.

Without a key the app still runs: targets, plans, calendar and exercises work, and chat falls back to knowledge-base answers.

### 2. Backend (terminal 1)

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn fitguide.main:app --reload --port 8000
```
If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope Process Bypass` first, or use Command Prompt and `.venv\Scripts\activate.bat`.

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn fitguide.main:app --reload --port 8000
```

Check it: open http://127.0.0.1:8000/api/health

### 3. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The dev server forwards `/api` calls to the backend on port 8000.

## Tests and evaluation

```bash
cd backend
pytest                    # 55 tests, no API key needed
python -m evals.run_all   # retrieval, food matching, plan constraints
python -m evals.vision_eval   # photo accuracy, needs your own photos (see docs/EVALUATION.md)
cd ../frontend
npm run typecheck && npm test
```

| Check | Result |
| --- | --- |
| Knowledge-base search (50 queries) | BM25 hit@1 0.92, hit@3 0.94, vs 0.64 / 0.82 for a simple word-overlap baseline |
| Food name matching (79 queries) | 79 / 79 |
| Plan constraints (2,880 generated profiles) | 96.6% pass; the failures are vegetarian fat-loss plans that fall short of 80% of the protein target |
| Photo calorie accuracy | **Not measured yet.** Run `vision_eval` with weighed meals to get a real number |

Read the limits in [docs/EVALUATION.md](docs/EVALUATION.md): the test queries were written by the project author, so they are optimistic.


## Honest limitations

- Calories are estimates. Food values are approximate averages, and portions vary.
- Photo analysis depends on the model and on portion guessing. The app shows a range and asks you to confirm.
- Free-tier Google models may use prompts to improve Google products. Do not type private health details you would not want shared.
- Exercise videos are YouTube links to other creators' videos (link only, nothing copied). Links were verified alive when built and can break later.
- Session data is lost when the tab closes (by design).

## Project layout

```
backend/   Python API, AI parts, tests, evals
frontend/  React + TypeScript app
api/       Vercel entry point
docs/      explanations
```
