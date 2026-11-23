"""Meal photo analysis = vision model (what and how much) + food table (calories). Always shows a range and always
needs the user's confirmation before anything is logged."""
from __future__ import annotations
from pydantic import BaseModel, Field
from ..calc import nutrition as nut
from ..llm.client import LLM, parse_json_model
from ..llm.prompts import VISION_SYSTEM


class VisionItem(BaseModel):
    name: str
    grams: float = Field(gt=0, le=3000)
    grams_low: float | None = None
    grams_high: float | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class VisionRaw(BaseModel):
    is_food: bool = True
    items: list[VisionItem] = Field(default_factory=list, max_length=12)
    notes: str = ""


class AnalyzedItem(BaseModel):
    name: str
    matched: bool
    food_id: str | None = None
    food_name: str | None = None
    grams: float
    grams_low: float
    grams_high: float
    kcal: int = 0
    kcal_low: int = 0
    kcal_high: int = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    confidence: float = 0.5


class VisionResult(BaseModel):
    is_food: bool
    items: list[AnalyzedItem]
    kcal: int
    kcal_low: int
    kcal_high: int
    notes: str = ""
    disclaimer: str = "Estimate from a photo. Portion size is the biggest source of error. Edit the amounts, then confirm."


def build_result(raw: VisionRaw) -> VisionResult:
    items: list[AnalyzedItem] = []
    for it in raw.items:
        low = it.grams_low if it.grams_low and it.grams_low > 0 else it.grams * 0.75
        high = it.grams_high if it.grams_high and it.grams_high >= it.grams else it.grams * 1.3
        low, high = min(low, it.grams), max(high, it.grams)
        f = nut.find_food(it.name)
        if not f:
            items.append(AnalyzedItem(name=it.name, matched=False, grams=it.grams, grams_low=low, grams_high=high, confidence=it.confidence))
            continue
        mid, lo, hi = nut.item_for(f["id"], it.grams), nut.item_for(f["id"], low), nut.item_for(f["id"], high)
        items.append(AnalyzedItem(name=it.name, matched=True, food_id=f["id"], food_name=f["name"], grams=it.grams, grams_low=low, grams_high=high,
                                  kcal=mid.kcal, kcal_low=lo.kcal, kcal_high=hi.kcal, protein=mid.protein, carbs=mid.carbs, fat=mid.fat, confidence=it.confidence))
    m = [i for i in items if i.matched]
    notes = raw.notes
    unmatched = [i.name for i in items if not i.matched]
    if unmatched:
        notes = (notes + " " if notes else "") + f"Not in the food table, so no calories were added for: {', '.join(unmatched)}. Pick a similar food to include it."
    return VisionResult(is_food=raw.is_food and bool(items), items=items, kcal=sum(i.kcal for i in m), kcal_low=sum(i.kcal_low for i in m),
                        kcal_high=sum(i.kcal_high for i in m), notes=notes)


async def analyze_image(llm: LLM, image_b64: str, mime: str, lang: str = "en") -> VisionResult:
    messages = [
        {"role": "system", "content": VISION_SYSTEM},
        {"role": "user", "content": [
            {"type": "text", "text": "Analyse this meal photo." + (" Write notes in Arabic." if lang == "ar" else "")},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
        ]},
    ]
    raw = await parse_json_model(llm, messages, VisionRaw, temperature=0.1, max_tokens=900)
    return build_result(raw)
