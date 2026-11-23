"""generate_plan(): the single entry point that builds a Plan from a profile + settings."""
from __future__ import annotations
import hashlib
from ..calc.energy import compute_targets
from ..schemas import Plan, Profile
from . import workout, diet


def effective_profile(p: Profile, settings: dict) -> Profile:
    """Chat requests are stored in `settings` and layered on top of the profile the user typed in."""
    patch = {}
    if settings.get("equipment"):
        patch["equipment"] = settings["equipment"]
    if settings.get("days_per_week"):
        patch["days_per_week"] = settings["days_per_week"]
    if settings.get("level"):
        patch["level"] = settings["level"]
    if settings.get("diet_style"):
        patch["diet_style"] = settings["diet_style"]
    if settings.get("goal"):
        patch["goal"] = settings["goal"]
    return p.model_copy(update=patch) if patch else p


def generate_plan(profile: Profile, week_index: int = 1, settings: dict | None = None, changes: list[str] | None = None,
                  status: str = "draft") -> Plan:
    settings = dict(settings or {})
    p = effective_profile(profile, settings)
    approach = workout.choose_approach(p, settings.get("approach"))
    base = compute_targets(p)
    override = None
    if settings.get("calorie_delta"):
        override = base.calories + int(settings["calorie_delta"])
    if settings.get("calories"):
        override = int(settings["calories"])
    targets = compute_targets(p, override) if override else base
    workouts = workout.build_workouts(p, approach, week_index, settings)
    meals = diet.build_diet(p, targets, week_index, settings)
    n_train = sum(1 for w in workouts if not w.rest)
    summary = (f"Week {week_index}: {n_train} training days ({workout.TEMPLATES[approach]['name']}) and about "
               f"{targets.calories} kcal a day with {targets.protein_g} g protein.")
    rationale = [
        f"Approach: {workout.TEMPLATES[approach]['name']}. {workout.APPROACH_INFO[approach]}",
        f"Calories: your estimated maintenance is {targets.tdee} kcal. {' '.join(targets.notes)}",
        f"Protein: {targets.protein_g} g a day, about {targets.protein_g / p.weight_kg:.1f} g per kg of body weight.",
    ]
    pid = hashlib.sha1(f"{p.model_dump_json()}|{week_index}|{sorted(settings.items())}".encode()).hexdigest()[:10]
    return Plan(plan_id=pid, week_index=week_index, status=status, approach=approach, approach_name=workout.TEMPLATES[approach]["name"],
                summary=summary, workouts=workouts, diet=meals, targets=targets, rationale=rationale, changes=changes or [], settings=settings)
