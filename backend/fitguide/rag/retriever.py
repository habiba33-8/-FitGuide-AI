"""Knowledge base loading, chunking and retrieval.

Chunking: each markdown file is split at '## ' headings. Every chunk keeps the file title and heading, because
a chunk like "Pace" is meaningless on its own. Per-user facts (profile, today's log, plan) are turned into extra
chunks at request time, so the same retriever answers both general questions and "what should I eat now?"."""
from __future__ import annotations
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from .bm25 import BM25, tokenize
from ..schemas import SessionState, SourceRef

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"

# Used only when no LLM is available to translate an Arabic question into English search terms.
AR_TO_EN = {
    "بروتين": "protein", "كالوري": "calories calorie", "سعرات": "calories calorie", "مية": "water", "مياه": "water hydration",
    "ماء": "water hydration", "تخسيس": "fat loss", "نزول": "fat loss", "وزن": "weight", "دهون": "fat", "تضخيم": "muscle gain",
    "عضل": "muscle", "تمرين": "workout exercise training", "تمارين": "workout exercise training", "نوم": "sleep", "اكل": "food meal",
    "أكل": "food meal", "وجبة": "meal", "رمضان": "ramadan", "كشري": "koshari", "فول": "ful medames", "طعمية": "ta'ameya falafel",
    "مكملات": "supplements", "كرياتين": "creatine", "اصابة": "injury", "إصابة": "injury", "ركبة": "knee", "ضهر": "back", "ظهر": "back",
    "كارديو": "cardio", "اسخن": "warm-up", "إحماء": "warm-up", "سكر": "diabetes", "ضغط": "blood pressure", "حمل": "pregnancy",
    "راحة": "rest recovery", "خطة": "plan", "دايت": "diet", "جدول": "plan schedule", "مبتدئ": "beginner", "صيام": "fasting",
}


@dataclass
class Chunk:
    id: str
    title: str
    text: str
    source: str  # "kb" or "user"


def _split_markdown(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", raw, re.M)
    title_s = title.group(1).strip() if title else path.stem
    parts = re.split(r"^## ", raw, flags=re.M)
    chunks = []
    for n, part in enumerate(parts[1:], 1):
        head, _, body = part.partition("\n")
        text = body.strip()
        if text:
            chunks.append(Chunk(id=f"{path.stem}#{n}", title=f"{title_s}: {head.strip()}", text=text, source="kb"))
    return chunks


@lru_cache(maxsize=1)
def kb_chunks() -> tuple[Chunk, ...]:
    out: list[Chunk] = []
    for p in sorted(KB_DIR.glob("*.md")):
        out.extend(_split_markdown(p))
    return tuple(out)


@lru_cache(maxsize=1)
def _kb_index() -> BM25:
    return BM25([c.title + " " + c.title + " " + c.text for c in kb_chunks()])


def user_chunks(state: SessionState) -> list[Chunk]:
    """Turn the user's own data into searchable chunks (their 'personal knowledge base')."""
    out: list[Chunk] = []
    p = state.profile
    if p:
        out.append(Chunk("user#profile", "Your profile",
                         f"Goal {p.goal.replace('_', ' ')}. {p.sex}, age {p.age}, {p.height_cm:.0f} cm, {p.weight_kg:.0f} kg. "
                         f"Activity {p.activity}. Level {p.level}. Equipment {p.equipment.replace('_', ' ')}. {p.days_per_week} training days per week. "
                         f"Diet style {p.diet_style.replace('_', ' ')}. Allergies: {', '.join(p.allergies) or 'none'}. "
                         f"Dislikes: {', '.join(p.dislikes) or 'none'}. Injuries: {', '.join(p.injuries) or 'none'}. Conditions: {', '.join(p.conditions) or 'none'}.", "user"))
    pl = state.plan
    if pl:
        t = pl.targets
        out.append(Chunk("user#targets", "Your daily targets",
                         f"Calories {t.calories} kcal, protein {t.protein_g} g, carbs {t.carbs_g} g, fat {t.fat_g} g, water {t.water_ml} ml.", "user"))
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for w in pl.workouts:
            if not w.rest:
                out.append(Chunk(f"user#workout{w.day}", f"Your workout on {days[w.day]}",
                                 f"{w.title}. " + ", ".join(f"{e.name} {e.sets}x{e.reps}" for e in w.exercises), "user"))
        for d in pl.diet:
            meals = "; ".join(f"{m.slot}: " + ", ".join(f"{i.name} {i.grams:.0f} g" for i in m.items) for m in d.meals)
            out.append(Chunk(f"user#diet{d.day}", f"Your meals on {days[d.day]}", f"{d.kcal} kcal. {meals}", "user"))
    log = state.today
    eaten = sum(i.kcal for i in log.meals)
    out.append(Chunk("user#today", "Today so far",
                     f"Eaten {eaten} kcal. Protein {sum(i.protein for i in log.meals):.0f} g. Water {log.water_ml} ml. "
                     f"Meals: {', '.join(i.name for i in log.meals) or 'nothing logged yet'}. Workout done: {log.workout_done}.", "user"))
    return out


PINNED = {"user#profile", "user#targets"}


def expand_arabic(query: str) -> str:
    extra = [en for ar, en in AR_TO_EN.items() if ar in query]
    return query + " " + " ".join(extra) if extra else query


def retrieve(query: str, state: SessionState | None = None, k: int = 4, min_score: float = 0.5) -> list[SourceRef]:
    query = expand_arabic(query)
    kb = list(kb_chunks())
    if state is None:
        cands = list(zip(_kb_index().scores(query), kb))
    else:
        # one shared index (KB + the user's own chunks) so word rarity (idf) is computed over the same corpus
        uc = user_chunks(state)
        allc = kb + uc
        sc = BM25([c.title + " " + c.title + " " + c.text for c in allc]).scores(query)
        cands = [(s * (1.15 if c.source == "user" else 1.0), c) for s, c in zip(sc, allc)]
    cands = [(s, c) for s, c in cands if s >= min_score and c.id not in PINNED]
    cands.sort(key=lambda x: -x[0])
    out = [SourceRef(id=c.id, title=c.title, snippet=c.text[:400], score=round(s, 3)) for s, c in cands[:k]]
    if state is not None:
        # "memory": the profile and daily targets are always given to the model, because almost every answer depends on them
        pinned = [SourceRef(id=c.id, title=c.title, snippet=c.text[:600], score=99.0) for c in user_chunks(state) if c.id in PINNED]
        out = pinned + out
    return out


def ids_for(query: str, k: int = 4) -> list[str]:
    return [r.id for r in retrieve(query, None, k)]


__all__ = ["retrieve", "kb_chunks", "user_chunks", "tokenize", "ids_for"]
