"""The chat agent. One user message goes through these steps (each one is a function you can read and test):

 1. retrieve   : find the most relevant knowledge-base and personal-data chunks (RAG)
 2. prompt     : build the prompt = rules + context + short history (user text is wrapped as untrusted data)
 3. generate   : ask the LLM for ONE JSON object (reply + proposed meal/water/plan changes)
 4. validate   : parse with Pydantic; unknown foods are reported, never guessed
 5. act        : plan changes are applied by deterministic code (planner/change.py), meals and water are returned
                 as proposals for the user to confirm in the UI
 6. fallback   : with no key or a failing model the user still gets retrieved passages, clearly marked."""
from __future__ import annotations
import json, re
from pydantic import BaseModel, Field
from ..calc import nutrition as nut
from ..llm.client import LLM, LLMError, parse_json_model
from ..llm.prompts import CHAT_SYSTEM
from ..planner.change import PlanChange, apply_change
from ..rag.retriever import retrieve
from ..schemas import Action, ChatRequest, ChatResponse, SourceRef


class LLMMealItem(BaseModel):
    name: str
    grams: float = Field(gt=0, le=3000)


class LLMMeal(BaseModel):
    items: list[LLMMealItem] = Field(default_factory=list, max_length=12)


class LLMTurn(BaseModel):
    reply: str
    meal: LLMMeal | None = None
    water_ml: int | None = Field(default=None, ge=0, le=5000)
    plan_changes: list[PlanChange] = Field(default_factory=list, max_length=4)
    used_sources: list[str] = Field(default_factory=list)


def retrieval_query(req: ChatRequest) -> str:
    users = [m.content for m in req.messages if m.role == "user"]
    return users[-1] + (" " + users[-2] if len(users) > 1 and len(users[-1].split()) < 5 else "")


def format_context(sources: list[SourceRef]) -> str:
    if not sources:
        return "(no relevant passages found)"
    return "\n\n".join(f"[{s.id}] {s.title}\n{s.snippet}" for s in sources)


def build_messages(req: ChatRequest, sources: list[SourceRef]) -> list[dict]:
    lang = "Arabic (clear, friendly, you may use common English fitness words)" if req.lang == "ar" else "English"
    msgs = [{"role": "system", "content": CHAT_SYSTEM.format(language=lang) + "\nCONTEXT:\n" + format_context(sources)}]
    for m in req.messages[-8:]:
        if m.role == "user":
            msgs.append({"role": "user", "content": f"<user_message>{m.content}</user_message>"})
        else:
            msgs.append({"role": "assistant", "content": m.content})
    return msgs


def resolve_meal(meal: LLMMeal | None) -> tuple[list, list[str]]:
    items, unknown = [], []
    for it in (meal.items if meal else []):
        f = nut.find_food(it.name)
        if f:
            items.append(nut.item_for(f["id"], it.grams))
        else:
            unknown.append(it.name)
    return items, unknown


WATER_RE = re.compile(r"(\d{2,4})\s*(?:ml|مل)", re.I)


def fallback_reply(req: ChatRequest, sources: list[SourceRef], reason: str) -> ChatResponse:
    last = req.messages[-1].content
    actions: list[Action] = []
    m = WATER_RE.search(last)
    if m and re.search(r"water|drank|drink|شربت|مية|ماء", last, re.I):
        ml = int(m.group(1))
        actions.append(Action(type="log_water", water_ml=ml, summary=f"{ml} ml of water"))
    sources = [x for x in sources if x.score < 99] or sources  # pinned profile/targets chunks are context, not answers
    if sources:
        top = sources[0]
        body = f"{top.snippet}\n\n(Source: {top.title})"
        intro = "The AI model is not available right now" if req.lang == "en" else "موديل الذكاء الاصطناعي مش متاح حاليا"
        reply = f"{intro} ({reason}). " + ("Here is the closest passage from my knowledge base:" if req.lang == "en" else "ده أقرب جزء من قاعدة المعرفة:") + "\n\n" + body
    else:
        reply = "I could not reach the AI model and found nothing relevant in my knowledge base. Try again in a moment." if req.lang == "en" else "مقدرتش أوصل للموديل ومالقيتش حاجة مناسبة في قاعدة المعرفة. جرب تاني بعد شوية."
    return ChatResponse(reply=reply, sources=sources[:3], actions=actions, degraded=True, trace=[f"fallback: {reason}"])


async def respond(llm: LLM | None, req: ChatRequest) -> ChatResponse:
    trace: list[str] = []
    sources = retrieve(retrieval_query(req), req.state, k=4)
    trace.append(f"retrieved {len(sources)} chunks: " + ", ".join(s.id for s in sources))
    if llm is None:
        return fallback_reply(req, sources, "no API key configured")
    try:
        turn = await parse_json_model(llm, build_messages(req, sources), LLMTurn, temperature=0.3, max_tokens=1000)
    except LLMError as e:
        return fallback_reply(req, sources, str(e)[:120])

    reply = turn.reply.strip()
    actions: list[Action] = []
    plan = None

    items, unknown = resolve_meal(turn.meal)
    if items:
        total = sum(i.kcal for i in items)
        actions.append(Action(type="log_meal", items=items, summary=f"{total} kcal"))
        trace.append(f"meal proposal: {len(items)} items, {total} kcal from food table")
    if unknown:
        reply += ("\n\n" + (f"I do not have {', '.join(unknown)} in my food table, so I did not add calories for it. Tell me a similar food or log it yourself."
                            if req.lang == "en" else f"مفيش {', '.join(unknown)} في جدول الأكل عندي فمحسبتش سعراته. قولي أكلة شبهه أو سجله بنفسك."))
    if turn.water_ml:
        actions.append(Action(type="log_water", water_ml=turn.water_ml, summary=f"{turn.water_ml} ml of water"))

    state = req.state
    if turn.plan_changes:
        if not (state.profile and state.plan):
            reply += "\n\n" + ("Create your plan first, then I can change it." if req.lang == "en" else "اعمل خطتك الأول وبعدين أقدر أعدلها.")
        else:
            cur = state.plan
            for ch in turn.plan_changes:
                res = apply_change(state.profile, cur, ch)
                if res.ok and res.plan:
                    res.plan.status = cur.status
                    res.plan.changes = cur.changes + [res.message] if cur.changes and cur.changes[-1] != res.message else [res.message]
                    cur, plan = res.plan, res.plan
                    actions.append(Action(type="plan_changed", summary=res.message))
                else:
                    actions.append(Action(type="refused_plan_change", summary=res.message))
                    reply += "\n\n" + res.message
            trace.append(f"plan changes: {[c.op for c in turn.plan_changes]}")
    used = [s for s in sources if s.id in set(turn.used_sources)] or sources[:2]
    return ChatResponse(reply=reply, sources=[s for s in used if not s.id.startswith("user#")][:3] or used[:2], actions=actions, plan=plan, trace=trace)
