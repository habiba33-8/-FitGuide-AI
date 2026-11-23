from __future__ import annotations
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field
from ..calc.energy import FLOOR
from ..calc import nutrition as nut
from ..schemas import Plan, Profile
from . import library as lib
from .build import generate_plan, effective_profile
from .workout import DAY_NAMES, TEMPLATES, training_days_for

MUSCLES = ["chest", "back", "shoulders", "biceps", "triceps", "quads", "hamstrings", "glutes", "calves", "core", "forearms"]


class PlanChange(BaseModel):
    op: Literal["swap_exercise", "remove_exercise", "set_days", "set_equipment", "set_level", "set_approach", "set_calories",
                "adjust_calories", "set_diet_style", "exclude_food", "add_focus", "set_goal", "set_training_days", "move_day"]
    target: Optional[str] = None  # exercise or food name
    value: Optional[str] = None
    number: Optional[int] = None
    days: Optional[list[str]] = None  # weekday names for set_training_days, [from, to] for move_day


class ChangeResult(BaseModel):
    ok: bool
    message: str
    plan: Optional[Plan] = None


_DAY_ALIASES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
                "الاثنين": 0, "الإثنين": 0, "الاتنين": 0, "الثلاثاء": 1, "التلات": 1, "الثلاث": 1, "الأربعاء": 2, "الاربعاء": 2, "الأربع": 2, "الخميس": 3,
                "الجمعة": 4, "الجمعه": 4, "السبت": 5, "الأحد": 6, "الاحد": 6}


def parse_day(text) -> int | None:
    """'Monday', 'mon', 'sat', 'السبت' or a number 0-6 (0 = Monday) -> weekday index."""
    t = str(text).strip().lower()
    if t.isdigit():
        return int(t) if 0 <= int(t) <= 6 else None
    if t in _DAY_ALIASES:
        return _DAY_ALIASES[t]
    return _DAY_ALIASES.get(t[:3]) if t[:3] in ("mon", "tue", "wed", "thu", "fri", "sat", "sun") else None


