"""Diet planner: builds a 7 day meal plan that hits the calorie target.

Idea: a library of simple meal templates (foods + base grams). For every slot we pick a template that fits the
user's diet style, allergies and dislikes, then scale all portions with ONE factor so the meal lands on the slot's
calorie target. Calories and macros are computed from the food table (calc/nutrition.py), never by the LLM."""
from __future__ import annotations
from ..calc import nutrition as nut
from ..schemas import DietDay, DietMeal, Profile, Targets

SLOT_SHARE = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.15, "dinner": 0.25}

# (template id, tags, [(food_id, grams)])  tags: veg = vegetarian ok, lc = suits low carb, hp = protein rich
T = {
    "breakfast": [
        ("b_ful", {"veg"}, [("ful_medames", 200), ("aish_baladi", 80), ("tomato", 100), ("boiled_egg", 50)]),
        ("b_oats", {"veg"}, [("oats", 50), ("milk_whole", 250), ("banana", 118), ("peanut_butter", 16)]),
        ("b_eggs_cheese", {"veg", "hp"}, [("boiled_egg", 100), ("bread_whole", 60), ("cucumber", 100), ("feta_cheese", 30)]),
        ("b_greek", {"veg", "hp"}, [("greek_yogurt", 200), ("oats", 40), ("strawberries", 100), ("almonds", 15)]),
        ("b_omelette", {"veg", "hp"}, [("beid_omelette", 120), ("aish_baladi", 60), ("tomato_cucumber_salad", 150)]),
        ("b_shakshuka", {"veg"}, [("shakshuka", 250), ("aish_baladi", 60)]),
        ("b_lc_eggs", {"veg", "lc", "hp"}, [("boiled_egg", 150), ("avocado", 80), ("feta_cheese", 40), ("cucumber", 100)]),
    ],
    "lunch": [
        ("l_chicken_rice", {"hp"}, [("chicken_breast_grilled", 150), ("white_rice", 180), ("salad_green", 150), ("olive_oil", 7)]),
        ("l_fish_rice", {"hp"}, [("white_fish", 180), ("brown_rice", 150), ("spinach_cooked", 100), ("salad_green", 100)]),
        ("l_kofta", {"hp"}, [("kofta", 150), ("egyptian_rice", 150), ("tomato_cucumber_salad", 150)]),
        ("l_lentils", {"veg"}, [("lentils_cooked", 250), ("brown_rice", 120), ("salad_green", 150), ("olive_oil", 7)]),
        ("l_thigh_potato", {"hp"}, [("chicken_thigh", 150), ("potato_boiled", 200), ("broccoli", 100)]),
        ("l_tuna_pasta", {"hp"}, [("tuna_canned", 120), ("pasta", 180), ("salad_green", 100), ("olive_oil", 7)]),
        ("l_lc_steak", {"lc", "hp"}, [("beef_steak", 150), ("broccoli", 150), ("salad_green", 100), ("olive_oil", 10)]),
        ("l_chickpea_quinoa", {"veg"}, [("chickpeas_cooked", 200), ("quinoa", 150), ("tomato_cucumber_salad", 150)]),
        ("l_molokhia", {"hp"}, [("molokhia", 250), ("chicken_breast_grilled", 120), ("egyptian_rice", 120)]),
        ("l_lentil_egg", {"veg", "hp"}, [("lentils_cooked", 200), ("boiled_egg", 100), ("brown_rice", 100), ("salad_green", 100)]),
        ("l_tofu_quinoa", {"veg", "hp"}, [("tofu", 200), ("quinoa", 120), ("broccoli", 100), ("olive_oil", 7)]),
        ("l_veg_tofu", {"veg", "lc"}, [("tofu", 200), ("broccoli", 150), ("mixed_vegetables_cooked", 150), ("olive_oil", 10)]),
    ],
    "snack": [
        ("s_yogurt_apple", {"veg", "hp"}, [("greek_yogurt", 170), ("apple", 180), ("walnuts", 15)]),
        ("s_cottage", {"veg", "hp", "lc"}, [("cottage_cheese", 150), ("cucumber", 100), ("bread_whole", 30)]),
        ("s_banana_pb", {"veg"}, [("banana", 118), ("peanut_butter", 16), ("milk_skim", 250)]),
        ("s_nuts_dates", {"veg"}, [("almonds", 28), ("dates", 24)]),
        ("s_whey", {"veg", "hp"}, [("whey_protein", 30), ("banana", 118)]),
        ("s_hummus", {"veg"}, [("hummus", 60), ("carrot", 100), ("bread_whole", 30)]),
        ("s_lc_egg", {"veg", "lc", "hp"}, [("boiled_egg", 100), ("cucumber", 100), ("olive_oil", 5)]),
        ("s_lc_nuts", {"veg", "lc"}, [("walnuts", 28), ("cheddar", 28), ("cucumber", 100)]),
    ],
    "dinner": [
        ("d_lentils", {"veg"}, [("lentils_cooked", 250), ("tomato_cucumber_salad", 150), ("aish_baladi", 60)]),
        ("d_chicken_sweet", {"hp"}, [("chicken_breast_grilled", 130), ("sweet_potato", 150), ("zucchini_cooked", 120)]),
        ("d_tuna_salad", {"hp", "lc"}, [("tuna_canned", 120), ("salad_green", 150), ("bread_whole", 60), ("olive_oil", 7)]),
        ("d_ful_egg", {"veg"}, [("ful_medames", 200), ("boiled_egg", 50), ("salad_green", 100), ("aish_baladi", 60)]),
        ("d_salmon_quinoa", {"hp"}, [("salmon", 130), ("quinoa", 100), ("broccoli", 100)]),
        ("d_lc_shrimp", {"lc", "hp"}, [("shrimp", 150), ("zucchini_cooked", 150), ("salad_green", 100), ("olive_oil", 10), ("avocado", 50)]),
        ("d_tofu_rice", {"veg", "hp"}, [("tofu", 200), ("brown_rice", 120), ("mixed_vegetables_cooked", 150)]),
        ("d_cottage_eggs", {"veg", "hp", "lc"}, [("cottage_cheese", 200), ("boiled_egg", 100), ("tomato", 120), ("bread_whole", 60)]),
    ],
}

