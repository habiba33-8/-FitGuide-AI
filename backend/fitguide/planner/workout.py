from __future__ import annotations
from ..schemas import Profile, PlanExercise, WorkoutDay
from . import library as lib

SCHEDULE = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 3, 4, 5], 6: [0, 1, 2, 3, 4, 5]}
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# A slot asks for "one exercise for these muscles/patterns". The planner fills it from the library.
S = lambda title, muscles=None, patterns=None: dict(title=title, muscles=muscles, patterns=patterns)

TEMPLATES = {
    "full_body": {
        "name": "Full body",
        "days": [
            ("Full body A", [S("squat", ["quads"], ["squat"]), S("push", ["chest"], ["push"]), S("pull", ["back"], ["pull"]), S("hinge", ["hamstrings", "glutes"], ["hinge"]), S("core", ["core"], ["core"])]),
            ("Full body B", [S("lunge", ["quads", "glutes"], ["lunge", "squat"]), S("shoulders", ["shoulders"], ["push"]), S("pull", ["back"], ["pull"]), S("glutes", ["glutes"], ["hinge", "isolation"]), S("core", ["core"], ["core"])]),
            ("Full body C", [S("squat", ["quads"], ["squat", "lunge"]), S("push", ["chest"], ["push", "isolation"]), S("pull", ["back"], ["pull"]), S("arms", ["biceps", "triceps"], ["isolation"]), S("core", ["core"], ["core"])]),
        ],
    },
    "upper_lower": {
        "name": "Upper / Lower",
        "days": [
            ("Upper A", [S("chest", ["chest"], ["push"]), S("back", ["back"], ["pull"]), S("shoulders", ["shoulders"], ["push"]), S("biceps", ["biceps"], ["isolation"]), S("triceps", ["triceps"], ["isolation", "push"])]),
            ("Lower A", [S("quads", ["quads"], ["squat"]), S("hamstrings", ["hamstrings"], ["hinge", "isolation"]), S("glutes", ["glutes"], ["hinge", "lunge"]), S("calves", ["calves"], None), S("core", ["core"], ["core"])]),
            ("Upper B", [S("back", ["back"], ["pull"]), S("chest", ["chest"], ["push", "isolation"]), S("rear delts", ["shoulders", "back"], ["isolation", "pull"]), S("biceps", ["biceps"], ["isolation"]), S("triceps", ["triceps"], ["isolation", "push"])]),
            ("Lower B", [S("quads", ["quads"], ["lunge", "squat", "isolation"]), S("hamstrings", ["hamstrings"], ["hinge"]), S("glutes", ["glutes"], ["hinge", "isolation"]), S("calves", ["calves"], None), S("core", ["core"], ["core"])]),
        ],
    },
    "ppl": {
        "name": "Push / Pull / Legs",
        "days": [
            ("Push", [S("chest", ["chest"], ["push"]), S("chest 2", ["chest"], ["push", "isolation"]), S("shoulders", ["shoulders"], ["push"]), S("side delts", ["shoulders"], ["isolation"]), S("triceps", ["triceps"], ["isolation", "push"])]),
            ("Pull", [S("back", ["back"], ["pull"]), S("back 2", ["back"], ["pull", "hinge"]), S("rear delts", ["shoulders", "back"], ["isolation", "pull"]), S("biceps", ["biceps"], ["isolation"]), S("biceps 2", ["biceps"], ["isolation"])]),
            ("Legs", [S("quads", ["quads"], ["squat"]), S("hamstrings", ["hamstrings"], ["hinge"]), S("quads 2", ["quads"], ["lunge", "isolation", "squat"]), S("glutes", ["glutes"], ["hinge", "isolation", "lunge"]), S("calves", ["calves"], None)]),
        ],
    },
}
TEMPLATES["home"] = {**TEMPLATES["full_body"], "name": "Home / bodyweight"}

APPROACH_INFO = {
    "full_body": "Trains your whole body each session. Best for beginners and 2 to 3 days a week.",
    "upper_lower": "Alternates upper and lower body days so each muscle is trained twice a week. Best for 4 days.",
    "ppl": "Push, pull and legs days. Best for 5 to 6 days a week and intermediate or advanced lifters.",
    "home": "Full body plan that needs no machines: bodyweight, dumbbells and bands.",
}


def choose_approach(p: Profile, override: str | None = None) -> str:
    if override in TEMPLATES:
        return override
    if p.equipment == "without_machine":
        return "home" if p.days_per_week <= 3 else "upper_lower"
    if p.days_per_week <= 3:
        return "full_body"
    if p.days_per_week == 4:
        return "upper_lower"
    return "ppl"


