"""Plan constraint evaluation: generate plans for a grid of profiles and check hard rules. No model involved:
the planner is deterministic, so these are checks of correctness and safety, not of 'quality'.
Run:  python -m evals.plan_eval"""
from __future__ import annotations
import itertools, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fitguide.calc.energy import FLOOR
from fitguide.planner import library as lib
from fitguide.planner.build import generate_plan, effective_profile
from fitguide.schemas import Profile

BANNED = {"dairy": {"milk_whole", "milk_skim", "yogurt_plain", "greek_yogurt", "cottage_cheese", "cheddar", "butter", "feta_cheese", "roumi_cheese", "labneh", "whey_protein"}}


def profiles():
    for sex, goal, level, eq, days, diet, wt in itertools.product(
            ["female", "male"], ["lose_fat", "build_muscle", "maintain", "improve_fitness"], ["beginner", "intermediate", "advanced"],
            ["with_machine", "without_machine", "both"], [2, 3, 4, 5, 6], ["balanced", "high_protein", "low_carb", "vegetarian"], [52, 85]):
        extra = {}
        if (days + wt) % 3 == 0:
            extra["injuries"] = ["knee"]
        if (days + wt) % 4 == 0:
            extra["allergies"] = ["dairy"]
        yield Profile(sex=sex, goal=goal, level=level, equipment=eq, days_per_week=days, diet_style=diet, weight_kg=wt,
                      height_cm=160 if sex == "female" else 178, age=25, **extra)


def check(p: Profile) -> list[str]:
    pl = generate_plan(p)
    ep = effective_profile(p, pl.settings)
    fails = []
    if sum(1 for w in pl.workouts if not w.rest) != p.days_per_week:
        fails.append("training_days")
    ex = [lib.by_id()[e.exercise_id] for w in pl.workouts for e in w.exercises]
    if p.equipment == "without_machine" and any(e["mode"] != "without_machine" for e in ex):
        fails.append("equipment")
    if any(lib.LEVELS[e["level"]] > lib.LEVELS[p.level] for e in ex):
        fails.append("level")
    if p.injuries and any(e["id"] in lib.injury_excludes(p.injuries) for e in ex):
        fails.append("injury")
    if any(not w.rest and len(w.exercises) < 4 for w in pl.workouts):
        fails.append("too_few_exercises")
    t = pl.targets
    if t.calories < FLOOR[p.sex]:
        fails.append("calorie_floor")
    if any(abs(d.kcal - t.calories) / t.calories > 0.12 for d in pl.diet):
        fails.append("calories_within_12pct")
    if sum(d.protein for d in pl.diet) / 7 < 0.8 * t.protein_g:
        fails.append("protein_80pct")
    if p.allergies and any(i.food_id in BANNED["dairy"] for d in pl.diet for m in d.meals for i in m.items):
        fails.append("allergy")
    return fails


def run() -> dict:
    from collections import Counter
    total, bad, c = 0, 0, Counter()
    for p in profiles():
        total += 1
        f = check(p)
        bad += bool(f)
        c.update(f)
    return {"profiles_tested": total, "profiles_with_any_failure": bad, "pass_rate": round(1 - bad / total, 4), "failures_by_rule": dict(c)}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
