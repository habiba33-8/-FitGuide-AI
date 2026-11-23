import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Bar, NeedProfile } from "../components";
import { resizeToJpeg } from "../image";
import { dayLog, sessionForApi, useStore } from "../store";
import type { Action, ChatMessage, SourceRef, VisionResult } from "../types";
import { todayIndex } from "../util";

type Extra = { sources?: SourceRef[]; actions?: Action[]; photo?: string; vision?: VisionResult; degraded?: boolean; handled?: boolean[] };
type Item = ChatMessage & { extra?: Extra };

const SUGGEST = {
  en: ["I ate 2 eggs and a slice of bread", "How much protein do I need?", "I drank a glass of water", "Swap squats, my knee hurts"],
  ar: ["أكلت بيضتين وعيش", "أنا محتاج بروتين كام؟", "شربت كوباية مية", "غيّر السكوات، ركبتي بتوجعني"],
};

function VisionCard({ v, onConfirm, onDismiss }: { v: VisionResult; onConfirm: (items: { food_id: string; grams: number }[]) => void; onDismiss: () => void }) {
  const [rows, setRows] = useState(v.items.filter((i) => i.matched).map((i) => ({ ...i, kpg: i.kcal / i.grams })));
  const [totals, setTotals] = useState<{ kcal: number } | null>(null);
  const unmatched = v.items.filter((i) => !i.matched);
  useEffect(() => {
    if (!rows.length) { setTotals({ kcal: 0 }); return; }
    const id = setTimeout(() => { api.compute(rows.map((r) => ({ food_id: r.food_id!, grams: r.grams }))).then((r) => setTotals(r.totals)).catch(() => undefined); }, 250);
    return () => clearTimeout(id);
  }, [rows]);
  if (!v.is_food) return <div className="notice warn card-inline">That does not look like food. Try another photo.</div>;
  return (
    <div className="card card-inline">
      <h3>Photo analysis</h3>
      <p className="small muted">{v.disclaimer} Estimated range: {v.kcal_low} to {v.kcal_high} kcal.</p>
      <table className="t">
        <thead><tr><th>Food</th><th>Grams</th><th>kcal</th><th /></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.food_name}</td>
              <td><input type="number" min={1} max={3000} aria-label={`Grams of ${r.food_name}`} value={r.grams} onChange={(e) => setRows(rows.map((x, k) => (k === i ? { ...x, grams: Math.max(1, Number(e.target.value)) } : x)))} /></td>
              <td>{Math.round(r.kpg * r.grams)}</td>
              <td><button className="btn btn-ghost btn-sm" aria-label={`Remove ${r.food_name}`} onClick={() => setRows(rows.filter((_, k) => k !== i))}>Remove</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {unmatched.length > 0 && <p className="small muted" style={{ marginTop: 8 }}>Not in the food table, so not counted: {unmatched.map((u) => u.name).join(", ")}.</p>}
      {v.notes && <p className="small muted">{v.notes}</p>}
      <div className="row between" style={{ marginTop: 12 }}>
        <b>Total: {totals ? Math.round(totals.kcal) : "..."} kcal</b>
        <div className="row"><button className="btn btn-ghost btn-sm" onClick={onDismiss}>Dismiss</button>
          <button className="btn btn-primary btn-sm" disabled={!rows.length} onClick={() => onConfirm(rows.map((r) => ({ food_id: r.food_id!, grams: r.grams })))}>Add to today</button></div>
      </div>
    </div>
  );
}

