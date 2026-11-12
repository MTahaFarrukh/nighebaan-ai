import { lazy, Suspense } from "react";
import { Loading } from "./components/ui";
import { HashRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import Analyze from "./pages/Analyze";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ModelLab = lazy(() => import("./pages/ModelLab"));
import Settings from "./pages/Settings";
import About from "./pages/About";
const navigation = [
  { path: "/analyze", label: "Analyze", icon: "⌕" },
  { path: "/dashboard", label: "Dashboard", icon: "▦" },
  { path: "/models", label: "Model Lab", icon: "◈" },
  { path: "/settings", label: "Settings", icon: "⚙" },
  { path: "/about", label: "About & Ethics", icon: "◎" },
];
export default function App() {
  return (
    <HashRouter>
      <a
        href="#main"
        className="skip-link"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to content
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <a className="brand" href="#/analyze">
            <span className="brand-mark" aria-hidden="true">
              N
            </span>
            <span>
              Nigehbaan<span className="brand-ai"> AI</span>
              <small>YOUR DIGITAL LOOKOUT</small>
            </span>
          </a>
          <div className="nav-caption">WORKSPACE</div>
          <nav aria-label="Main navigation">
            {navigation.map((item) => (
              <NavLink key={item.path} to={item.path}>
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-note">
            <span className="status-dot" /> Local demo
            <p>
              Private by design.
              <br />
              Built for informed decisions.
            </p>
            <span className="badge neutral">Experimental</span>
          </div>
        </aside>
        <div className="workspace">
          <div className="topbar">
            <span>
              AI &amp; Expert Systems <span className="muted">/ Nigehbaan</span>
            </span>
            <span className="small muted">Text, links & media</span>
          </div>
          <main id="main" tabIndex={-1}>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/analyze" element={<Analyze />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/models" element={<ModelLab />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/about" element={<About />} />
                <Route path="*" element={<Navigate to="/analyze" replace />} />
              </Routes>
            </Suspense>
            <footer>
              Nigehbaan AI <span>Human judgment stays in control.</span>
            </footer>
          </main>
        </div>
      </div>
    </HashRouter>
  );
}
