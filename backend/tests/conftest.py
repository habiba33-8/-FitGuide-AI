import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from fitguide.schemas import Profile


@pytest.fixture
def profile():
    return Profile(name="Test", sex="female", age=22, height_cm=165, weight_kg=62, goal="lose_fat", activity="light",
                   level="beginner", equipment="both", days_per_week=3)
