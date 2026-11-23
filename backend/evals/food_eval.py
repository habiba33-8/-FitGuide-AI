"""Food-name matching evaluation: does a typed or spoken food name map to the right row of the food table?"""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fitguide.calc.nutrition import find_food

DATA = pathlib.Path(__file__).parent / "data" / "food_queries.json"


def run() -> dict:
    pairs = json.loads(DATA.read_text(encoding="utf-8"))
    ok, wrong = 0, []
    for q, exp in pairs:
        f = find_food(q)
        if f and f["id"] == exp:
            ok += 1
        else:
            wrong.append({"query": q, "expected": exp, "got": f["id"] if f else None})
    return {"n": len(pairs), "accuracy": round(ok / len(pairs), 3), "wrong": wrong}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, ensure_ascii=False))