export default function Chat() {
  const { state, dispatch } = useStore();
  const [items, setItems] = useState<Item[]>(() => state.messages.map((m) => ({ ...m })));
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(true);
  const [err, setErr] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const file = useRef<HTMLInputElement>(null);
  const lang = state.chatLang;
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [items, busy]);

  if (!state.profile) return <NeedProfile what="The coach chat" />;
  const plan = state.plan;
  const log = dayLog(state, todayIndex());
  const kcal = Math.round(log.meals.reduce((a, m) => a + m.kcal, 0));
  const t = plan?.targets;

  const persist = (list: Item[]) => dispatch({ t: "messages", messages: list.slice(-30).map(({ role, content }) => ({ role, content })) });
  const patch = (idx: number, fn: (e: Extra) => Extra) => setItems((l) => l.map((m, i) => (i === idx ? { ...m, extra: fn(m.extra ?? {}) } : m)));

  async function send(content: string) {
    const msg = content.trim();
    if (!msg || busy) return;
    setErr(""); setText("");
    const next: Item[] = [...items, { role: "user", content: msg }];
    setItems(next); setBusy(true);
    try {
      const r = await api.chat(next.slice(-12).map(({ role, content }) => ({ role, content })), lang, sessionForApi(state));
      if (r.plan) dispatch({ t: "setPlan", plan: { ...r.plan, status: "approved" } });
      const out: Item[] = [...next, { role: "assistant", content: r.reply, extra: { sources: r.sources, actions: r.actions, degraded: r.degraded, handled: r.actions.map(() => false) } }];
      setItems(out); persist(out);
    } catch (e) { setErr(e instanceof Error ? e.message : "Something went wrong."); }
    finally { setBusy(false); }
  }

  async function photo(f: File | undefined) {
    if (!f || busy) return;
    setErr(""); setBusy(true);
    try {
      const img = await resizeToJpeg(f);
      const next: Item[] = [...items, { role: "user", content: lang === "ar" ? "صورة وجبة" : "Meal photo", extra: { photo: img.dataUrl } }];
      setItems(next);
      const v = await api.vision(img.base64, "image/jpeg", lang);
      const out: Item[] = [...next, { role: "assistant", content: v.is_food ? (lang === "ar" ? "ده تقديري للوجبة. راجع الكميات وبعدين أكد." : "Here is my estimate. Check the amounts, then confirm.") : (lang === "ar" ? "الصورة دي مش شبه أكل." : "That does not look like food."), extra: { vision: v } }];
      setItems(out); persist(out);
    } catch (e) { setErr(e instanceof Error ? e.message : "Photo analysis failed."); }
    finally { setBusy(false); if (file.current) file.current.value = ""; }
  }

  function confirmAction(mi: number, ai: number, a: Action) {
    if (a.type === "log_meal") dispatch({ t: "addMeal", items: a.items });
    if (a.type === "log_water") dispatch({ t: "addWater", ml: a.water_ml });
    patch(mi, (e) => ({ ...e, handled: (e.handled ?? []).map((h, i) => (i === ai ? true : h)) }));
  }

  return (
    <div className="chat-wrap">
      <div className="chat-head">
        <div><h2 style={{ margin: 0, fontSize: "1.5rem" }}>Coach chat</h2><span className="muted small">Ask, log meals, send a photo, or request plan changes.</span></div>
        <div className="seg" role="group" aria-label="Chat language">
          <button aria-selected={lang === "en"} onClick={() => dispatch({ t: "lang", lang: "en" })}>English</button>
          <button aria-selected={lang === "ar"} onClick={() => dispatch({ t: "lang", lang: "ar" })}>العربية</button>
        </div>
      </div>
      <div className="msgs" aria-live="polite">
        {items.length === 0 && (
          <div className="notice">Hi{state.profile.name ? ` ${state.profile.name}` : ""}. I can answer nutrition and training questions from a vetted knowledge base, log what you eat or drink, and change your plan. Calories always come from a food table, and I ask before I log anything.
            {!plan && " You have no plan yet: build one from the Weekly plan page."}</div>
        )}
        {items.map((m, mi) => {
          const rtl = /[\u0600-\u06FF]/.test(m.content);
          return (
            <div key={mi} style={{ display: "contents" }}>
              <div className={`msg ${m.role}${rtl ? " rtl" : ""}`}>
                {m.extra?.photo && <img src={m.extra.photo} alt="Your meal" />}
                {m.content}
                {m.extra?.degraded && <div className="small" style={{ marginTop: 6, opacity: .8 }}>The AI model is not available, so this answer comes straight from the knowledge base.</div>}
                {m.extra?.sources && m.extra.sources.length > 0 && (
                  <details className="sources"><summary>Sources ({m.extra.sources.length})</summary>
                    {m.extra.sources.map((s) => <div key={s.id}><b>{s.title}</b>: {s.snippet}</div>)}</details>
                )}
              </div>
              {m.extra?.vision && !m.extra.handled?.[0] && (
                <VisionCard v={m.extra.vision} onDismiss={() => patch(mi, (e) => ({ ...e, handled: [true] }))}
                  onConfirm={async (rows) => { try { const r = await api.compute(rows); dispatch({ t: "addMeal", items: r.items }); patch(mi, (e) => ({ ...e, handled: [true] })); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } }} />
              )}
              {m.extra?.actions?.map((a, ai) => {
                if (a.type === "plan_changed") return <div key={ai} className="notice card-inline">Plan updated: {a.summary}</div>;
                if (a.type === "refused_plan_change") return <div key={ai} className="notice warn card-inline">Not changed: {a.summary}</div>;
                const done = m.extra?.handled?.[ai];
                return (
                  <div key={ai} className="card card-inline">
                    <b>{a.type === "log_meal" ? "Log this meal?" : "Log water?"}</b>
                    {a.type === "log_meal" ? (
                      <table className="t"><tbody>{a.items.map((i, k) => <tr key={k}><td>{i.name}</td><td>{Math.round(i.grams)} g</td><td>{i.kcal} kcal</td></tr>)}</tbody></table>
                    ) : <p className="muted">{a.water_ml} ml</p>}
                    <div className="row" style={{ marginTop: 10 }}>
                      {done ? <span className="tag ok">Added</span> : <button className="btn btn-primary btn-sm" onClick={() => confirmAction(mi, ai, a)}>Add to today</button>}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
        {busy && <div className="msg assistant muted">Thinking...</div>}
        {err && <div className="notice danger card-inline">{err}</div>}
        <div ref={end} />
      </div>
      <div>
        {items.length === 0 && <div className="suggest">{SUGGEST[lang].map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>}
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <input ref={file} type="file" accept="image/*" hidden onChange={(e) => photo(e.target.files?.[0])} />
          <button type="button" className="btn btn-ghost" aria-label="Upload a meal photo" disabled={busy} onClick={() => file.current?.click()}>Photo</button>
          <textarea rows={1} dir="auto" value={text} placeholder={lang === "ar" ? "اكتب رسالتك" : "Message your coach"} aria-label="Message"
            onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} />
          <button className="btn btn-primary" disabled={busy || !text.trim()}>Send</button>
        </form>
      </div>
      {t && (
        <aside className="widget" aria-label="Today">
          <button className="toggle" aria-label={open ? "Collapse" : "Expand"} onClick={() => setOpen(!open)}>{open ? "–" : "+"}</button>
          <div className="small" style={{ color: "#cbb9ff" }}>Today</div>
          {open ? (
            <>
              <div className="row between small" style={{ marginTop: 8 }}><span>Calories</span><span>{kcal} / {t.calories}</span></div><Bar value={kcal} total={t.calories} />
              <div className="row between small"><span>Water</span><span>{log.water_ml} / {t.water_ml} ml</span></div><Bar value={log.water_ml} total={t.water_ml} water />
              <button className="water-btn" onClick={() => dispatch({ t: "addWater", ml: 250 })}>+ 250 ml water</button>
            </>
          ) : <div className="small">{kcal} kcal · {log.water_ml} ml</div>}
        </aside>
      )}
    </div>
  );
}
