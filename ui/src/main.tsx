import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import "./index.css";
import { api, type User } from "./lib/api";
import { AppProvider, useApp } from "./lib/app";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AssessmentView from "./pages/AssessmentView";
import NewAssessment from "./pages/NewAssessment";
import RunAssessment from "./pages/RunAssessment";
import { Assessments, Audit, Findings, Reports } from "./pages/Lists";
import { Assets, AttackLab, Coverage, Settings } from "./pages/Admin";

function Gate({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useApp();
  const [checked, setChecked] = useState(false);
  const nav = useNavigate();
  useEffect(() => {
    api.get<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setChecked(true));
    const onAuth = () => { setUser(null); nav("/login"); };
    window.addEventListener("aura:unauthenticated", onAuth);
    return () => window.removeEventListener("aura:unauthenticated", onAuth);
  }, []);
  if (!checked) return <div className="p-10"><Loading label="Starting" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Gate><Layout /></Gate>}>
        <Route index element={<Dashboard />} />
        <Route path="/assessments" element={<Assessments />} />
        <Route path="/assessments/new" element={<NewAssessment />} />
        <Route path="/assessments/:id/run" element={<RunAssessment />} />
        <Route path="/assessments/:id/:tab" element={<AssessmentView />} />
        <Route path="/assessments/:id" element={<AssessmentView />} />
        <Route path="/findings" element={<Findings />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/assets/:type" element={<Assets />} />
        <Route path="/attack-lab" element={<AttackLab />} />
        <Route path="/settings/:section" element={<Settings />} />
        <Route path="/coverage" element={<Coverage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
