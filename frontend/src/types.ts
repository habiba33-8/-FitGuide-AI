// These types mirror backend/fitguide/schemas.py. If you change one side, change the other.
export type Goal = "lose_fat" | "build_muscle" | "maintain" | "improve_fitness";
export type Level = "beginner" | "intermediate" | "advanced";
export type Equipment = "with_machine" | "without_machine" | "both";
export type DietStyle = "balanced" | "high_protein" | "low_carb" | "vegetarian";

export interface Profile {
  name: string; sex: "female" | "male"; age: number; height_cm: number; weight_kg: number;
  goal: Goal; activity: "sedentary" | "light" | "moderate" | "active"; level: Level; equipment: Equipment;
  days_per_week: number; diet_style: DietStyle; allergies: string[]; dislikes: string[]; conditions: string[]; injuries: string[];
}
export interface Targets {
  bmr: number; tdee: number; calories: number; protein_g: number; carbs_g: number; fat_g: number; water_ml: number;
  notes: string[]; safety_flags: string[];
}
export interface PlanExercise { exercise_id: string; name: string; sets: number; reps: string; rest_s: number; video?: string | null }
export interface WorkoutDay { day: number; title: string; focus: string[]; exercises: PlanExercise[]; rest: boolean }
export interface MealItem { food_id: string; name: string; grams: number; kcal: number; protein: number; carbs: number; fat: number }
export interface DietMeal { slot: string; items: MealItem[]; kcal: number }
export interface DietDay { day: number; meals: DietMeal[]; kcal: number; protein: number; carbs: number; fat: number }
export interface Plan {
  plan_id: string; week_index: number; status: "draft" | "approved"; approach: string; approach_name: string; summary: string;
  workouts: WorkoutDay[]; diet: DietDay[]; targets: Targets; rationale: string[]; changes: string[]; settings: Record<string, unknown>;
}
export interface DayProgress { day: number; workout_done: boolean; exercises_done: number; exercises_total: number; kcal?: number | null; water_ml?: number | null }
export interface WeekProgress { days: DayProgress[]; start_weight_kg?: number | null; end_weight_kg?: number | null; felt?: "too_easy" | "just_right" | "too_hard" | null }
export interface DayLog { meals: MealItem[]; water_ml: number; workout_done: boolean }
export interface ChatMessage { role: "user" | "assistant"; content: string }
export interface SessionState { profile: Profile | null; plan: Plan | null; today: DayLog; today_index: number }
export interface Action { type: "log_meal" | "log_water" | "plan_changed" | "refused_plan_change"; items: MealItem[]; water_ml: number; summary: string }
export interface SourceRef { id: string; title: string; snippet: string; score: number }
export interface ChatResponse { reply: string; sources: SourceRef[]; actions: Action[]; plan: Plan | null; degraded: boolean; trace: string[] }
export interface AnalyzedItem {
  name: string; matched: boolean; food_id: string | null; food_name: string | null; grams: number; grams_low: number; grams_high: number;
  kcal: number; kcal_low: number; kcal_high: number; protein: number; carbs: number; fat: number; confidence: number;
}
export interface VisionResult { is_food: boolean; items: AnalyzedItem[]; kcal: number; kcal_low: number; kcal_high: number; notes: string; disclaimer: string }
export interface Exercise {
  id: string; name: string; muscle: string; secondary: string[]; equipment: string; mode: "with_machine" | "without_machine"; level: Level;
  cues: string[]; common_mistake: string; video?: { url: string; title: string; channel: string; verified: boolean } | null;
}
export interface Approach { id: string; name: string; description: string }
