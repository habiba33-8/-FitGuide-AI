"""Weekly renewal: reads last week's progress and decides how next week's plan changes.

Rules are simple on purpose so a user (and a reviewer) can read them:
1. Training load: adherence >= 80% and not "too hard" -> small progression. < 50% or "too hard" -> make it easier.
2. Every 4th week is a deload week (about 40% less volume).
3. Calories: compare the real weekly weight change with the safe range for the goal. Outside the range -> +/-100 kcal.
   Never below the safe floor, never more than 300 kcal away from the original target."""
from __future__ import annotations
from ..calc.energy import FLOOR
from ..schemas import Plan, Profile, WeekProgress
from .build import generate_plan

GOAL_RANGE = {  # expected weekly change as a fraction of body weight (min, max)
    "lose_fat": (-0.010, -0.0025),
    "build_muscle": (0.001, 0.005),
    "maintain": (-0.004, 0.004),
    "improve_fitness": (-0.004, 0.004),
}


def adherence(progress: WeekProgress, plan: Plan) -> float:
    planned = sum(1 for w in plan.workouts if not w.rest)
    if planned == 0:
        return 1.0
    done = sum(1 for d in progress.days if d.workout_done)
    return min(1.0, done / planned)


def renew_plan(profile: Profile, plan: Plan, progress: WeekProgress) -> Plan:
    settings = dict(plan.settings)
    changes: list[str] = []
    week = plan.week_index + 1
    adh = adherence(progress, plan)
    bump = int(settings.get("volume_bump", 0))

    if progress.felt == "too_hard" or adh < 0.5:
        bump = max(0, bump - 1)
        changes.append(f"You completed {round(adh * 100)}% of workouts" + (" and it felt too hard" if progress.felt == "too_hard" else "") + ". Training load is kept easier this week so you can build the habit.")
    elif adh >= 0.8 or progress.felt == "too_easy":
        if bump < 3:
            bump += 1
            changes.append(f"You completed {round(adh * 100)}% of workouts" + (" and it felt too easy" if progress.felt == "too_easy" else "") + ". Added a bit more training volume (progressive overload).")
        else:
            changes.append("You are already at the top volume level. Keep the same load and try to add reps or weight inside each set.")
    else:
        changes.append(f"You completed {round(adh * 100)}% of workouts. Training stays the same this week.")
    settings["volume_bump"] = bump

    deload = week % 4 == 0
    settings["deload"] = deload
    if deload:
        changes.append("Week 4 of the cycle is a deload week: about 40% less volume so your body can recover.")

    # calories vs weight trend
    logged_days = sum(1 for d in progress.days if d.kcal)
    if progress.start_weight_kg and progress.end_weight_kg and logged_days >= 4:
        change = (progress.end_weight_kg - progress.start_weight_kg) / progress.start_weight_kg
        lo, hi = GOAL_RANGE[profile.goal]
        delta = int(settings.get("calorie_delta", 0))
        if change > hi and profile.goal in ("lose_fat",):
            delta -= 100
            changes.append(f"Weight changed {change * 100:+.1f}% which is slower than your fat-loss range. Calories -100 kcal.")
        elif change < lo and profile.goal == "lose_fat":
            delta += 100
            changes.append(f"Weight changed {change * 100:+.1f}% which is faster than the safe range. Calories +100 kcal.")
        elif change < lo and profile.goal == "build_muscle":
            delta += 100
            changes.append(f"Weight changed {change * 100:+.1f}% which is slower than your muscle-gain range. Calories +100 kcal.")
        elif change > hi and profile.goal == "build_muscle":
            delta -= 100
            changes.append(f"Weight changed {change * 100:+.1f}% which is faster than planned, so extra gain may be fat. Calories -100 kcal.")
        elif not (lo <= change <= hi) and profile.goal in ("maintain", "improve_fitness"):
            delta += -100 if change > hi else 100
            changes.append(f"Weight changed {change * 100:+.1f}%. Calories adjusted by {-100 if change > hi else 100} kcal to keep it steady.")
        else:
            changes.append(f"Weight changed {change * 100:+.1f}%, which is inside the expected range. Calories stay the same.")
        delta = max(-300, min(300, delta))
        settings["calorie_delta"] = delta
        floor = FLOOR[profile.sex]
        base = generate_plan(profile, week, {**settings, "calorie_delta": 0}).targets.calories
        if base + delta < floor:
            settings["calorie_delta"] = floor - base
            changes.append(f"Calories can not go below the safe minimum of {floor} kcal.")
    else:
        changes.append("Not enough weight or food logs to adjust calories, so they stay the same. Log weight at the start and end of the week and food on at least 4 days.")
    return generate_plan(profile, week, settings, changes=changes)
