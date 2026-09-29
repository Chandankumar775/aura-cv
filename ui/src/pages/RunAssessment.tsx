import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CircleCheck, CircleDashed, CircleX, LoaderCircle, Square } from "lucide-react";
import { api, type Assessment } from "../lib/api";
import { useApi, useEventStream } from "../lib/hooks";
import { moduleNames } from "../lib/format";
import { Button, Card, cx, ErrorState, Loading, PageHeader, StatusPill } from "../components/ui";

type CheckState = { id: string; name?: string; state: "queued" | "running" | "done" | "unavailable" | "error"; findings?: number; reason?: string; fallback?: string | null };

export default function RunAssessment() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const asm = useApi<Assessment>(`/assessments/${id}`);
  const [mods, setMods] = useState<Record<string, { status: string; checks: CheckState[] }>>({});
  const [current, setCurrent] = useState<string | null>(null);
  const [flags, setFlags] = useState(0);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    if (asm.data && ["COMPLETED", "FAILED", "CANCELLED"].includes(asm.data.status)) nav(`/assessments/${id}/overview`, { replace: true });
    if (asm.data && !Object.keys(mods).length) setMods(Object.fromEntries(asm.data.modules.map((m) => [m, { status: "PENDING", checks: [] }])));
  }, [asm.data]);

  // Fallback for hosts that buffer the event stream: poll status and move on when finished.
  useEffect(() => {
    const t = window.setInterval(async () => {
      try {
        const a = await api.get<Assessment>(`/assessments/${id}`);
        if (["COMPLETED", "FAILED", "CANCELLED"].includes(a.status)) nav(`/assessments/${id}/overview`, { replace: true });
      } catch { /* shown by the main loader */ }
    }, 3000);
    return () => window.clearInterval(t);
  }, [id]);

  useEventStream(`/api/v1/assessments/${id}/events`, (ev) => {
    if (ev.type === "module_started") {
      setCurrent(ev.module);
      setMods((m) => ({ ...m, [ev.module]: { status: "RUNNING", checks: ev.checks.map((c: { id: string; name: string }) => ({ id: c.id, name: c.name, state: "queued" })) } }));
    }
    const upd = (cid: string, patch: Partial<CheckState>) => setMods((m) => {
      const out = { ...m };
      for (const k of Object.keys(out)) {
        const idx = out[k].checks.findIndex((c) => c.id === cid);
        if (idx >= 0 && out[k].status === "RUNNING") {
          const checks = [...out[k].checks];
          checks[idx] = { ...checks[idx], ...patch };
          out[k] = { ...out[k], checks };
        }
      }
      return out;
    });
    if (ev.type === "check_started") upd(ev.check_id, { state: "running", name: ev.name });
    if (ev.type === "check_completed") { upd(ev.check_id, { state: "done", findings: ev.findings }); setFlags((f) => f + ev.findings); }
    if (ev.type === "check_unavailable") upd(ev.check_id, { state: ev.status === "ERROR" ? "error" : "unavailable", reason: ev.reason, fallback: ev.fallback_used });
    if (ev.type === "module_completed") setMods((m) => ({ ...m, [ev.module]: { ...m[ev.module], status: ev.status } }));
    if (ev.type === "assessment_completed") {
      setDone(ev.status);
      setTimeout(() => nav(`/assessments/${id}/overview`), 1400);
    }
  });

  if (asm.loading) return <Loading />;
  if (asm.error || !asm.data) return <ErrorState error={asm.error} />;
  const list = Object.values(mods);
  const moduleDone = list.filter((m) => !["PENDING", "RUNNING"].includes(m.status)).length;
  const running = list.find((m) => m.status === "RUNNING");
  const frac = running && running.checks.length ? running.checks.filter((c) => ["done", "unavailable", "error"].includes(c.state)).length / running.checks.length : 0;
  const progress = (moduleDone + frac) / Math.max(list.length, 1);

  return (
    <div>
      <PageHeader title={asm.data.name}
        sub={<>Access <span className="font-mono">{asm.data.access_level_used}</span> · seed <span className="font-mono">{asm.data.seed}</span> · live progress from the scheduler</>}
        right={!done && <Button variant="danger" icon={<Square size={13} />} onClick={() => api.post(`/assessments/${id}/cancel`)}>Cancel</Button>} />
      <Card className="mb-6">
        <div className="flex items-center justify-between text-[13px]">
          <span className="flex items-center gap-2 text-ink-2">{done ? <CircleCheck size={16} className="text-accept" /> : <LoaderCircle size={16} className="animate-spin text-brand" />}
            {done ? `Assessment ${done.toLowerCase()} — opening results…` : current ? `Running ${moduleNames[current]}…` : "Queued…"}</span>
          <span className="font-mono text-ink-3">{flags} flags so far</span>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full rounded-full bg-brand transition-all duration-500" style={{ width: `${done ? 100 : Math.min(99, Math.max(3, progress * 100))}%` }} /></div>
      </Card>
      <div className="grid gap-4 xl:grid-cols-2">
        {Object.entries(mods).map(([m, s]) => (
          <Card key={m} className="!p-4">
            <div className="mb-3 flex items-center justify-between"><div className="text-[14px] font-medium text-ink"><span className="font-mono text-[11px] text-ink-3">{m}</span> {moduleNames[m]}</div><StatusPill status={s.status} /></div>
            {s.checks.length === 0 ? <div className="text-[12.5px] text-ink-3">Waiting…</div> : (
              <div className="space-y-1">
                {s.checks.map((c) => (
                  <div key={c.id} className={cx("flex items-start gap-2.5 rounded-md px-2 py-1.5 text-[12.5px] transition-colors", c.state === "running" && "bg-brand/[0.07]")}>
                    {c.state === "queued" && <span className="mt-1 h-3 w-3 rounded-full border border-line" />}
                    {c.state === "running" && <LoaderCircle size={14} className="mt-0.5 animate-spin text-brand" />}
                    {c.state === "done" && <CircleCheck size={14} className="mt-0.5 text-accept" />}
                    {c.state === "unavailable" && <CircleDashed size={14} className="mt-0.5 text-gap" />}
                    {c.state === "error" && <CircleX size={14} className="mt-0.5 text-quarantine" />}
                    <div className="flex-1">
                      <span className={c.state === "queued" ? "text-ink-3" : "text-ink"}>{c.name ?? c.id}</span>
                      {c.state === "unavailable" && <div className="text-[11.5px] text-gap">UNAVAILABLE — {c.reason}{c.fallback && ` · fallback ${c.fallback}`}</div>}
                    </div>
                    {c.state === "done" && <span className={cx("font-mono text-[11px]", c.findings ? "text-review" : "text-ink-3")}>{c.findings} flag{c.findings === 1 ? "" : "s"}</span>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