_EN_DAYS = {"monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
            "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6}
_AR_DAYS = {"الاثنين": 0, "الاتنين": 0, "الإثنين": 0, "الثلاثاء": 1, "التلات": 1, "الثلاث": 1, "الاربعاء": 2, "الأربعاء": 2, "الاربع": 2, "الأربع": 2,
            "الخميس": 3, "الجمعة": 4, "الجمعه": 4, "السبت": 5, "الاحد": 6, "الأحد": 6}


def find_days_in_text(text: str) -> list[int]:
    """Weekdays mentioned in free text, in order, without repeats. Works for English and Arabic ('والسبت' too)."""
    import re
    found: list[int] = []
    for tok in re.findall(r"[\w\u0600-\u06FF]+", text.lower()):
        for t in (tok, tok[1:] if tok.startswith("و") else tok):
            d = _EN_DAYS.get(t, _AR_DAYS.get(t))
            if d is not None and d not in found:
                found.append(d)
                break
    return found


_CHANGE_WORDS = re.compile(r"change|set|switch|train|workout|move|make|want|غير|اغير|عدل|اتمرن|تمرين|انقل|خلي|عايز|عاوز|ايام|أيام", re.I)
_DAY_COUNT_RE = re.compile(
    r"\b(?P<count>[2-6]|two|three|four|five|six)\s*(?:days?|workouts?)(?:\s+(?:per|a)\s+week)?\b|"
    r"\b(?:days?|workouts?)\s+(?:to|=|:)\s*(?P<after>[2-6]|two|three|four|five|six)\b",
    re.I,
)
_DAY_COUNT_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def day_count_from_text(text: str, awaiting_days: bool = False) -> int | None:
    match = _DAY_COUNT_RE.search(text)
    if match:
        value = match.group("count") or match.group("after")
    elif awaiting_days:
        answer = re.fullmatch(r"\s*(2|3|4|5|6|two|three|four|five|six)(?:\s+days?)?\s*[.!]?\s*", text, re.I)
        if not answer:
            return None
        value = answer.group(1)
    else:
        return None
    return int(value) if value.isdigit() else _DAY_COUNT_WORDS[value.lower()]


def days_change_from_text(text: str, awaiting_days: bool = False) -> PlanChange | None:
    """Safety net: if the user clearly names 2+ weekdays and asks for a change, build the op in code, whatever the AI said."""
    days = find_days_in_text(text)
    if len(days) >= 2 and (_CHANGE_WORDS.search(text) or awaiting_days) and not re.search(r"\b(ate|eat|had|meal|lunch|dinner|breakfast)\b|اكلت|وجبة|غدا|عشا|فطار", text, re.I):
        return PlanChange(op="set_training_days", days=[DAY_NAMES[d].lower() for d in days])
    return None


def apply_change(profile: Profile, plan: Plan, change: PlanChange) -> ChangeResult:
    s = dict(plan.settings)
    p = effective_profile(profile, s)
    op = change.op
    note = ""
    if op in ("swap_exercise", "remove_exercise"):
        ex = lib.find_exercise(change.target or "")
        if not ex:
            return ChangeResult(ok=False, message=f"I could not find an exercise called '{change.target}' in your plan.")
        s["excluded_exercises"] = sorted(set(s.get("excluded_exercises", [])) | {ex["id"]})
        alt = lib.by_id().get(ex["alternative"])
        note = f"Replaced {ex['name']}" + (f" (a similar option is {alt['name']})" if alt and op == "swap_exercise" else "") + "." if op == "swap_exercise" else f"Removed {ex['name']} from your plan."
    elif op == "set_days":
        n = change.number
        if n is None or not 2 <= n <= 6:
            return ChangeResult(ok=False, message="Training days must be between 2 and 6.")
        s["days_per_week"] = n
        for k in ("training_days", "session_map", "approach"):
            s.pop(k, None)  # a plain count resets any weekdays chosen earlier
        note = f"Now training {n} days a week."
    elif op == "set_training_days":
        days = [parse_day(d) for d in (change.days or [])]
        if not days or any(d is None for d in days):
            return ChangeResult(ok=False, message="Tell me the weekdays you want to train on, for example Saturday, Tuesday and Thursday.")
        chosen = sorted(set(days))
        if not 2 <= len(chosen) <= 6:
            return ChangeResult(ok=False, message="Pick between 2 and 6 training days, so you get at least one rest day.")
        s["training_days"] = chosen
        s["days_per_week"] = len(chosen)
        s.pop("session_map", None)
        s.pop("approach", None)
        note = "Now training on " + ", ".join(DAY_NAMES[d] for d in chosen) + "."
    elif op == "move_day":
        pair = [parse_day(d) for d in (change.days or [])]
        if len(pair) != 2 or None in pair:
            return ChangeResult(ok=False, message="Tell me which day to move and which day to move it to, for example from Wednesday to Thursday.")
        src, dst = pair
        current = sorted(d.day for d in plan.workouts if not d.rest)
        if src not in current:
            return ChangeResult(ok=False, message=f"{DAY_NAMES[src]} is a rest day in your plan, so there is no workout to move.")
        if src == dst:
            return ChangeResult(ok=False, message=f"The workout is already on {DAY_NAMES[src]}.")
        if dst in current:
            return ChangeResult(ok=False, message=f"You already train on {DAY_NAMES[dst]}. Pick a rest day, or ask me to set your training days.")
        smap = {int(k): v for k, v in s.get("session_map", {}).items()} or {d: i for i, d in enumerate(current)}
        smap[dst] = smap.pop(src)
        s["session_map"] = smap
        s["training_days"] = sorted((set(current) - {src}) | {dst})
        s["days_per_week"] = len(current)
        note = f"Moved your {DAY_NAMES[src]} workout to {DAY_NAMES[dst]}."
    elif op == "set_equipment":
        v = (change.value or "").lower()
        mode = "without_machine" if ("without" in v or "no_machine" in v or "home" in v or "bodyweight" in v) else "with_machine" if ("with" in v or "gym" in v or "machine" in v) else "both" if "both" in v else None
        if not mode:
            return ChangeResult(ok=False, message="Equipment must be: with machines, without machines, or both.")
        s["equipment"] = mode
        note = {"with_machine": "Using gym machines and weights.", "without_machine": "No machines: bodyweight, dumbbells and bands only.", "both": "Using both machines and no-machine exercises."}[mode]
    elif op == "set_level":
        v = (change.value or "").lower()
        if v not in lib.LEVELS:
            return ChangeResult(ok=False, message="Level must be beginner, intermediate or advanced.")
        s["level"] = v
        note = f"Level set to {v}."
    elif op == "set_approach":
        v = (change.value or "").lower().replace(" ", "_").replace("/", "_")
        v = {"push_pull_legs": "ppl", "fullbody": "full_body", "bodyweight": "home", "upper_lower": "upper_lower", "upperlower": "upper_lower"}.get(v, v)
        if v not in TEMPLATES:
            return ChangeResult(ok=False, message=f"Available approaches: {', '.join(TEMPLATES)}.")
        s["approach"] = v
        note = f"Training approach changed to {TEMPLATES[v]['name']}."
    elif op in ("set_calories", "adjust_calories"):
        base = generate_plan(profile, plan.week_index, {**s, "calories": None, "calorie_delta": 0}).targets
        if op == "set_calories":
            if change.number is None:
                return ChangeResult(ok=False, message="Tell me the calorie number you want.")
            new = change.number
        else:
            if change.number is None:
                return ChangeResult(ok=False, message="Tell me how many calories to add or remove.")
            new = plan.targets.calories + change.number
        floor = FLOOR[p.sex]
        if new < floor:
            return ChangeResult(ok=False, message=f"I can not set calories below {floor} kcal. That is the safe minimum without a doctor or dietitian.")
        if new > base.tdee * 1.35:
            return ChangeResult(ok=False, message="That is too far above your estimated daily energy use. Pick a smaller number.")
        s["calories"] = int(round(new / 10) * 10)
        s.pop("calorie_delta", None)
        note = f"Calories set to about {s['calories']} kcal a day."
    elif op == "set_diet_style":
        v = (change.value or "").lower().replace(" ", "_").replace("-", "_")
        v = {"highprotein": "high_protein", "lowcarb": "low_carb", "veg": "vegetarian"}.get(v, v)
        if v not in ("balanced", "high_protein", "low_carb", "vegetarian"):
            return ChangeResult(ok=False, message="Diet style must be balanced, high protein, low carb or vegetarian.")
        s["diet_style"] = v
        note = f"Diet style changed to {v.replace('_', ' ')}."
    elif op == "exclude_food":
        f = nut.find_food(change.target or "", min_score=0.7)
        name = f["name"] if f else (change.target or "").strip()
        if not name:
            return ChangeResult(ok=False, message="Which food should I remove?")
        s["excluded_foods"] = sorted(set(s.get("excluded_foods", [])) | {name})
        note = f"Removed {name} from your meals."
    elif op == "add_focus":
        m = (change.target or change.value or "").lower().strip()
        m = {"abs": "core", "arms": "biceps", "legs": "quads", "butt": "glutes", "glute": "glutes", "bicep": "biceps", "tricep": "triceps", "shoulder": "shoulders", "calf": "calves"}.get(m, m)
        if m not in MUSCLES:
            return ChangeResult(ok=False, message=f"I can focus on: {', '.join(MUSCLES)}.")
        s["focus"] = sorted(set(s.get("focus", [])) | {m})
        note = f"Added extra {m} work."
    elif op == "set_goal":
        v = (change.value or "").lower().replace(" ", "_")
        v = {"lose_weight": "lose_fat", "fat_loss": "lose_fat", "muscle_gain": "build_muscle", "gain_muscle": "build_muscle", "bulk": "build_muscle", "cut": "lose_fat"}.get(v, v)
        if v not in ("lose_fat", "build_muscle", "maintain", "improve_fitness"):
            return ChangeResult(ok=False, message="Goal must be lose fat, build muscle, maintain or improve fitness.")
        s["goal"] = v
        s.pop("calories", None)
        s.pop("calorie_delta", None)
        note = f"Goal changed to {v.replace('_', ' ')}. Calories were recalculated."
    new_plan = generate_plan(profile, plan.week_index, s, changes=[note], status="approved")
    return ChangeResult(ok=True, message=note, plan=new_plan)
