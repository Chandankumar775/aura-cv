import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Database, Cpu, Radio, Aperture, Lock, WifiOff } from "lucide-react";
import { api, type User } from "../lib/api";
import { useApp } from "../lib/app";
import { Mark } from "../components/Layout";
import { Button } from "../components/ui";
import TerrainScene from "../components/TerrainScene";

const PILLARS = [
  { icon: Database, title: "Training data", text: "Trigger injection, label flipping, systematic mislabelling, duplicate flooding, out-of-distribution insertion — rolled up to source-level risk." },
  { icon: Cpu, title: "Models", text: "Substitution, modification and backdoor behaviour, with methods matched to the access available and gaps declared." },
  { icon: Radio, title: "Inference records", text: "Signed, hash-chained records binding image, model, configuration and output. Alteration and replay are detectable." },
  { icon: Aperture, title: "Operating conditions", text: "Calibrated shift risk, characterised by factor, separating probable drift from suspicious manipulation." },
];

export default function Login() {
  const { setUser } = useApp();
  const nav = useNavigate();
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hosted, setHosted] = useState(false);
  useEffect(() => { api.get<{ hosted?: boolean }>("/health").then((h) => setHosted(!!h.hosted)).catch(() => {}); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const u = await api.post<User>("/auth/login", { username, password });
      setUser(u);
      nav("/");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden px-6 py-12">
      <TerrainScene intensity={1.15} />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(90%_70%_at_30%_45%,rgb(6_9_13/0.15),rgb(6_9_13/0.78)_100%)]" />
      <div className="relative grid w-full max-w-[1120px] gap-14 lg:grid-cols-[1.25fr_1fr]">
        <div className="relative flex flex-col justify-center before:pointer-events-none before:absolute before:-inset-x-16 before:-inset-y-10 before:-z-10 before:rounded-[48px] before:bg-[radial-gradient(closest-side,rgb(6_9_13/0.82),transparent)]">
          <div className="flex items-center gap-3.5">
            <Mark size={44} />
            <div>
              <div className="text-[22px] font-semibold tracking-[0.06em] text-ink">AURA-CV</div>
              <div className="text-[12.5px] text-ink-3">Air-Gapped Unified Risk &amp; Assurance for Computer Vision</div>
            </div>
          </div>
          <h1 className="mt-10 max-w-[580px] text-[38px] font-semibold leading-[1.1] tracking-[-0.03em] text-ink [text-wrap:balance]">
            Evidence-based integrity assurance for multi-contributor vision pipelines.
          </h1>
          <p className="mt-4 max-w-[520px] text-[14.5px] leading-relaxed text-ink-2">
            Assess contributed data, supplied models, inference records and new operating conditions — without assuming any source is trusted. Every flag carries its reason, evidence, confidence and a recommended disposition.
          </p>
          <div className="mt-10 grid max-w-[640px] grid-cols-1 gap-3 sm:grid-cols-2">
            {PILLARS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="glass rounded-xl p-4">
                <div className="flex items-center gap-2 text-[13px] font-medium text-ink"><Icon size={15} className="text-brand" /> {title}</div>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-3">{text}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="palette-in relative flex items-center">
          <form onSubmit={submit} className="glass-strong w-full rounded-2xl p-8">
            <div className="flex items-center gap-2 text-[12px] text-ink-3"><Lock size={13} /> Local sign-in · this workstation only</div>
            <h2 className="mt-3 text-[20px] font-semibold text-ink">Sign in to the assurance console</h2>
            <label className="mt-7 block">
              <span className="label-caps">Username</span>
              <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
                className="mt-2 h-11 w-full rounded-lg border border-line bg-canvas px-3.5 text-[14px] text-ink focus:border-brand/60 focus:outline-none" />
            </label>
            <label className="mt-4 block">
              <span className="label-caps">Password</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" autoFocus
                className="mt-2 h-11 w-full rounded-lg border border-line bg-canvas px-3.5 text-[14px] text-ink focus:border-brand/60 focus:outline-none" />
            </label>
            {err && <div className="mt-3 text-[13px] text-quarantine">{err}</div>}
            <div className="mt-6"><Button type="submit" variant="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button></div>
            <p className="mt-4 text-[12px] text-ink-3">No password recovery on an air-gapped system — an administrator resets passwords.</p>

            <div className="mt-7 rounded-lg border border-review/30 bg-review/[0.06] p-3.5 text-[12px] text-ink-2">
              <div className="font-semibold tracking-wide text-review">DEMONSTRATION BUILD</div>
              <p className="mt-1 text-ink-3">Seeded with an illustrative scenario; values are not measured results.</p>
              <div className="mt-2.5 grid grid-cols-2 gap-2 font-mono text-[11.5px]">
                <button type="button" onClick={() => { setUsername("analyst"); setPassword("aura-analyst"); }} className="rounded border border-line bg-canvas px-2 py-1.5 text-left hover:border-ink-3">analyst / aura-analyst</button>
                <button type="button" onClick={() => { setUsername("admin"); setPassword("aura-admin"); }} className="rounded border border-line bg-canvas px-2 py-1.5 text-left hover:border-ink-3">admin / aura-admin</button>
              </div>
            </div>
            <div className="mt-5 flex items-center gap-2 text-[11.5px] text-ink-3"><WifiOff size={12} /> {hosted ? "Hosted demonstration. The production build runs fully offline, with no cloud services or external APIs." : "Runs fully offline · no cloud services or external APIs"}</div>
          </form>
        </div>
      </div>
    </div>
  );
}
