"""Food database + calorie maths. Calories always come from here, never from the model's guess."""
from __future__ import annotations
import json, re, difflib
from functools import lru_cache
from pathlib import Path
from ..schemas import MealItem

DATA = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def foods() -> dict[str, dict]:
    return {f["id"]: f for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\u0600-\u06FF ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def _index() -> list[tuple[str, str]]:
    idx = []
    for f in foods().values():
        for label in [f["name"], f["arabic"], f["id"].replace("_", " "), *f["aliases"]]:
            idx.append((_norm(label), f["id"]))
    return idx


def find_food(query: str, min_score: float = 0.62) -> dict | None:
    """Exact, then substring, then fuzzy match against names, Arabic names and aliases."""
    q = _norm(query)
    if not q:
        return None
    idx = _index()
    for label, fid in idx:
        if label == q:
            return foods()[fid]
    subs = [(len(label), fid) for label, fid in idx if len(label) >= 3 and (label in q or q in label)]
    if subs:
        return foods()[sorted(subs, key=lambda x: abs(x[0] - len(q)))[0][1]]
    labels = [l for l, _ in idx]
    m = difflib.get_close_matches(q, labels, n=1, cutoff=min_score)
    if m:
        return foods()[next(fid for l, fid in idx if l == m[0])]
    return None


def search_foods(query: str, limit: int = 8) -> list[dict]:
    q = _norm(query)
    if not q:
        return []
    scored = []
    for f in foods().values():
        labels = [_norm(f["name"]), _norm(f["arabic"]), *[_norm(a) for a in f["aliases"]]]
        best = max((1.0 if q == l else 0.9 if l.startswith(q) else 0.75 if q in l else difflib.SequenceMatcher(None, q, l).ratio() * 0.6) for l in labels)
        if best >= 0.5:
            scored.append((best, f))
    return [f for _, f in sorted(scored, key=lambda x: -x[0])[:limit]]


def item_for(food_id: str, grams: float) -> MealItem:
    f = foods()[food_id]
    m = f["per100g"]
    k = grams / 100.0
    return MealItem(food_id=food_id, name=f["name"], grams=round(grams, 1), kcal=int(round(m["kcal"] * k)),
                    protein=round(m["protein"] * k, 1), carbs=round(m["carbs"] * k, 1), fat=round(m["fat"] * k, 1))


def totals(items: list[MealItem]) -> dict:
    return {
        "kcal": sum(i.kcal for i in items),
        "protein": round(sum(i.protein for i in items), 1),
        "carbs": round(sum(i.carbs for i in items), 1),
        "fat": round(sum(i.fat for i in items), 1),
    }
