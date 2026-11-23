import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Bar, NeedProfile } from "../components";
import { buildProgress, dayLog, useStore } from "../store";
import type { Approach } from "../types";
import { DAYS, DAYS_LONG, label, todayIndex } from "../util";

export default function PlanPage() {
  const { state, dispatch } = useStore();
  const { plan, profile } = state;
  const [day, setDay] = useState(todayIndex());
  const [approaches, setApproaches] = useState<Approach[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { api.approaches().then(setApproaches).catch(() => undefined); }, []);

  if (!profile || !plan) return <NeedProfile what="Your weekly plan" />;
  const approved = plan.status === "approved";
  const w = plan.workouts.find((x) => x.day === day);
  const d = plan.diet.find((x) => x.day === day);
  const totalEx = plan.workouts.reduce((a, x) => a + x.exercises.length, 0);
  const doneEx = plan.workouts.reduce((a, x) => a + x.exercises.filter((_, i) => state.checks[`${x.day}:${i}`]).length, 0);
  const workoutDays = plan.workouts.filter((x) => !x.rest);

  async function regenerate(approach: string) {
    setBusy(true); setErr("");
    try { dispatch({ t: "setPlan", plan: await api.generate(profile!, approach) }); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }
  async function renew() {
    setBusy(true); setErr("");
    try { dispatch({ t: "newWeek", plan: await api.renew(profile!, plan!, buildProgress(state)) }); setDay(todayIndex()); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }

  return (
    <div className="container page">
      <div className="row between" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="eyebrow">Week {plan.week_index} {approved ? "" : "· draft"}</div>
          <h1 style={{ fontSize: "2.4rem" }}>{plan.approach_name}</h1>
          <p className="muted" style={{ maxWidth: 640 }}>{plan.summary}</p>
        </div>
        <span className={`tag ${approved ? "ok" : "warn"}`}>{approved ? "Approved" : "Waiting for your approval"}</span>
      </div>

      {plan.targets.safety_flags.map((f) => <div key={f} className="notice danger" style={{ marginBottom: 12 }}>{f}</div>)}
      {err && <div className="notice danger" style={{ marginBottom: 12 }}>{err}</div>}

      {!approved && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3>Review your draft</h3>
          <p className="muted">Nothing is active until you approve it. Want a different style of week? Pick one and the plan is rebuilt.</p>
          <div className="chips" style={{ marginBottom: 16 }}>
            {approaches.map((a) => <button key={a.id} className="chip" title={a.description} aria-pressed={plan.approach === a.id} disabled={busy} onClick={() => regenerate(a.id)}>{a.name}</button>)}
          </div>
          {plan.rationale.length > 0 && <ul className="muted small">{plan.rationale.map((r) => <li key={r}>{r}</li>)}</ul>}
          <button className="btn btn-primary" disabled={busy} onClick={() => dispatch({ t: "approve" })}>Approve this plan</button>
        </div>
      )}

      {approved && (
        <div className="notice locked" style={{ marginBottom: 24 }}>
          This plan is locked. To change anything, ask the <Link to="/chat">coach chat</Link> (for example, "swap squats, my knee hurts"). It checks the request and updates the plan for you.
          {plan.changes.length > 0 && <div className="small" style={{ marginTop: 6 }}>Changes so far: {plan.changes.join(" · ")}</div>}
        </div>
      )}

      <div className="daytabs" role="tablist" style={{ marginBottom: 20 }}>
        {DAYS.map((n, i) => {
          const wd = plan.workouts.find((x) => x.day === i);
          return <button key={n} role="tab" aria-selected={day === i} className="daytab" onClick={() => setDay(i)}>{n}<small>{wd?.rest ? "Rest" : "Train"}</small></button>;
        })}
      </div>

      <div className="grid g2">
        <div className="card">
          <div className="row between"><h3>{DAYS_LONG[day]} workout</h3>{w && !w.rest && <span className="tag">{w.focus.map(label).join(" + ")}</span>}</div>
          {!w || w.rest ? <p className="muted">Rest day. Walk, stretch, drink water. Recovery is part of the plan.</p> : (
            <>
              <p className="muted small">{w.title}</p>
              {w.exercises.map((e, i) => {
                const k = `${day}:${i}`;
                return (
                  <div key={k} className={`ex${state.checks[k] ? " done" : ""}`}>
                    <input type="checkbox" aria-label={`Done: ${e.name}`} checked={!!state.checks[k]} disabled={!approved} onChange={() => dispatch({ t: "toggleCheck", key: k })} />
                    <div><div className="ex-name"><b>{e.name}</b></div><div className="muted small">{e.sets} sets × {e.reps} · rest {e.rest_s}s</div></div>
                    {e.video && <a className="btn btn-ghost btn-sm" href={e.video} target="_blank" rel="noopener noreferrer">Video</a>}
                  </div>
                );
              })}
              {!approved && <p className="hint">Approve the plan to start checking exercises off.</p>}
            </>
          )}
        </div>
        <div className="card">
          <div className="row between"><h3>{DAYS_LONG[day]} meals</h3>{d && <span className="tag">{d.kcal} kcal</span>}</div>
          {d && <p className="muted small">Protein {d.protein} g · Carbs {d.carbs} g · Fat {d.fat} g</p>}
          {d?.meals.map((m) => (
            <div key={m.slot} className="meal" style={{ marginBottom: 12 }}>
              <div className="row between"><h4>{m.slot}</h4><span className="muted small">{m.kcal} kcal</span></div>
              <div className="muted small">{m.items.map((i) => `${i.name} ${Math.round(i.grams)} g`).join(", ")}</div>
            </div>
          ))}
          <p className="hint">Calories come from the food table. Real portions vary, so treat them as close estimates.</p>
        </div>
      </div>

      {approved && (
        <div className="card" style={{ marginTop: 24 }}>
          <h3>This week so far</h3>
          <div className="grid g3" style={{ marginBottom: 16 }}>
            <div><div className="row between small"><span>Exercises done</span><span>{doneEx} / {totalEx}</span></div><Bar value={doneEx} total={totalEx} /></div>
            <div><div className="row between small"><span>Today water</span><span>{dayLog(state, todayIndex()).water_ml} / {plan.targets.water_ml} ml</span></div><Bar value={dayLog(state, todayIndex()).water_ml} total={plan.targets.water_ml} water /></div>
            <div><div className="row between small"><span>Training days planned</span><span>{workoutDays.length}</span></div></div>
          </div>
          <h3>Renew for next week</h3>
          <p className="muted small">Tell us how the week felt. The next plan is built from what you did, then you approve it again.</p>
          <div className="two">
            <div className="field"><label htmlFor="sw">Weight at start (kg)</label><input id="sw" type="number" value={state.startWeight ?? ""} onChange={(e) => dispatch({ t: "weights", start: e.target.value ? Number(e.target.value) : null })} /></div>
            <div className="field"><label htmlFor="ew">Weight now (kg)</label><input id="ew" type="number" value={state.endWeight ?? ""} onChange={(e) => dispatch({ t: "weights", end: e.target.value ? Number(e.target.value) : null })} /></div>
          </div>
          <div className="chips" style={{ marginBottom: 16 }}>
            {([["too_easy", "Too easy"], ["just_right", "Just right"], ["too_hard", "Too hard"]] as const).map(([v, l]) => <button key={v} className="chip" aria-pressed={state.felt === v} onClick={() => dispatch({ t: "felt", felt: v })}>{l}</button>)}
          </div>
          <button className="btn btn-primary" disabled={busy} onClick={renew}>{busy ? "Building next week..." : "Create next week's plan"}</button>
        </div>
      )}
    </div>
  );
}
