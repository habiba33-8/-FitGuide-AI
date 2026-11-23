export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const DAYS_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** 0 = Monday, matching the backend. */
export const todayIndex = (d = new Date()) => (d.getDay() + 6) % 7;

export function weekDates(base = new Date()): Date[] {
  const monday = new Date(base);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - todayIndex(base));
  return Array.from({ length: 7 }, (_, i) => { const d = new Date(monday); d.setDate(monday.getDate() + i); return d; });
}

export const pct = (v: number, total: number) => (total > 0 ? Math.max(0, Math.min(100, Math.round((v / total) * 100))) : 0);

export const GOAL_LABEL: Record<string, string> = { lose_fat: "Lose fat", build_muscle: "Build muscle", maintain: "Maintain", improve_fitness: "Improve fitness" };
export const label = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
