# Deploy on Vercel

1. Upload the project to GitHub (check that no `.env` file is in it).
2. In Vercel: Add New > Project > import the repo. Leave the root directory as the repo root. `vercel.json` handles the build.
3. Settings > Environment Variables: add `LLM_API_KEY` (your Gemini key). Optional: `LLM_MODELS`, `VISIT_LOG_WEBHOOK_URL`.
4. Deploy. Open `/api/health`: `llm_configured` should be `true`.

How it fits together: `vercel.json` builds the frontend to `frontend/dist`, serves it as static files, and sends `/api/*` to `api/index.py`, which exposes the FastAPI app. Functions are allowed 60 seconds because model calls can be slow.

Notes
- Free tiers have rate limits. The model list in `LLM_MODELS` is a fallback chain.
- Vercel's request size limit is about 4.5 MB. The browser shrinks photos before upload.
- If you ever pasted a key anywhere public, rotate it.
