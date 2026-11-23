"""Deterministic energy and macro maths. The LLM never does arithmetic: it calls these functions' results.

Formulas
- BMR: Mifflin-St Jeor  (10*kg + 6.25*cm - 5*age + 5 for men, -161 for women)
- TDEE: BMR x activity factor
- Calories: TDEE adjusted for the goal, never below a safe floor
"""
from __future__ import annotations
from ..schemas import Profile, Targets

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
FLOOR = {"female": 1200, "male": 1500}
RED_FLAG_WORDS = {
    "diabet": "Diabetes: food and exercise targets here are general. Talk to your doctor before changing your diet.",
    "pregnan": "Pregnancy: do not follow a calorie deficit. Ask your doctor for a plan.",
    "breastfeed": "Breastfeeding: avoid a calorie deficit without medical advice.",
    "heart": "Heart condition: get medical clearance before starting an exercise plan.",
    "kidney": "Kidney condition: high protein targets may not be safe. Ask your doctor.",
    "eating disorder": "Eating disorder history: calorie tracking can be harmful. Please speak to a professional.",
    "anorex": "Eating disorder history: calorie tracking can be harmful. Please speak to a professional.",
    "bulim": "Eating disorder history: calorie tracking can be harmful. Please speak to a professional.",
    "hypertens": "High blood pressure: get medical clearance before intense exercise.",
    "asthma": "Asthma: keep your inhaler nearby and keep intensity moderate at first.",
}


def bmr(p: Profile) -> float:
    base = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age
    return base + (5 if p.sex == "male" else -161)


def tdee(p: Profile) -> float:
    return bmr(p) * ACTIVITY[p.activity]


def safety_flags(p: Profile) -> list[str]:
    text = " ".join(p.conditions + p.injuries).lower()
    flags = [msg for key, msg in RED_FLAG_WORDS.items() if key in text]
    if p.age < 18:
        flags.append("Under 18: keep goals focused on health and skills, not weight loss. Talk to a doctor or coach.")
    return list(dict.fromkeys(flags))


def compute_targets(p: Profile, calorie_override: int | None = None) -> Targets:
    notes: list[str] = []
    b, t = bmr(p), tdee(p)
    kcal = t
    if p.goal == "lose_fat":
        kcal = t * 0.82  # about an 18% deficit: moderate and sustainable
        notes.append("Fat loss: about 18% below maintenance, which is a moderate deficit.")
    elif p.goal == "build_muscle":
        kcal = t * 1.08
        notes.append("Muscle gain: about 8% above maintenance to support growth without adding too much fat.")
    elif p.goal == "improve_fitness":
        notes.append("Fitness: eating at maintenance.")
    else:
        notes.append("Maintenance: eating at your estimated daily energy use.")
    floor = FLOOR[p.sex]
    if kcal < floor:
        kcal = floor
        notes.append(f"Raised to the safe minimum of {floor} kcal.")
    if calorie_override:
        kcal = max(floor, min(calorie_override, t * 1.35))
        notes.append("Calories adjusted by a request or by last week's progress.")
    kcal = int(round(kcal / 10.0) * 10)

    protein_per_kg = {"lose_fat": 2.0, "build_muscle": 1.9, "maintain": 1.6, "improve_fitness": 1.6}[p.goal]
    if p.diet_style == "high_protein":
        protein_per_kg += 0.2
    protein = int(round(p.weight_kg * protein_per_kg))
    if protein * 4 > 0.33 * kcal:
        protein = int(0.33 * kcal / 4)  # keep protein to a practical share of calories (about 33% at most)
        notes.append("Protein is capped at about a third of your calories so the plan stays realistic.")
    fat_share = 0.25 if p.diet_style != "low_carb" else 0.40
    fat = int(round(kcal * fat_share / 9))
    carbs = max(0, int(round((kcal - protein * 4 - fat * 9) / 4)))
    if p.diet_style == "low_carb":
        notes.append("Low carb style: more fat, fewer carbs, same protein.")
    water = int(round((p.weight_kg * 33 + (400 if p.activity in ("moderate", "active") else 0)) / 50.0) * 50)
    return Targets(bmr=int(round(b)), tdee=int(round(t)), calories=kcal, protein_g=protein, carbs_g=carbs,
                   fat_g=fat, water_ml=water, notes=notes, safety_flags=safety_flags(p))


def weekly_weight_change_bound(p: Profile) -> float:
    """Conservative healthy bound in kg/week (about 0.5 to 1% of body weight)."""
    return round(p.weight_kg * 0.01, 2)
