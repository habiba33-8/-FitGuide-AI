import json, re
from fitguide.calc.energy import compute_targets, bmr, FLOOR
from fitguide.calc import nutrition as nut
from fitguide.planner import library as lib
from fitguide.planner import diet
from fitguide.schemas import Profile


def test_bmr_mifflin(profile):
    # 10*62 + 6.25*165 - 5*22 - 161 = 1380.25
    assert round(bmr(profile), 1) == 1380.2 or round(bmr(profile), 1) == 1380.3


def test_targets_consistent(profile):
    t = compute_targets(profile)
    assert t.calories < t.tdee  # fat loss = deficit
    assert abs((t.protein_g * 4 + t.carbs_g * 4 + t.fat_g * 9) - t.calories) < 60
    assert t.calories >= FLOOR["female"]


def test_floor_enforced():
    p = Profile(sex="female", age=60, height_cm=140, weight_kg=40, goal="lose_fat", activity="sedentary")
    assert compute_targets(p).calories >= 1200


def test_safety_flags():
    p = Profile(age=30, height_cm=170, weight_kg=70, conditions=["I have Diabetes"])
    assert compute_targets(p).safety_flags
    assert Profile(age=16, height_cm=170, weight_kg=60) and compute_targets(Profile(age=16, height_cm=170, weight_kg=60)).safety_flags


def test_food_lookup_english_arabic_alias():
    assert nut.find_food("koshari")["id"] == "koshary"
    assert nut.find_food("كشري")["id"] == "koshary"
    assert nut.find_food("falafel")["id"] == "taameya"
    assert nut.find_food("xyzzy unknown dish") is None


def test_item_math():
    i = nut.item_for("boiled_egg", 100)
    assert i.kcal == 155 and i.protein == 12.6


def test_food_table_integrity():
    for f in nut.foods().values():
        m = f["per100g"]
        est = m["protein"] * 4 + m["carbs"] * 4 + m["fat"] * 9
        if m["kcal"] > 40:
            assert abs(est - m["kcal"]) / m["kcal"] < 0.25, f["id"]


def test_meal_templates_reference_real_foods():
    for slot, ts in diet.T.items():
        for tid, tags, items in ts:
            for fid, g in items:
                assert fid in nut.foods(), (tid, fid)
    for ids in diet.ALLERGENS.values():
        assert ids <= set(nut.foods()), ids - set(nut.foods())


def test_exercise_library_integrity():
    ex = lib.exercises()
    assert len(ex) >= 60
    ids = {e["id"] for e in ex}
    for e in ex:
        assert e["alternative"] in ids, e["id"]
        assert e["mode"] in ("with_machine", "without_machine")
        assert e["level"] in lib.LEVELS
        assert re.match(r"https://www\.youtube\.com/(watch\?v=[\w-]{11}|results\?search_query=)", e["video"]["url"]), e["id"]
        assert len(e["cues"]) >= 2
    verified = sum(1 for e in ex if e["video"]["verified"])
    assert verified / len(ex) > 0.9