ALLERGENS = {
    "dairy": {"milk_whole", "milk_skim", "yogurt_plain", "greek_yogurt", "cottage_cheese", "cheddar", "butter", "feta_cheese", "roumi_cheese", "labneh", "whey_protein"},
    "lactose": {"milk_whole", "milk_skim", "yogurt_plain", "greek_yogurt", "cottage_cheese", "cheddar", "butter", "feta_cheese", "roumi_cheese", "labneh", "whey_protein"},
    "nuts": {"almonds", "walnuts", "peanuts", "peanut_butter"},
    "peanut": {"peanuts", "peanut_butter"},
    "egg": {"boiled_egg", "fried_eggs", "beid_omelette", "shakshuka"},
    "gluten": {"aish_baladi", "bread_white", "bread_whole", "pasta", "oats", "couscous", "cornflakes", "feteer"},
    "wheat": {"aish_baladi", "bread_white", "bread_whole", "pasta", "oats", "couscous", "cornflakes", "feteer"},
    "fish": {"tuna_canned", "salmon", "white_fish"},
    "shellfish": {"shrimp"},
    "seafood": {"tuna_canned", "salmon", "white_fish", "shrimp"},
    "soy": {"tofu"},
    "sesame": {"tahini", "hummus", "baba_ghanoush"},
}


def blocked_foods(p: Profile, settings: dict) -> set[str]:
    blocked: set[str] = set()
    for a in p.allergies:
        al = a.lower()
        for key, ids in ALLERGENS.items():
            if key in al:
                blocked |= ids
    for term in list(p.dislikes) + list(settings.get("excluded_foods", [])):
        t = term.lower().strip()
        if not t:
            continue
        f = nut.find_food(term, min_score=0.8)
        if f:
            blocked.add(f["id"])
        for key, ids in ALLERGENS.items():  # "eggs" blocks every egg dish, "milk" every dairy food
            if key in t or (t.rstrip("s") == key):
                blocked |= ids
        for fid, food in nut.foods().items():
            names = [food["name"].lower(), food["id"].replace("_", " ")] + [a.lower() for a in food["aliases"]]
            if any(t in n or (len(t) > 3 and n in t) for n in names):
                blocked.add(fid)
    return blocked


def _scaled(items: list[tuple[str, float]], kcal_target: float):
    base = sum(nut.item_for(f, g).kcal for f, g in items) or 1
    factor = max(0.5, min(2.0, kcal_target / base))
    out = []
    for f, g in items:
        grams = max(5, round(g * factor / 5) * 5)
        if nut.foods()[f]["category"] == "fat" and nut.foods()[f]["portion_g"] <= 16:
            grams = max(5, round(g * min(factor, 1.3)))  # oils/spreads stay small
        out.append(nut.item_for(f, grams))
    return out


def build_diet(p: Profile, t: Targets, week_index: int, settings: dict) -> list[DietDay]:
    blocked = blocked_foods(p, settings)
    protein_focus = p.goal in ("lose_fat", "build_muscle") or p.diet_style == "high_protein"
    days: list[DietDay] = []
    for d in range(7):
        meals: list[DietMeal] = []
        for si, slot in enumerate(("breakfast", "lunch", "snack", "dinner")):
            pool = []
            for tid, tags, items in T[slot]:
                if any(f in blocked for f, _ in items):
                    continue
                if p.diet_style == "vegetarian" and "veg" not in tags:
                    continue
                if p.diet_style == "low_carb" and "lc" not in tags:
                    continue
                pool.append((tid, tags, items))
            if not pool and p.diet_style == "low_carb":  # relax: keep style soft if the pool is empty
                pool = [x for x in T[slot] if not any(f in blocked for f, _ in x[2])]
            if not pool:
                pool = [x for x in T[slot]]
            if protein_focus:
                hp = [x for x in pool if "hp" in x[1]]
                pool = hp or pool
            tid, tags, items = pool[(d + week_index + si * 2) % len(pool)]
            scaled = _scaled(items, t.calories * SLOT_SHARE[slot])
            meals.append(DietMeal(slot=slot, items=scaled, kcal=sum(i.kcal for i in scaled)))
        short = t.calories - sum(m.kcal for m in meals)
        if short > 0.06 * t.calories:  # big targets: add one extra snack instead of making meals huge
            ok = [x for x in T["snack"] if not any(f in blocked for f, _ in x[2])]
            pool = [x for x in ok if not (p.diet_style == "low_carb" and "lc" not in x[1])] or ok or T["snack"]
            tid, tags, items = pool[(d + week_index + 5) % len(pool)]
            scaled = _scaled(items, short)
            meals.append(DietMeal(slot="extra", items=scaled, kcal=sum(i.kcal for i in scaled)))
        all_items = [i for m in meals for i in m.items]
        tot = nut.totals(all_items)
        days.append(DietDay(day=d, meals=meals, kcal=tot["kcal"], protein=int(round(tot["protein"])), carbs=int(round(tot["carbs"])), fat=int(round(tot["fat"]))))
    return days
