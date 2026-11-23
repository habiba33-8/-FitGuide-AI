"""Photo-calorie accuracy check. YOU provide the photos and the true calories (a weighed meal), the script measures the error.

Setup:
  1. Put meal photos in evals/vision_samples/ (jpg/png/webp).
  2. List them in evals/vision_samples/manifest.csv with columns: filename,true_kcal,description
     (true_kcal = what you get when you weigh every item and use the food table or a food label).
  3. Put LLM_API_KEY in backend/.env, then:  python -m evals.vision_eval
  --dry-run  uses a fake model so you can test the script without a key. Its numbers mean NOTHING about accuracy.
"""
from __future__ import annotations
import asyncio, base64, csv, json, mimetypes, pathlib, statistics, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fitguide.llm.client import OpenAICompatLLM
from fitguide.llm.mock import MockLLM
from fitguide.vision.analyzer import analyze_image

DIR = pathlib.Path(__file__).parent / "vision_samples"


def score(rows: list[dict]) -> dict:
    """rows: dicts with true, kcal, low, high. Returns the headline numbers."""
    if not rows:
        return {"n": 0, "note": "No samples. Add photos and manifest.csv (see the top of this file)."}
    errs = [abs(r["kcal"] - r["true"]) for r in rows]
    rel = [e / r["true"] for e, r in zip(errs, rows)]
    return {
        "n": len(rows),
        "mae_kcal": round(statistics.mean(errs), 1),
        "mean_abs_pct_error": round(100 * statistics.mean(rel), 1),
        "within_20pct": round(sum(x <= 0.20 for x in rel) / len(rows), 3),
        "range_coverage": round(sum(r["low"] <= r["true"] <= r["high"] for r in rows) / len(rows), 3),
    }


def load_manifest(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("filename") and r.get("true_kcal")]


async def run(dry: bool = False, directory: pathlib.Path = DIR) -> dict:
    manifest = load_manifest(directory / "manifest.csv")
    llm = MockLLM({"is_food": True, "items": [{"name": "rice", "grams": 200}], "notes": "dry run"}) if dry else OpenAICompatLLM()
    rows, failed = [], []
    for m in manifest:
        p = directory / m["filename"]
        if not p.exists() and not dry:
            failed.append(m["filename"]); continue
        data = p.read_bytes() if p.exists() else b"x"
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        try:
            res = await analyze_image(llm, base64.b64encode(data).decode(), mime)
        except Exception as e:  # keep going, report at the end
            failed.append(f"{m['filename']}: {str(e)[:80]}"); continue
        rows.append({"true": float(m["true_kcal"]), "kcal": res.kcal, "low": res.kcal_low, "high": res.kcal_high})
        if dry:
            llm = MockLLM({"is_food": True, "items": [{"name": "rice", "grams": 200}], "notes": "dry run"})
    out = score(rows)
    out["failed"] = failed
    out["dry_run"] = dry
    return out


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run("--dry-run" in sys.argv)), indent=1))
