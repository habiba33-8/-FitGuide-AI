import { Link } from "react-router-dom";

export function NeedProfile({ what }: { what: string }) {
  return (
    <div className="container page">
      <div className="card empty">
        <h2>Tell us about you first</h2>
        <p className="muted">{what} is built from your body, goal and training level. It takes about a minute.</p>
        <Link className="btn btn-primary" to="/start">Start onboarding</Link>
      </div>
    </div>
  );
}

export function NeedPlan({ what }: { what: string }) {
  return (
    <div className="container page">
      <div className="card empty">
        <h2>No plan yet</h2>
        <p className="muted">{what} shows up after you create and approve your weekly plan.</p>
        <Link className="btn btn-primary" to="/plan">Go to the plan</Link>
      </div>
    </div>
  );
}

export function Bar({ value, total, water }: { value: number; total: number; water?: boolean }) {
  const p = total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0;
  return <div className={`bar${water ? " water" : ""}`} role="progressbar" aria-valuenow={Math.round(p)} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${p}%` }} /></div>;
}
