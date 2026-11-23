"""FastAPI application: thin HTTP layer over the AI modules. Stateless by design (no database): the browser keeps the
demo session and sends the state it needs with each request."""
from __future__ import annotations
import base64
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .agent.chat import respond
from .calc import nutrition as nut
from .calc.energy import compute_targets
from .config import get_settings
from .llm.client import LLM, LLMError, OpenAICompatLLM
from .planner import library as lib
from .planner.adapt import renew_plan
from .planner.build import generate_plan
from .planner.workout import APPROACH_INFO, TEMPLATES
from .rag.retriever import kb_chunks
from .schemas import ChatRequest, ChatResponse, Plan, Profile, Targets, WeekProgress
from .telemetry import log_visit
from .vision.analyzer import VisionResult, analyze_image

app = FastAPI(title="FitGuide AI API", version="1.0.0")
_s = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=list(_s.allowed_origins), allow_methods=["*"], allow_headers=["*"])

MAX_IMAGE_BYTES = 3_500_000  # Vercel request bodies are limited to about 4.5 MB; the frontend resizes photos first


def get_llm() -> Optional[LLM]:
    return OpenAICompatLLM() if get_settings().llm_enabled else None


@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "llm_configured": s.llm_enabled, "models": list(s.models) if s.llm_enabled else [],
            "kb_chunks": len(kb_chunks()), "foods": len(nut.foods()), "exercises": len(lib.exercises())}


class TargetsReq(BaseModel):
    profile: Profile


@app.post("/api/targets", response_model=Targets)
def targets(req: TargetsReq):
    return compute_targets(req.profile)


class GenerateReq(BaseModel):
    profile: Profile
    approach: Optional[str] = None


@app.post("/api/plan/generate", response_model=Plan)
def plan_generate(req: GenerateReq):
    settings = {"approach": req.approach} if req.approach else {}
    return generate_plan(req.profile, 1, settings)


class RenewReq(BaseModel):
    profile: Profile
    plan: Plan
    progress: WeekProgress


@app.post("/api/plan/renew", response_model=Plan)
def plan_renew(req: RenewReq):
    return renew_plan(req.profile, req.plan, req.progress)


@app.get("/api/plan/approaches")
def approaches():
    return [{"id": k, "name": TEMPLATES[k]["name"], "description": APPROACH_INFO[k]} for k in TEMPLATES]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, llm: Optional[LLM] = Depends(get_llm)):
    return await respond(llm, req)


class VisionReq(BaseModel):
    image_base64: str = Field(min_length=100)
    mime: str = "image/jpeg"
    lang: str = "en"


@app.post("/api/vision/analyze", response_model=VisionResult)
async def vision(req: VisionReq, llm: Optional[LLM] = Depends(get_llm)):
    if req.mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Use a JPEG, PNG or WebP image.")
    try:
        if len(base64.b64decode(req.image_base64, validate=True)) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image too large. Use a smaller photo.")
    except ValueError:
        raise HTTPException(400, "Image is not valid base64.")
    if llm is None:
        raise HTTPException(503, "Photo analysis needs an AI model key. Add LLM_API_KEY to the backend settings.")
    try:
        return await analyze_image(llm, req.image_base64, req.mime, req.lang)
    except LLMError as e:
        raise HTTPException(502, f"The AI model could not analyse this photo: {str(e)[:160]}")


@app.get("/api/foods")
def foods_search(q: str = Query("", max_length=60), limit: int = Query(8, ge=1, le=30)):
    if not q.strip():
        return list(nut.foods().values())[:limit]
    return nut.search_foods(q, limit)


class MealReq(BaseModel):
    items: list[dict] = Field(default_factory=list, max_length=20)


@app.post("/api/meal/compute")
def meal_compute(req: MealReq):
    """Compute calories for items the user picked/edited by hand: [{food_id, grams}]."""
    out = []
    for it in req.items:
        fid, g = it.get("food_id"), it.get("grams")
        if fid not in nut.foods() or not isinstance(g, (int, float)) or not 0 < g <= 3000:
            raise HTTPException(422, f"Invalid item: {it}")
        out.append(nut.item_for(fid, float(g)))
    return {"items": out, "totals": nut.totals(out)}


@app.get("/api/exercises")
def exercises_list(muscle: Optional[str] = None, mode: Optional[str] = None, level: Optional[str] = None, q: Optional[str] = None):
    out = lib.exercises()
    if muscle:
        out = [e for e in out if e["muscle"] == muscle]
    if mode:
        out = [e for e in out if e["mode"] == mode]
    if level:
        out = [e for e in out if e["level"] == level]
    if q:
        out = [e for e in out if q.lower() in e["name"].lower()]
    return out


class VisitReq(BaseModel):
    name: str = Field(default="", max_length=40)


@app.post("/api/visit")
async def visit(req: VisitReq):
    return {"logged": await log_visit("demo_started", req.name)}
