import asyncio
from evals import vision_eval as v


def test_score_math():
    r = v.score([{"true": 500, "kcal": 450, "low": 400, "high": 520}, {"true": 400, "kcal": 600, "low": 500, "high": 650}])
    assert r["mae_kcal"] == 125.0 and r["within_20pct"] == 0.5 and r["range_coverage"] == 0.5


def test_empty_is_honest():
    assert v.score([])["n"] == 0


def test_dry_run_with_manifest(tmp_path):
    (tmp_path / "manifest.csv").write_text("filename,true_kcal,description\na.jpg,260,rice\n")
    out = asyncio.run(v.run(dry=True, directory=tmp_path))
    assert out["n"] == 1 and out["dry_run"] is True
