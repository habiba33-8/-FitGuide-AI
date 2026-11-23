import { NavLink, Route, Routes, Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Landing from "./pages/Landing";
import Onboarding from "./pages/Onboarding";
import Chat from "./pages/Chat";
import PlanPage from "./pages/PlanPage";
import CalendarPage from "./pages/CalendarPage";
import Exercises from "./pages/Exercises";
import { useStore } from "./store";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/chat", label: "Coach chat" },
  { to: "/plan", label: "Weekly plan" },
  { to: "/calendar", label: "Calendar" },
  { to: "/exercises", label: "Exercises" },
];

export function Logo() {
  return (
    <span className="brand-mark" aria-hidden>
      <svg width="18" height="18" viewBox="0 0 32 32"><path d="M4 18h6l3-9 5 15 3-6h7" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </span>
  );
}

export default function App() {
  const { state } = useStore();
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return (
    <>
      <header className="nav">
        <div className="container nav-inner">
          <Link to="/" className="brand"><Logo />FitGuide AI</Link>
          <nav className="nav-links" aria-label="Main">
            {links.map((l) => <NavLink key={l.to} to={l.to} end={l.end}>{l.label}</NavLink>)}
            <NavLink to="/start">{state.profile ? "Profile" : "Get started"}</NavLink>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/start" element={<Onboarding />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/exercises" element={<Exercises />} />
          <Route path="*" element={<div className="container page empty"><h2>Page not found</h2><Link to="/">Back home</Link></div>} />
        </Routes>
      </main>
    </>
  );
}
