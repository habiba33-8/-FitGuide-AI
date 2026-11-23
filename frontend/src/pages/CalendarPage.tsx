import { useState } from "react";
import { Link } from "react-router-dom";
import { NeedProfile, NeedPlan } from "../components";
import { useStore } from "../store";
import { DAYS_LONG, label, todayIndex, weekDates } from "../util";

export default function CalendarPage() {
  const { state } = useStore();
  const [sel, setSel] = useState(todayIndex());
  const { plan, profile } = state;
  if (!profile) return <NeedProfile what="The calendar" />;
  if (!plan || plan.status !== "approved") return <NeedPlan what="The calendar" />;
  const dates = weekDates();
  const w = plan.workouts.find((x) => x.day === sel);
  const d = plan.diet.find((x) => x.day === sel);
  return (
    <div className="container page">
      <div className="eyebrow">Week {plan.week_index}</div>
      <h1 style={{ fontSize: "2.4rem" }}>Your week at a glance</h1>
      <p className="muted">The same schedule as your plan, laid out by date. Select a day for details. To change anything, ask the <Link to="/chat">coach chat</Link>.</p>
      <div className="cal" style={{ margin: "24px 0" }}>
        {dates.map((dt, i) => {
          const wd = plan.workouts.find((x) => x.day === i);
          const dd = plan.diet.find((x) => x.day === i);
          const done = wd ? wd.exercises.filter((_, k) => state.checks[`${i}:${k}`]).length : 0;
          return (
            <button key={i} className={`cal-day${i === todayIndex() ? " today" : ""}${i === sel ? " sel" : ""}`} onClick={() => setSel(i)} aria-pressed={i === sel}>
              <div className="muted small">{dt.toLocaleDateString("en", { weekday: "short" })}</div>
              <div className="d">{dt.getDate()}</div>
              {wd?.rest ? <span className="cal-pill r">Rest</span> : <span className="cal-pill w">{wd?.focus.map(label).join(" + ")} {wd && wd.exercises.length ? `· ${done}/${wd.exercises.length}` : ""}</span>}
              {dd && <span className="cal-pill f">{dd.kcal} kcal</span>}
            </button>
          );
        })}
      </div>
      <div className="grid g2">
        <div className="card"><h3>{DAYS_LONG[sel]} training</h3>
          {!w || w.rest ? <p className="muted">Rest day.</p> : <ul className="muted">{w.exercises.map((e) => <li key={e.exercise_id}>{e.name}: {e.sets} × {e.reps}</li>)}</ul>}
        </div>
        <div className="card"><h3>{DAYS_LONG[sel]} food</h3>
          {d?.meals.map((m) => <p key={m.slot} className="muted" style={{ marginBottom: 8 }}><b style={{ textTransform: "capitalize", color: "var(--ink)" }}>{m.slot}</b> ({m.kcal} kcal): {m.items.map((i) => i.name).join(", ")}</p>)}
        </div>
      </div>
    </div>
  );
}