def sets_reps(p: Profile, slot_index: int, muscle: str, pattern: str, bump: int, deload: bool) -> tuple[int, str]:
    base_sets = {"beginner": 2, "intermediate": 3, "advanced": 4}[p.level]
    compound = pattern in ("squat", "hinge", "push", "pull", "lunge") and slot_index < 3
    sets = base_sets + (1 if compound and p.level != "beginner" and bump >= 1 else 0)
    if p.level == "beginner" and compound and bump >= 2:
        sets = 3
    reps = "8-12" if compound else "10-15"
    if p.goal == "lose_fat" and not compound:
        reps = "12-15"
    if p.goal == "build_muscle" and compound:
        reps = "6-10" if p.level != "beginner" else "8-12"
    if muscle == "cardio":
        return 1, "10-20 min"
    if pattern == "core":
        return (max(1, round(base_sets * 0.6)) if deload else base_sets), "30-45 s"
    if deload:
        sets = max(1, round(sets * 0.6))
    return sets, reps


def training_days_for(p: Profile, settings: dict) -> list[int]:
    """Weekdays (0 = Monday) the user trains on: their own choice from chat, or a sensible default spread."""
    chosen = sorted({int(d) for d in settings.get("training_days", []) if 0 <= int(d) <= 6})
    return chosen if 2 <= len(chosen) <= 6 else SCHEDULE[p.days_per_week]


def build_workouts(p: Profile, approach: str, week_index: int, settings: dict) -> list[WorkoutDay]:
    tmpl = TEMPLATES[approach]
    exclude = set(settings.get("excluded_exercises", [])) | lib.injury_excludes(p.injuries)
    focus = settings.get("focus", [])
    bump = int(settings.get("volume_bump", 0))
    deload = bool(settings.get("deload", False))
    equipment = "without_machine" if approach == "home" else p.equipment
    days = training_days_for(p, settings)
    session_map = {int(k): v for k, v in settings.get("session_map", {}).items()}  # weekday -> which session of the template
    out: dict[int, WorkoutDay] = {}
    used_global: dict[str, int] = {}
    for rank, day_index in enumerate(days):
        n = session_map.get(day_index, rank)  # moving a day keeps its session (same exercises)
        title, slots = tmpl["days"][n % len(tmpl["days"])]
        if approach == "ppl" and p.days_per_week == 5 and n >= 3:
            title, slots = tmpl["days"][n - 3]  # 5 days: PPL + Push/Pull
        chosen: list[PlanExercise] = []
        used: set[str] = set()
        for si, slot in enumerate(slots):
            cands = lib.candidates(muscles=slot["muscles"], patterns=slot["patterns"], level=p.level, equipment=equipment, exclude=exclude | used)
            if not cands and slot["patterns"]:  # relax the pattern but keep the muscle
                cands = lib.candidates(muscles=slot["muscles"], level=p.level, equipment=equipment, exclude=exclude | used)
            if not cands:
                continue
            # rotation: later weeks and days pick different exercises so the plan does not get stale
            fresh = sorted(cands, key=lambda e: used_global.get(e["id"], 0))
            e = fresh[(week_index - 1 + n) % min(len(fresh), 3)] if len(fresh) > 1 else fresh[0]
            used.add(e["id"])
            used_global[e["id"]] = used_global.get(e["id"], 0) + 1
            sets, reps = sets_reps(p, si, e["muscle"], e["pattern"], bump, deload)
            rest = 120 if e["pattern"] in ("squat", "hinge") and e["equipment"] == "barbell" else 90 if e["pattern"] in ("squat", "hinge", "push", "pull") else 60
            chosen.append(PlanExercise(exercise_id=e["id"], name=e["name"], sets=sets, reps=reps, rest_s=rest, video=e["video"]["url"]))
        # focus muscles requested via chat get one extra exercise
        for m in focus:
            cands = lib.candidates(muscles=[m], level=p.level, equipment=equipment, exclude=exclude | used)
            if cands and (n % 2 == 0 or len(days) <= 3):
                e = cands[(week_index + n) % len(cands)]
                used.add(e["id"])
                sets, reps = sets_reps(p, 3, e["muscle"], "isolation", bump, deload)
                chosen.append(PlanExercise(exercise_id=e["id"], name=e["name"], sets=sets, reps=reps, rest_s=60, video=e["video"]["url"]))
        if p.goal in ("lose_fat", "improve_fitness"):
            cardio = lib.candidates(muscles=["cardio"], level=p.level, equipment=equipment, exclude=exclude | used)
            if cardio:
                c = cardio[(week_index + n) % len(cardio)]
                chosen.append(PlanExercise(exercise_id=c["id"], name=c["name"], sets=1, reps="10-20 min", rest_s=0, video=c["video"]["url"]))
        out[day_index] = WorkoutDay(day=day_index, title=title, focus=sorted({lib.by_id()[x.exercise_id]["muscle"] for x in chosen}), exercises=chosen)
    return [out.get(d) or WorkoutDay(day=d, title="Rest day" if d not in days else "", rest=True) for d in range(7)]
