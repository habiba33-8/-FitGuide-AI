"""Vercel entry point: Vercel looks for `app` in api/index.py."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from fitguide.main import app  # noqa: E402,F401
