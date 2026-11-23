# How FitGuide works (a learning guide)

Read this with the code open. Each section names the file.

## 1. The big idea: the AI proposes, code decides
Language models are good at understanding messy text and photos. They are bad at exact maths and can make things up. So FitGuide uses the model only to understand, and uses normal code for everything that must be right: calories, targets, plan edits.

## 2. Calculations (`calc/energy.py`)
- BMR: calories your body burns at rest, from the Mifflin-St Jeor equation.
- TDEE: BMR times an activity factor.
- Target: TDEE minus about 18% to lose fat, plus about 8% to build muscle. There are safety floors, and flags for conditions like diabetes or pregnancy.
- Protein is set per kg of body weight and capped at about a third of calories.

## 3. Foods (`calc/nutrition.py`, `data/foods.json`)
Each food has calories, protein, carbs and fat per 100 g. `find_food` matches a name (English or Egyptian, like "كشري") to a row. Calories = per100g x grams / 100. This is why the calories can be checked.

## 4. RAG: giving the model facts (`rag/`)
RAG means Retrieval-Augmented Generation: first search a set of documents, then give the best passages to the model to answer from.
- The knowledge base is the markdown files in `data/kb/`. They are split into chunks at each `##` heading.
- BM25 (`rag/bm25.py`) scores chunks by how well they match the question: rare words count more, and very long chunks are not favoured. It is written from scratch so you can read it.
- Your profile and targets are always added, so answers fit you.
- Sources are returned to the screen so you can verify the answer.

## 5. The chat agent (`agent/chat.py`)
Steps: retrieve, build the prompt, ask the model for JSON, validate, act, fall back. The JSON can contain a meal, water, or a plan change. Pydantic models in `schemas.py` reject anything malformed. `llm/client.py` retries once on bad JSON and tries the next model on rate limits.

## 6. Planner (`planner/`)
- `workout.py` picks exercises by split, level, equipment and injuries from the exercise library.
- `diet.py` builds meals from templates, scales portions to hit the calorie target, and removes allergens and dislikes.
- `adapt.py` renews the week: if you finished most workouts and it felt easy, it adds a little volume; if it felt too hard or you missed a lot, it lowers it; every 4th week is a lighter deload week.
- `change.py` applies changes requested in chat as small operations (swap an exercise, remove a food, change days). The model suggests, this code applies and checks.

## 7. Vision (`vision/analyzer.py`)
The model looks at the photo and lists foods with estimated grams. Each food is matched to the table, calories are computed with a low/high range, and the user edits and confirms. Portion size is the main source of error, which is why you can edit the grams.

## 8. Evaluation (`evals/`)
See [EVALUATION.md](EVALUATION.md). Habit to learn: never claim an accuracy you have not measured.

## 9. The frontend (`frontend/src/`)
- `store.tsx` keeps state in sessionStorage with a reducer.
- `api.ts` is the only place that calls the backend.
- `types.ts` mirrors the backend schemas.
- Each page in `pages/` is one screen.
