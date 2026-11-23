import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useStore } from "../store";
import type { Profile } from "../types";

const GOALS: [Profile["goal"], string, string][] = [
  ["lose_fat", "Lose fat", "A moderate calorie deficit with enough protein."],
  ["build_muscle", "Build muscle", "A small surplus and progressive training."],
  ["maintain", "Maintain", "Keep your weight and stay active."],
  ["improve_fitness", "Improve fitness", "Eat at maintenance, train for stamina and strength."],
];
const ACTIVITY: [Profile["activity"], string][] = [["sedentary", "Mostly sitting"], ["light", "Light activity"], ["moderate", "Moderately active"], ["active", "Very active"]];
const ALLERGIES = ["dairy", "nuts", "egg", "gluten", "fish", "shellfish", "soy", "sesame"];
const INJURIES = ["knee", "back", "shoulder", "wrist", "elbow", "hip", "ankle"];
const CONDITIONS = ["diabetes", "pregnancy", "heart condition", "kidney condition"];

const blank: Profile = { name: "", sex: "female", age: 22, height_cm: 165, weight_kg: 65, goal: "maintain", activity: "light", level: "beginner",
  equipment: "both", days_per_week: 3, diet_style: "balanced", allergies: [], dislikes: [], conditions: [], injuries: [] };

function Toggle({ list, value, onChange }: { list: string[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="chips">
      {list.map((x) => (
        <button type="button" key={x} className="chip" aria-pressed={value.includes(x)}
          onClick={() => onChange(value.includes(x) ? value.filter((v) => v !== x) : [...value, x])}>{x}</button>
      ))}
    </div>
  );
}

export default function Onboarding() {
  const { state, dispatch } = useStore();
  const nav = useNavigate();
  const [p, setP] = useState<Profile>(state.profile ?? blank);
  const [dislikes, setDislikes] = useState((state.profile?.dislikes ?? []).join(", "));
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP((o) => ({ ...o, [k]: v }));
  const num = (k: "age" | "height_cm" | "weight_kg") => (e: React.ChangeEvent<HTMLInputElement>) => set(k, Number(e.target.value));

  const valid = p.age >= 14 && p.age <= 80 && p.height_cm >= 120 && p.height_cm <= 230 && p.weight_kg >= 30 && p.weight_kg <= 250;

  async function finish() {
    setBusy(true); setErr("");
    const profile = { ...p, name: p.name.trim(), dislikes: dislikes.split(",").map((s) => s.trim()).filter(Boolean) };
    try {
      const plan = await api.generate(profile);
      dispatch({ t: "setProfile", profile });
      dispatch({ t: "newWeek", plan });
      dispatch({ t: "messages", messages: [] });
      if (!state.visited) { api.visit(profile.name).catch(() => undefined); dispatch({ t: "visited" }); }
      nav("/plan");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong.");
    } finally { setBusy(false); }
  }

  return (
    <div className="container page">
      <div className="wizard">
        <div className="eyebrow">Step {step + 1} of 3</div>
        <div className="progress-dots" aria-hidden>{[0, 1, 2].map((i) => <i key={i} className={i <= step ? "on" : ""} />)}</div>
        <div className="card">
          {step === 0 && (
            <>
              <h2>About you</h2>
              <div className="field"><label htmlFor="name">First name (optional)</label><input id="name" maxLength={40} value={p.name} onChange={(e) => set("name", e.target.value)} /></div>
              <div className="field"><span>Sex (used by the calorie equation)</span>
                <div className="chips">{(["female", "male"] as const).map((s) => <button type="button" key={s} className="chip" aria-pressed={p.sex === s} onClick={() => set("sex", s)}>{s}</button>)}</div></div>
              <div className="two">
                <div className="field"><label htmlFor="age">Age</label><input id="age" type="number" value={p.age} onChange={num("age")} /></div>
                <div className="field"><label htmlFor="h">Height (cm)</label><input id="h" type="number" value={p.height_cm} onChange={num("height_cm")} /></div>
              </div>
              <div className="field"><label htmlFor="w">Weight (kg)</label><input id="w" type="number" value={p.weight_kg} onChange={num("weight_kg")} /></div>
              {!valid && <div className="notice warn">Check the numbers: age 14 to 80, height 120 to 230 cm, weight 30 to 250 kg.</div>}
              <div className="notice" style={{ marginTop: 14 }}>Privacy: your answers stay in this browser tab and are sent to the AI only to build your plan. No account, no database. The demo owner may see your first name and the time you started, nothing else.</div>
            </>
          )}
          {step === 1 && (
            <>
              <h2>Goal and training</h2>
              {GOALS.map(([g, t, d]) => <button type="button" key={g} className="opt" aria-pressed={p.goal === g} onClick={() => set("goal", g)}><b>{t}</b><span className="muted small">{d}</span></button>)}
              <div className="field"><span>Daily activity</span><div className="chips">{ACTIVITY.map(([a, l]) => <button type="button" key={a} className="chip" aria-pressed={p.activity === a} onClick={() => set("activity", a)}>{l}</button>)}</div></div>
              <div className="field"><span>Training level</span><div className="chips">{(["beginner", "intermediate", "advanced"] as const).map((l) => <button type="button" key={l} className="chip" aria-pressed={p.level === l} onClick={() => set("level", l)}>{l}</button>)}</div></div>
              <div className="field"><span>Where do you train?</span><div className="chips">
                {([["without_machine", "At home, no machines"], ["with_machine", "Gym with machines"], ["both", "Either"]] as const).map(([v, l]) => <button type="button" key={v} className="chip" aria-pressed={p.equipment === v} onClick={() => set("equipment", v)}>{l}</button>)}</div></div>
              <div className="field"><span>Training days per week: {p.days_per_week}</span><input aria-label="Training days" type="range" min={2} max={6} value={p.days_per_week} onChange={(e) => set("days_per_week", Number(e.target.value))} /></div>
            </>
          )}
          {step === 2 && (
            <>
              <h2>Food and safety</h2>
              <div className="field"><span>Eating style</span><div className="chips">
                {(["balanced", "high_protein", "low_carb", "vegetarian"] as const).map((d) => <button type="button" key={d} className="chip" aria-pressed={p.diet_style === d} onClick={() => set("diet_style", d)}>{d.replace("_", " ")}</button>)}</div></div>
              <div className="field"><span>Allergies or intolerances</span><Toggle list={ALLERGIES} value={p.allergies} onChange={(v) => set("allergies", v)} /></div>
              <div className="field"><label htmlFor="dl">Foods you dislike (comma separated)</label><input id="dl" value={dislikes} onChange={(e) => setDislikes(e.target.value)} placeholder="liver, tuna" /></div>
              <div className="field"><span>Injuries or sore areas</span><Toggle list={INJURIES} value={p.injuries} onChange={(v) => set("injuries", v)} /></div>
              <div className="field"><span>Health conditions (we only use this to show safety notes)</span><Toggle list={CONDITIONS} value={p.conditions} onChange={(v) => set("conditions", v)} /></div>
              {err && <div className="notice danger">{err}</div>}
            </>
          )}
          <div className="row between" style={{ marginTop: 20 }}>
            <button className="btn btn-ghost" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>Back</button>
            {step < 2
              ? <button className="btn btn-primary" disabled={!valid} onClick={() => setStep(step + 1)}>Next</button>
              : <button className="btn btn-primary" disabled={busy || !valid} onClick={finish}>{busy ? "Building your plan..." : "Build my plan"}</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
