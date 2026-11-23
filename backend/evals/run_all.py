"""Run every offline evaluation and print one summary. (Photo accuracy needs your own photos: see vision_eval.py.)"""
import asyncio, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from evals import food_eval, plan_eval, retrieval_eval, vision_eval

if __name__ == "__main__":
    out = {"retrieval": retrieval_eval.run(), "food_matching": food_eval.run(), "plan_constraints": plan_eval.run()}
    for k, v in out.items():
        v.pop("wrong", None); v.pop("misses", None); v.pop("failures", None)
    out["vision"] = asyncio.run(vision_eval.run())
    print(json.dumps(out, indent=1, ensure_ascii=False))
