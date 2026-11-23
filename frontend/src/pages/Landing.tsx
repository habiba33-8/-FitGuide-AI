import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Profile, Targets } from "../types";
import { Bar } from "../components";

const base: Profile = { name: "", sex: "female", age: 22, height_cm: 165, weight_kg: 65, goal: "maintain", activity: "light", level: "beginner",
  equipment: "both", days_per_week: 3, diet_style: "balanced", allergies: [], dislikes: [], conditions: [], injuries: [] };

const GOALS: [Profile["goal"], string][] = [["lose_fat", "Lose fat"], ["build_muscle", "Build muscle"], ["maintain", "Maintain"]];

function Try() {
  const [p, setP] = useState<Profile>(base);
  const [t, setT] = useState<Targets | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => { api.targets(p).then((x) => { setT(x); setErr(false); }).catch(() => setErr(true)); }, 250);
    return () => clearTimeout(id);
  }, [p]);
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP((o) => ({ ...o, [k]: v }));
  return (
    <div className="grid g2">
      <div className="card">
        <h3>Your numbers</h3>
        <div className="field"><span>Weight: {p.weight_kg} kg</span><input aria-label="Weight" type="range" min={40} max={130} value={p.weight_kg} onChange={(e) => set("weight_kg", +e.target.value)} /></div>
        <div className="field"><span>Height: {p.height_cm} cm</span><input aria-label="Height" type="range" min={140} max={205} value={p.height_cm} onChange={(e) => set("height_cm", +e.target.value)} /></div>
        <div className="field"><span>Age: {p.age}</span><input aria-label="Age" type="range" min={16} max={65} value={p.age} onChange={(e) => set("age", +e.target.value)} /></div>
        <div className="chips" role="group" aria-label="Goal">
          {GOALS.map(([g, l]) => <button key={g} className="chip" aria-pressed={p.goal === g} onClick={() => set("goal", g)}>{l}</button>)}
        </div>
      </div>
      <div className="card">
        <h3>Your daily targets</h3>
        {err && <div className="notice warn">Start the backend to see live numbers (see the README).</div>}
        {t && !err && (
          <>
            <div className="row between"><div><div className="stat">{t.calories}</div><div className="muted small">kcal per day</div></div>
              <div><div className="stat">{t.protein_g}g</div><div className="muted small">protein</div></div>
              <div><div className="stat">{(t.water_ml / 1000).toFixed(1)}L</div><div className="muted small">water</div></div></div>
            <p className="small muted" style={{ marginTop: 16 }}>Your body burns about {t.tdee} kcal a day. The target is set from that, using the Mifflin-St Jeor equation. Plain maths in code, not a guess from a chatbot.</p>
            <Bar value={t.calories} total={t.tdee * 1.2} />
          </>
        )}
      </div>
    </div>
  );
}

const TABS = ["The problem", "The solution", "How it works"] as const;

export default function Landing() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("The problem");
  return (
    <>
      <div className="container hero">
        <div>
          <div className="eyebrow">AI fitness and nutrition coach</div>
          <h1>A plan that fits your body, <em>and keeps fitting it.</em></h1>
          <p className="hero-lead">Most plans are copied from the internet and never change. FitGuide builds a weekly workout and meal plan from your numbers, checks the maths in code, and adjusts each week from what you really did.</p>
          <div className="row"><Link to="/start" className="btn btn-primary">Build my plan</Link><Link to="/chat" className="btn btn-ghost">Try the coach chat</Link></div>
        </div>
        <div className="hero-panel" aria-hidden>
          <div className="small" style={{ color: "#cbb9ff" }}>Today</div>
          <div className="stat" style={{ margin: "6px 0 14px" }}>1,420 <span className="small" style={{ fontWeight: 500 }}>/ 1,900 kcal</span></div>
          <Bar value={1420} total={1900} />
          <div className="row between small" style={{ margin: "14px 0 6px" }}><span>Protein</span><span>88 / 120 g</span></div>
          <Bar value={88} total={120} />
          <div className="row between small" style={{ margin: "14px 0 6px" }}><span>Water</span><span>1.5 / 2.4 L</span></div>
          <Bar value={1500} total={2400} water />
        </div>
      </div>

      <section className="section container">
        <div className="seg" role="tablist" aria-label="Explainer">
          {TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>{t}</button>)}
        </div>
        <div style={{ marginTop: 24 }}>
          {tab === "The problem" && (
            <div className="compare">
              <div className="card bad"><h3>A generic plan</h3><ul className="muted"><li>Same calories for everyone</li><li>Never changes after week one</li><li>Calorie counts guessed from a photo with no way to check</li><li>You stop following it and nobody notices</li></ul></div>
              <div className="card good"><h3>What people actually need</h3><ul className="muted"><li>Targets from their own body and goal</li><li>A plan that adapts to real progress</li><li>Numbers they can verify</li><li>A coach to ask when life changes</li></ul></div>
            </div>
          )}
          {tab === "The solution" && (
            <div className="grid g3">
              <div className="card"><div className="eyebrow">Personal</div><h3>Targets from your body</h3><p className="muted">Calories, protein and water are calculated in code from your age, size, goal and activity.</p></div>
              <div className="card"><div className="eyebrow">Adaptive</div><h3>Weekly renewal</h3><p className="muted">Every week you log how it went. The next plan gets harder, easier or a deload, by clear rules.</p></div>
              <div className="card"><div className="eyebrow">Checkable</div><h3>Calories you can verify</h3><p className="muted">The AI finds the foods and amounts. The calories come from a food table, with a range and your confirmation.</p></div>
            </div>
          )}
          {tab === "How it works" && (
            <div className="grid g2">
              <div className="steps">
                <div className="step"><div><b>Tell us about you.</b><div className="muted">One minute. No account, nothing saved on a server.</div></div></div>
                <div className="step"><div><b>Review a draft plan.</b><div className="muted">Workout and meals for the week. You approve it.</div></div></div>
                <div className="step"><div><b>Follow it and talk to the coach.</b><div className="muted">Log meals by text or photo. Ask for changes in chat.</div></div></div>
                <div className="step"><div><b>Renew every week.</b><div className="muted">Progress in, a new draft out.</div></div></div>
              </div>
              <div className="card"><h3>Where the AI is</h3><p className="muted">A language model reads your messages and photos. A search over a small knowledge base (RAG) gives it trusted facts. Code validates everything it says before the plan or your log changes.</p><Link to="/chat">Open the coach chat</Link></div>
            </div>
          )}
        </div>
      </section>

      <section className="section container">
        <div className="eyebrow">Try it</div>
        <h2>See your targets in seconds</h2>
        <Try />
      </section>

      <footer className="footer"><div className="container">FitGuide AI is a portfolio demo. It gives general guidance and is not medical advice. Nothing is stored after you close the tab.</div></footer>
    </>
  );
}
