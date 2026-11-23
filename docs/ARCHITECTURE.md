# Architecture

## Request flow for a chat message

1. The browser sends the last messages, the language, and the session state (profile, plan, today's log).
2. `agent/chat.py` builds a search query and `rag/retriever.py` finds the best knowledge-base chunks. The profile and targets are always added.
3. The prompt (`llm/prompts.py`) tells the model to answer with JSON: a reply, an optional meal, an optional water amount, an optional plan change.
4. `llm/client.py` calls the model, tries the next model if one is rate-limited, and retries once if the JSON is invalid.
5. Code validates the JSON with Pydantic. Foods are looked up in `data/foods.json` and calories are computed there. Plan changes become `PlanChange` operations that `planner/change.py` applies and checks.
6. If anything fails, or there is no key, the answer falls back to the best knowledge-base passage.
7. The browser shows confirm cards. Nothing is logged until the user clicks.

## Why this design

- The model never does arithmetic or edits the plan directly. It proposes, code decides.
- Everything between the model and the user is typed (`schemas.py`), so bad output fails loudly.
- No database. The browser keeps the session, which also keeps the demo private and the hosting free.

## Files

| Path | Role |
| --- | --- |
| `backend/fitguide/main.py` | API routes |
| `backend/fitguide/calc/` | BMR/TDEE, targets, food maths |
| `backend/fitguide/rag/` | BM25 and chunking |
| `backend/fitguide/planner/` | plan building, weekly renewal, validated changes |
| `backend/fitguide/vision/` | photo analysis |
| `backend/fitguide/data/` | foods, exercises, knowledge base |
| `backend/evals/` | evaluation scripts |
| `frontend/src/pages/` | one file per page |
| `frontend/src/store.tsx` | session state in sessionStorage |
