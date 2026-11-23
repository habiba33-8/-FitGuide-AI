"""Pydantic models = the contract between frontend, API and the AI layer.
Everything that comes from the LLM is parsed through these, so a bad answer fails loudly instead of silently."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

Goal = Literal["lose_fat", "build_muscle", "maintain", "improve_fitness"]
Level = Literal["beginner", "intermediate", "advanced"]
Equipment = Literal["with_machine", "without_machine", "both"]
Lang = Literal["en", "ar"]


class Profile(BaseModel):
    name: str = Field(default="", max_length=40)
    sex: Literal["female", "male"] = "female"
    age: int = Field(ge=14, le=80)
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=30, le=250)
    goal: Goal = "maintain"
    activity: Literal["sedentary", "light", "moderate", "active"] = "light"
    level: Level = "beginner"
    equipment: Equipment = "both"
    days_per_week: int = Field(default=3, ge=2, le=6)
    diet_style: Literal["balanced", "high_protein", "low_carb", "vegetarian"] = "balanced"
    allergies: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)  # free text, used only for safety flags
    injuries: list[str] = Field(default_factory=list)


class Targets(BaseModel):
    bmr: int
    tdee: int
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    water_ml: int
    notes: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)


class PlanExercise(BaseModel):
    exercise_id: str
    name: str
    sets: int
    reps: str
    rest_s: int = 60
    video: Optional[str] = None


class WorkoutDay(BaseModel):
    day: int = Field(ge=0, le=6)  # 0 = Monday
    title: str
    focus: list[str] = Field(default_factory=list)
    exercises: list[PlanExercise] = Field(default_factory=list)
    rest: bool = False


class MealItem(BaseModel):
    food_id: str
    name: str
    grams: float
    kcal: int
    protein: float
    carbs: float
    fat: float


class DietMeal(BaseModel):
    slot: Literal["breakfast", "lunch", "snack", "dinner", "extra"]
    items: list[MealItem]
    kcal: int


class DietDay(BaseModel):
    day: int = Field(ge=0, le=6)
    meals: list[DietMeal]
    kcal: int
    protein: int
    carbs: int
    fat: int


class Plan(BaseModel):
    plan_id: str
    week_index: int = 1
    status: Literal["draft", "approved"] = "draft"
    approach: str
    approach_name: str
    summary: str
    workouts: list[WorkoutDay]
    diet: list[DietDay]
    targets: Targets
    rationale: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)  # overrides applied by chat: excluded exercises/foods, focus, etc.


class DayProgress(BaseModel):
    day: int
    workout_done: bool = False
    exercises_done: int = 0
    exercises_total: int = 0
    kcal: Optional[int] = None
    water_ml: Optional[int] = None


class WeekProgress(BaseModel):
    days: list[DayProgress] = Field(default_factory=list)
    start_weight_kg: Optional[float] = None
    end_weight_kg: Optional[float] = None
    felt: Optional[Literal["too_easy", "just_right", "too_hard"]] = None


class DayLog(BaseModel):
    meals: list[MealItem] = Field(default_factory=list)
    water_ml: int = 0
    workout_done: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class SessionState(BaseModel):
    profile: Optional[Profile] = None
    plan: Optional[Plan] = None
    today: DayLog = Field(default_factory=DayLog)
    today_index: int = 0


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)
    lang: Lang = "en"
    state: SessionState = Field(default_factory=SessionState)

    @field_validator("messages")
    @classmethod
    def last_is_user(cls, v):
        if v[-1].role != "user":
            raise ValueError("last message must be from the user")
        return v


class ProposedItem(BaseModel):
    food_id: str
    name: str
    grams: float


class Action(BaseModel):
    type: Literal["log_meal", "log_water", "plan_changed", "refused_plan_change"]
    items: list[MealItem] = Field(default_factory=list)
    water_ml: int = 0
    summary: str = ""


class SourceRef(BaseModel):
    id: str
    title: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    sources: list[SourceRef] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    plan: Optional[Plan] = None
    degraded: bool = False  # True when no LLM key / LLM failed and the answer came from retrieval only
    trace: list[str] = Field(default_factory=list)
