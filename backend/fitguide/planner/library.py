"""Exercise library access + filters."""
from __future__ import annotations
import json, re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
LEVELS = {"beginner": 0, "intermediate": 1, "advanced": 2}


@lru_cache(maxsize=1)
def exercises() -> list[dict]:
    return json.loads((DATA / "exercises.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def by_id() -> dict[str, dict]:
    return {e["id"]: e for e in exercises()}


def find_exercise(text: str) -> dict | None:
    t = re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()
    if not t:
        return None
    t_id = t.replace(" ", "_")
    if t_id in by_id():
        return by_id()[t_id]
    best, score = None, 0
    tw = set(t.split())
    for e in exercises():
        nw = set(re.sub(r"[^a-z0-9 ]", " ", e["name"].lower()).split())
        s = len(tw & nw) / max(1, len(tw | nw))
        if t in e["name"].lower():
            s += 1
        if s > score:
            best, score = e, s
    return best if score >= 0.4 else None


# Injury keyword -> exercise ids to avoid, with a safer swap implied by each exercise's `alternative`
INJURY_AVOID = {
    "knee": {"walking_lunge", "reverse_lunge", "bulgarian_split_squat", "burpee", "jumping_jack", "barbell_back_squat", "step_up", "nordic_curl"},
    "back": {"deadlift", "barbell_row", "romanian_deadlift", "dumbbell_rdl", "back_extension", "kettlebell_swing", "barbell_back_squat", "russian_twist"},
    "shoulder": {"overhead_press", "dumbbell_shoulder_press", "pike_push_up", "chest_dip", "bench_dip", "machine_shoulder_press", "pull_up", "skull_crusher"},
    "wrist": {"push_up", "close_grip_push_up", "pike_push_up", "plank", "side_plank", "mountain_climber", "burpee"},
    "elbow": {"skull_crusher", "chest_dip", "bench_dip", "close_grip_push_up", "barbell_curl"},
    "hip": {"bulgarian_split_squat", "walking_lunge", "barbell_back_squat", "hip_thrust"},
    "ankle": {"burpee", "jumping_jack", "walking_lunge", "mountain_climber", "bodyweight_calf_raise", "standing_calf_raise"},
}


def injury_excludes(injuries: list[str]) -> set[str]:
    text = " ".join(injuries).lower()
    out: set[str] = set()
    for key, ids in INJURY_AVOID.items():
        if key in text or (key == "back" and "spine" in text):
            out |= ids
    return out


def candidates(*, muscles: list[str] | None = None, patterns: list[str] | None = None, level: str = "beginner",
               equipment: str = "both", exclude: set[str] | None = None) -> list[dict]:
    exclude = exclude or set()
    maxlvl = LEVELS[level]
    out = []
    for e in exercises():
        if e["id"] in exclude:
            continue
        if muscles and e["muscle"] not in muscles:
            continue
        if patterns and e["pattern"] not in patterns:
            continue
        if LEVELS[e["level"]] > maxlvl:
            continue
        if equipment == "with_machine" and e["mode"] != "with_machine" and e["equipment"] != "dumbbell":
            continue
        if equipment == "without_machine" and e["mode"] != "without_machine":
            continue
        out.append(e)
    # prefer exercises at the user's own level, then library order (stable, so plans are reproducible)
    out.sort(key=lambda e: (-(LEVELS[e["level"]] == maxlvl), 0))
    return out
