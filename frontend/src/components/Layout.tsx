import { NavLink, Outlet } from "react-router-dom";
import { Badge } from "./Notice";
import { useSettings } from "../state/settings";

export function Layout() {
  const { mode, liveReady } = useSettings();
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="container topbar-inner">
          <NavLink to="/" className="brand">
            <span aria-hidden="true">🏋️</span> AetherFit <span className="brand-ai">AI</span>
          </NavLink>
          <nav aria-label="Main">
            <NavLink to="/" end>
              New plan
            </NavLink>
            <NavLink to="/plans">My plans</NavLink>
            <NavLink to="/models">Models</NavLink>
            <NavLink to="/settings">
              Settings{" "}
              <Badge tone={mode === "live" ? (liveReady ? "good" : "warn") : "sim"} title={mode === "live" ? "Gemini-generated plans" : "Rule-based simulated plans (no AI key needed)"}>
                {mode === "live" ? (liveReady ? "Live" : "Live · key missing") : "Simulated"}
              </Badge>
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main" className="container main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="container">
          AetherFit AI is an educational tool, not medical advice. Predictions come from models trained on a bundled synthetic dataset — see{" "}
          <NavLink to="/models">model details</NavLink>. Consult a qualified professional before starting an exercise programme.
        </div>
      </footer>
    </>
  );
}
