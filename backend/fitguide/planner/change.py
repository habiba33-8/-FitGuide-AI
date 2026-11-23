"""Chat-driven plan changes. The LLM proposes a change as JSON; THIS code validates and applies it.
That keeps the model creative but the plan safe: it can never write meals or exercises directly."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
from ..calc.energy import FLOOR
from ..calc import nutrition as nut
from ..schemas import Plan, Profile
from . import library as lib
from .build import generate_plan, effective_profile
from .workout import TEMPLATES

MUSCLES = ["chest", "back", "shoulders", "biceps", "triceps", "quads", "hamstrings", "glutes", "calves", "core", "forearms"]


class PlanChange(BaseModel):
    op: Literal["swap_exercise", "remove_exercise", "set_days", "set_equipment", "set_level", "set_approach", "set_calories",
                "adjust_calories", "set_diet_style", "exclude_food", "add_focus", "set_goal"]
    target: Optional[str] = None  # exercise or food name
    value: Optional[str] = None
    number: Optional[int] = None


class ChangeResult(BaseModel):
    ok: bool
    message: str
    plan: Optional[Plan] = None


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
        s.pop("approach", None)
        note = f"Now training {n} days a week."
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
