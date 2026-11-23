import { createContext, useContext, useEffect, useMemo, useReducer, type ReactNode } from "react";
import type { ChatMessage, DayLog, DayProgress, MealItem, Plan, Profile, SessionState, WeekProgress } from "./types";
import { todayIndex } from "./util";

/** Everything lives in the browser tab (sessionStorage). Close the tab and it is gone: no login, no database. */
export interface AppState {
  profile: Profile | null;
  plan: Plan | null;
  logs: Record<number, DayLog>; // per weekday index
  checks: Record<string, boolean>; // "day:exerciseIndex" -> done
  messages: ChatMessage[];
  chatLang: "en" | "ar";
  startWeight: number | null;
  endWeight: number | null;
  felt: WeekProgress["felt"];
  visited: boolean;
}

const EMPTY_LOG: DayLog = { meals: [], water_ml: 0, workout_done: false };
const initial: AppState = { profile: null, plan: null, logs: {}, checks: {}, messages: [], chatLang: "en", startWeight: null, endWeight: null, felt: null, visited: false };
const KEY = "fitguide-session-v1";

type Act =
  | { t: "setProfile"; profile: Profile }
  | { t: "setPlan"; plan: Plan }
  | { t: "approve" }
  | { t: "newWeek"; plan: Plan }
  | { t: "addMeal"; items: MealItem[] }
  | { t: "addWater"; ml: number }
  | { t: "toggleCheck"; key: string }
  | { t: "setWorkoutDone"; day: number; done: boolean }
  | { t: "messages"; messages: ChatMessage[] }
  | { t: "lang"; lang: "en" | "ar" }
  | { t: "weights"; start?: number | null; end?: number | null }
  | { t: "felt"; felt: WeekProgress["felt"] }
  | { t: "visited" }
  | { t: "reset" };

function reducer(s: AppState, a: Act): AppState {
  switch (a.t) {
    case "setProfile": return { ...s, profile: a.profile, startWeight: s.startWeight ?? a.profile.weight_kg };
    case "setPlan": return { ...s, plan: a.plan };
    case "approve": return s.plan ? { ...s, plan: { ...s.plan, status: "approved" } } : s;
    case "newWeek": return { ...s, plan: a.plan, logs: {}, checks: {}, felt: null, startWeight: s.endWeight ?? s.startWeight, endWeight: null };
    case "addMeal": { const d = todayIndex(); const l = s.logs[d] ?? EMPTY_LOG; return { ...s, logs: { ...s.logs, [d]: { ...l, meals: [...l.meals, ...a.items] } } }; }
    case "addWater": { const d = todayIndex(); const l = s.logs[d] ?? EMPTY_LOG; return { ...s, logs: { ...s.logs, [d]: { ...l, water_ml: l.water_ml + a.ml } } }; }
    case "toggleCheck": return { ...s, checks: { ...s.checks, [a.key]: !s.checks[a.key] } };
    case "setWorkoutDone": { const l = s.logs[a.day] ?? EMPTY_LOG; return { ...s, logs: { ...s.logs, [a.day]: { ...l, workout_done: a.done } } }; }
    case "messages": return { ...s, messages: a.messages };
    case "lang": return { ...s, chatLang: a.lang };
    case "weights": return { ...s, startWeight: a.start === undefined ? s.startWeight : a.start, endWeight: a.end === undefined ? s.endWeight : a.end };
    case "felt": return { ...s, felt: a.felt };
    case "visited": return { ...s, visited: true };
    case "reset": return { ...initial };
  }
}

function load(): AppState {
  try { const raw = sessionStorage.getItem(KEY); if (raw) return { ...initial, ...JSON.parse(raw) }; } catch { /* ignore */ }
  return initial;
}

const Ctx = createContext<{ state: AppState; dispatch: (a: Act) => void } | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, load);
  useEffect(() => { try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch { /* quota */ } }, [state]);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const c = useContext(Ctx);
  if (!c) throw new Error("StoreProvider missing");
  return c;
}

export const dayLog = (s: AppState, d: number): DayLog => s.logs[d] ?? EMPTY_LOG;

export function sessionForApi(s: AppState): SessionState {
  const d = todayIndex();
  return { profile: s.profile, plan: s.plan, today: dayLog(s, d), today_index: d };
}

/** Weekly progress sent to the backend when the user renews the plan. */
export function buildProgress(s: AppState): WeekProgress {
  const days: DayProgress[] = (s.plan?.workouts ?? []).map((w) => {
    const done = w.exercises.filter((_, i) => s.checks[`${w.day}:${i}`]).length;
    const log = dayLog(s, w.day);
    return { day: w.day, workout_done: w.rest ? false : log.workout_done || (w.exercises.length > 0 && done === w.exercises.length),
      exercises_done: done, exercises_total: w.exercises.length,
      kcal: log.meals.length ? Math.round(log.meals.reduce((a, m) => a + m.kcal, 0)) : null, water_ml: log.water_ml || null };
  });
  return { days, start_weight_kg: s.startWeight, end_weight_kg: s.endWeight, felt: s.felt };
}
