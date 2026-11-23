import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Exercise } from "../types";
import { label } from "../util";

const LEVELS = ["beginner", "intermediate", "advanced"];

export default function Exercises() {
  const [all, setAll] = useState<Exercise[]>([]);
  const [err, setErr] = useState("");
  const [mode, setMode] = useState("");
  const [level, setLevel] = useState("");
  const [muscle, setMuscle] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => { api.exercises().then(setAll).catch((e) => setErr(e.message)); }, []);
  const muscles = useMemo(() => [...new Set(all.map((e) => e.muscle))].sort(), [all]);
  const shown = all.filter((e) => (!mode || e.mode === mode) && (!level || e.level === level) && (!muscle || e.muscle === muscle) && e.name.toLowerCase().includes(q.toLowerCase()));
  const pick = (cur: string, set: (v: string) => void, v: string) => set(cur === v ? "" : v);
  return (
    <div className="container page">
      <div className="eyebrow">Exercise library</div>
      <h1 style={{ fontSize: "2.4rem" }}>Find the right movement</h1>
      <p className="muted">Each exercise has form cues and a link to a tutorial video on YouTube. Videos belong to their creators and open on YouTube.</p>
      {err && <div className="notice danger">{err}</div>}
      <div className="card" style={{ margin: "20px 0" }}>
        <div className="field"><label htmlFor="s">Search</label><input id="s" value={q} onChange={(e) => setQ(e.target.value)} placeholder="squat, row, plank" /></div>
        <div className="row" style={{ gap: 24, alignItems: "flex-start" }}>
          <div><div className="hint">Equipment</div><div className="chips">
            <button className="chip" aria-pressed={mode === "without_machine"} onClick={() => pick(mode, setMode, "without_machine")}>Without machine</button>
            <button className="chip" aria-pressed={mode === "with_machine"} onClick={() => pick(mode, setMode, "with_machine")}>With machine</button></div></div>
          <div><div className="hint">Level</div><div className="chips">{LEVELS.map((l) => <button key={l} className="chip" aria-pressed={level === l} onClick={() => pick(level, setLevel, l)}>{label(l)}</button>)}</div></div>
        </div>
        <div className="hint" style={{ marginTop: 12 }}>Muscle</div>
        <div className="chips">{muscles.map((m) => <button key={m} className="chip" aria-pressed={muscle === m} onClick={() => pick(muscle, setMuscle, m)}>{label(m)}</button>)}</div>
      </div>
      <p className="muted small">{shown.length} exercises</p>
      <div className="grid g3">
        {shown.map((e) => (
          <div key={e.id} className="card ex-card">
            <div className="row between"><h3 style={{ margin: 0 }}>{e.name}</h3></div>
            <div className="chips"><span className="tag">{label(e.muscle)}</span><span className="tag">{label(e.level)}</span><span className="tag">{e.mode === "with_machine" ? "Machine" : "No machine"}</span></div>
            <ul>{e.cues.slice(0, 3).map((c) => <li key={c}>{c}</li>)}</ul>
            <p className="small" style={{ margin: 0 }}><b>Avoid:</b> <span className="muted">{e.common_mistake}</span></p>
            {e.video && <a className="btn btn-ghost btn-sm" href={e.video.url} target="_blank" rel="noopener noreferrer" title={`${e.video.title} (${e.video.channel})`}>Watch on YouTube</a>}
            {e.video && <span className="hint">{e.video.channel}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
