import pytest
from fitguide.planner.build import generate_plan
from fitguide.planner.change import PlanChange, apply_change
from fitguide.planner.adapt import renew_plan
from fitguide.planner import library as lib
from fitguide.schemas import Profile, WeekProgress, DayProgress


def mk(**kw):
    d = dict(age=24, sex="female", height_cm=168, weight_kg=64, goal="lose_fat", level="beginner", equipment="both", days_per_week=3)
    d.update(kw)
    return Profile(**d)


@pytest.mark.parametrize("days", [2, 3, 4, 5, 6])
def test_training_days_match(days):
    pl = generate_plan(mk(days_per_week=days))
    assert sum(1 for w in pl.workouts if not w.rest) == days
    assert len(pl.workouts) == 7 and len(pl.diet) == 7


@pytest.mark.parametrize("equipment,mode", [("without_machine", "without_machine")])
def test_equipment_respected(equipment, mode):
    pl = generate_plan(mk(equipment=equipment, days_per_week=4))
    for w in pl.workouts:
        for e in w.exercises:
            assert lib.by_id()[e.exercise_id]["mode"] == mode


def test_level_respected():
    pl = generate_plan(mk(level="beginner", days_per_week=5))
    for w in pl.workouts:
        for e in w.exercises:
            assert lib.LEVELS[lib.by_id()[e.exercise_id]["level"]] == 0


def test_injury_avoided():
    pl = generate_plan(mk(injuries=["knee pain"], level="intermediate"))
    bad = lib.injury_excludes(["knee pain"])
    assert all(e.exercise_id not in bad for w in pl.workouts for e in w.exercises)


@pytest.mark.parametrize("kw", [dict(), dict(goal="build_muscle", sex="male", weight_kg=80, height_cm=180), dict(diet_style="vegetarian"), dict(diet_style="low_carb")])
def test_diet_hits_calories(kw):
    pl = generate_plan(mk(**kw))
    for d in pl.diet:
        assert abs(d.kcal - pl.targets.calories) / pl.targets.calories < 0.12, (kw, d.kcal, pl.targets.calories)


def test_allergy_and_dislike_respected():
    pl = generate_plan(mk(allergies=["dairy", "nuts"], dislikes=["tuna"]))
    banned = {"milk_whole", "greek_yogurt", "feta_cheese", "almonds", "walnuts", "tuna_canned", "cheddar", "cottage_cheese", "peanut_butter"}
    assert all(i.food_id not in banned for d in pl.diet for m in d.meals for i in m.items)


def test_vegetarian_has_no_meat():
    pl = generate_plan(mk(diet_style="vegetarian"))
    meat = {"chicken_breast_grilled", "chicken_thigh", "beef_steak", "kofta", "tuna_canned", "salmon", "white_fish", "shrimp"}
    assert all(i.food_id not in meat for d in pl.diet for m in d.meals for i in m.items)


def test_plan_is_deterministic():
    p = mk()
    assert generate_plan(p).model_dump() == generate_plan(p).model_dump()


def test_change_swap_and_remove():
    p = mk()
    pl = generate_plan(p)
    r = apply_change(p, pl, PlanChange(op="swap_exercise", target="push up"))
    assert r.ok and all(e.exercise_id != "push_up" for w in r.plan.workouts for e in w.exercises)
    assert not apply_change(p, pl, PlanChange(op="remove_exercise", target="zzz not an exercise")).ok


def test_change_calorie_floor_and_ceiling():
    p = mk()
    pl = generate_plan(p)
    assert not apply_change(p, pl, PlanChange(op="set_calories", number=800)).ok
    assert not apply_change(p, pl, PlanChange(op="set_calories", number=9000)).ok
    ok = apply_change(p, pl, PlanChange(op="set_calories", number=1800))
    assert ok.ok and ok.plan.targets.calories == 1800


def test_change_days_and_approach_and_food():
    p = mk()
    pl = generate_plan(p)
    r = apply_change(p, pl, PlanChange(op="set_days", number=5))
    assert sum(1 for w in r.plan.workouts if not w.rest) == 5
    assert not apply_change(p, pl, PlanChange(op="set_days", number=9)).ok
    r = apply_change(p, pl, PlanChange(op="exclude_food", target="eggs"))
    assert all(i.food_id not in {"boiled_egg", "fried_eggs", "beid_omelette"} for d in r.plan.diet for m in d.meals for i in m.items)
    assert apply_change(p, pl, PlanChange(op="set_approach", value="push pull legs")).plan.approach == "ppl"


def test_renew_progression_and_deload():
    p = mk()
    pl = generate_plan(p)
    good = WeekProgress(days=[DayProgress(day=i, workout_done=True, kcal=1500) for i in (0, 2, 4)], start_weight_kg=64, end_weight_kg=63.7)
    n = renew_plan(p, pl, good)
    assert n.week_index == 2 and n.settings["volume_bump"] == 1 and n.status == "draft"
    w3 = renew_plan(p, n, good)
    w4 = renew_plan(p, w3, good)
    assert w4.settings["deload"] is True


def test_renew_easier_when_missed():
    p = mk()
    pl = generate_plan(p)
    pl.settings["volume_bump"] = 2
    n = renew_plan(p, pl, WeekProgress(days=[DayProgress(day=0, workout_done=True)]))
    assert n.settings["volume_bump"] == 1


def test_renew_calories_respect_floor():
    p = mk(weight_kg=45, height_cm=150, age=40, activity="sedentary")
    pl = generate_plan(p)
    prog = WeekProgress(days=[DayProgress(day=i, workout_done=True, kcal=1200) for i in range(5)], start_weight_kg=45, end_weight_kg=45.5)
    n = renew_plan(p, pl, prog)
    assert n.targets.calories >= 1200
