import type { Approach, ChatMessage, ChatResponse, Exercise, MealItem, Plan, Profile, SessionState, Targets, VisionResult, WeekProgress } from "./types";

async function call<T>(path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new Error("Cannot reach the backend. Is it running on port 8000?");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const j = await res.json(); if (typeof j.detail === "string") detail = j.detail; else if (j.detail) detail = "Some of the details look invalid. Please check the form."; } catch { /* keep default */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => call<{ ok: boolean; llm_configured: boolean; models: string[]; kb_chunks: number; foods: number; exercises: number }>("/api/health"),
  targets: (profile: Profile) => call<Targets>("/api/targets", { profile }),
  approaches: () => call<Approach[]>("/api/plan/approaches"),
  generate: (profile: Profile, approach?: string) => call<Plan>("/api/plan/generate", { profile, approach }),
  renew: (profile: Profile, plan: Plan, progress: WeekProgress) => call<Plan>("/api/plan/renew", { profile, plan, progress }),
  chat: (messages: ChatMessage[], lang: "en" | "ar", state: SessionState) => call<ChatResponse>("/api/chat", { messages, lang, state }),
  vision: (image_base64: string, mime: string, lang: "en" | "ar") => call<VisionResult>("/api/vision/analyze", { image_base64, mime, lang }),
  compute: (items: { food_id: string; grams: number }[]) => call<{ items: MealItem[]; totals: { kcal: number; protein: number; carbs: number; fat: number } }>("/api/meal/compute", { items }),
  exercises: () => call<Exercise[]>("/api/exercises"),
  visit: (name: string) => call<{ logged: boolean }>("/api/visit", { name }),
};
