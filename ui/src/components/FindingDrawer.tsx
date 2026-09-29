import { useEffect, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Copy, X } from "lucide-react";
import { api, type Disposition, type Finding } from "../lib/api";
import { useApp } from "../lib/app";
import { useKey } from "../lib/hooks";
import { dateTime, fmtValue, humanKey, moduleNames } from "../lib/format";
import {
  Button, ConfidenceMeter, cx, DispositionBadge, KeyValue, Loading, Notice, RequirementTag, SeverityBadge, Thumb, VerificationChecklist,
} from "./ui";

const RESERVED = new Set(["metrics", "thresholds", "sample_ids", "artefact_ids", "verification_steps"]);

function DecisionForm({ finding, onDone }: { finding: Finding; onDone: (f: Finding) => void }) {
  const { toast } = useApp();
  const [choice, setChoice] = useState<Disposition>(finding.effective_disposition);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { setChoice(finding.effective_disposition); setText(""); setErr(null); }, [finding.id]);

  useKey((e) => {
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === "TEXTAREA" || tag === "INPUT") {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
      return;
    }
    const map: Record<string, Disposition> = { a: "ACCEPT", r: "REVIEW", q: "QUARANTINE" };
    if (map[e.key.toLowerCase()]) {
      setChoice(map[e.key.toLowerCase()]);
      (document.getElementById("justification") as HTMLTextAreaElement | null)?.focus();
      e.preventDefault();
    }
  });

  const submit = async () => {
    if (!text.trim()) { setErr("A justification is required: it is recorded in the audit log with your identity."); return; }
    setBusy(true);
    try {
      const f = await api.post<Finding>(`/findings/${finding.id}/decisions`, { decision: choice, justification: text });
      setText("");
      setErr(null);
      onDone(f);
      toast({ tone: choice === "QUARANTINE" ? "danger" : choice === "REVIEW" ? "warn" : "ok", title: `Decision recorded: ${choice}`, detail: `${finding.check_name} · signed into the audit log with your identity.` });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const opts: { v: Disposition; key: string; tone: string }[] = [
    { v: "ACCEPT", key: "A", tone: "border-accept/50 bg-accept/12 text-accept" },
    { v: "REVIEW", key: "R", tone: "border-review/50 bg-review/12 text-review" },
    { v: "QUARANTINE", key: "Q", tone: "border-quarantine/50 bg-quarantine/12 text-quarantine" },
  ];
  return (
    <div className="glass-inset rounded-xl p-4">
      <div className="label-caps mb-3">Analyst decision</div>
      <div className="grid grid-cols-3 gap-2">
        {opts.map((o) => (
          <button key={o.v} onClick={() => setChoice(o.v)}
            className={cx("flex items-center justify-between rounded-lg border px-3 py-2 text-[12.5px] font-semibold tracking-wide transition-colors",
              choice === o.v ? o.tone : "border-line text-ink-3 hover:text-ink-2")}>
            {o.v}
            <kbd className="rounded border border-current/30 px-1 font-mono text-[10px] opacity-70">{o.key}</kbd>
          </button>
        ))}
      </div>
      <textarea id="justification" value={text} onChange={(e) => setText(e.target.value)} rows={3}
        placeholder="Justification (required) — what you checked and why you decided this."
        className="mt-3 w-full resize-none rounded-lg border border-line bg-canvas px-3 py-2.5 text-[13px] text-ink placeholder:text-ink-3 focus:border-brand/60 focus:outline-none" />
      {err && <div className="mt-2 text-[12.5px] text-quarantine">{err}</div>}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11.5px] text-ink-3">Recorded in the audit log · <kbd className="font-mono">Ctrl+Enter</kbd> to submit</span>
        <Button variant="primary" onClick={submit} disabled={busy}>{busy ? "Recording…" : "Record decision"}</Button>
      </div>
    </div>
  );
}

function Evidence({ f }: { f: Finding }) {
  const ev = f.evidence;
  const metrics = Object.entries(ev.metrics ?? {}).filter(([, v]) => typeof v !== "object" || Array.isArray(v));
  const nested = Object.entries(ev.metrics ?? {}).filter(([, v]) => v && typeof v === "object" && !Array.isArray(v));
  const thresholds = Object.entries(ev.thresholds ?? {});
  const extras = Object.entries(ev).filter(([k, v]) => !RESERVED.has(k) && v !== null && v !== undefined && !["overlay", "histogram", "triggers", "probes", "clusters"].includes(k));
  const overlay = (ev.overlay as any) ?? null;
  return (
    <div className="space-y-5">
      {metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line">
          {metrics.map(([k, v]) => (
            <div key={k} className="bg-panel px-3.5 py-2.5">
              <div className="text-[11px] text-ink-3">{humanKey(k)}</div>
              <div className="mt-0.5 break-all font-mono text-[13px] text-ink">{fmtValue(v)}</div>
            </div>
          ))}
        </div>
      )}
      {nested.map(([k, v]) => (
        <div key={k}>
          <div className="mb-1.5 text-[11px] text-ink-3">{humanKey(k)}</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(v as Record<string, unknown>).map(([a, b]) => (
              <span key={a} className="rounded border border-line bg-raised px-2 py-0.5 text-[12px] text-ink-2">{a} <span className="font-mono text-ink">{fmtValue(b)}</span></span>
            ))}
          </div>
        </div>
      ))}
      {thresholds.length > 0 && (
        <div className="text-[12.5px] text-ink-3">
          Thresholds: {thresholds.map(([k, v], i) => <span key={k}>{i > 0 && " · "}<span className="text-ink-2">{humanKey(k)}</span> <span className="font-mono">{fmtValue(v)}</span></span>)}
        </div>
      )}
      {extras.length > 0 && (
        <KeyValue items={extras.map(([k, v]) => [humanKey(k), <span className="text-ink-2">{fmtValue(v)}</span>])} />
      )}
      {ev.verification_steps && ev.verification_steps.length > 0 && <VerificationChecklist steps={ev.verification_steps} />}
      {ev.sample_ids?.length > 0 && (
        <div>
          <div className="mb-2 text-[11px] text-ink-3">Affected samples ({ev.sample_ids.length}{ev.sample_ids.length > 12 ? ", first 12 shown" : ""})</div>
          <div className="grid grid-cols-6 gap-2">
            {ev.sample_ids.slice(0, 12).map((s) => <Thumb key={s} id={s} size={76} overlay={overlay} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function CopyJson({ f }: { f: Finding }) {
  const [done, setDone] = useState(false);
  const copy = () => {
    const keys = ["id", "assessment_id", "module", "check_id", "created_at", "status", "reason", "evidence", "confidence", "severity", "affected_asset", "recommended_disposition", "limitations"] as const;
    const out = Object.fromEntries(keys.map((k) => [k, (f as any)[k]]));
    navigator.clipboard?.writeText(JSON.stringify(out, null, 2));
    setDone(true);
    setTimeout(() => setDone(false), 1400);
  };
  return (
    <button onClick={copy} className="flex items-center gap-1.5 rounded px-2 py-1.5 text-[12px] text-ink-3 hover:bg-raised hover:text-ink" title="Copy the schema-valid finding as JSON">
      {done ? <Check size={14} className="text-accept" /> : <Copy size={14} />} {done ? "Copied" : "Copy JSON"}
    </button>
  );
}

export default function FindingDrawer() {
  const { drawer, closeFinding, openFinding, bump } = useApp();
  const [f, setF] = useState<Finding | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!drawer) { setF(null); return; }
    setF(null);
    api.get<Finding>(`/findings/${drawer.id}`).then(setF).catch((e) => setErr(e.message));
  }, [drawer?.id]);

  const idx = drawer ? drawer.ids.indexOf(drawer.id) : -1;
  const go = (d: number) => {
    if (!drawer) return;
    const n = drawer.ids[idx + d];
    if (n) openFinding(n, drawer.ids);
  };
  useKey((e) => {
    const tag = (e.target as HTMLElement)?.tagName;
    if (e.key === "Escape") closeFinding();
    if (tag === "TEXTAREA" || tag === "INPUT") return;
    if (e.key === "j" || e.key === "ArrowDown") go(1);
    if (e.key === "k" || e.key === "ArrowUp") go(-1);
  }, !!drawer);

  if (!drawer) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/55 backdrop-blur-[2px]" onClick={closeFinding} />
      <aside className="slide-in glass-strong relative flex h-full w-[min(760px,94vw)] flex-col">
        <div className="flex items-center justify-between border-b border-line px-6 py-3.5">
          <div className="flex items-center gap-2 text-[12.5px] text-ink-3">
            <button onClick={() => go(-1)} disabled={idx <= 0} className="rounded p-1 hover:bg-raised disabled:opacity-30" title="Previous (k)"><ChevronLeft size={16} /></button>
            <span className="font-mono">{idx + 1} / {drawer.ids.length}</span>
            <button onClick={() => go(1)} disabled={idx >= drawer.ids.length - 1} className="rounded p-1 hover:bg-raised disabled:opacity-30" title="Next (j)"><ChevronRight size={16} /></button>
            <span className="ml-2 hidden sm:inline">j / k to move · A / R / Q to decide · Esc to close</span>
          </div>
          <div className="flex items-center gap-1">
            {f && <CopyJson f={f} />}
            <button onClick={closeFinding} className="rounded p-1.5 text-ink-3 hover:bg-raised hover:text-ink" aria-label="Close"><X size={17} /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!f ? (err ? <Notice tone="danger">{err}</Notice> : <Loading />) : (
            <div className="space-y-7">
              <div>
                <div className="flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
                  <span className="font-medium text-ink-2">{moduleNames[f.module]}</span>·<span className="font-mono">{f.check_id}</span>
                  <RequirementTag id={f.requirement} />
                  {f.assessment_name && <span className="truncate">· {f.assessment_name}</span>}
                </div>
                <h2 className="mt-2 text-[21px] font-semibold tracking-tight text-ink">{f.check_name}</h2>
                <p className="mt-1 text-[13px] text-ink-3">{f.check_description}</p>
              </div>

              {/* The five mandatory fields, prominently (R-GOV-1) */}
              <div className="grid grid-cols-4 gap-px overflow-hidden rounded-xl border border-line bg-line">
                <div className="bg-raised px-4 py-3">
                  <div className="label-caps">Recommended</div>
                  <div className="mt-2"><DispositionBadge value={f.recommended_disposition} unavailable={f.status === "UNAVAILABLE"} size="md" /></div>
                </div>
                <div className="bg-raised px-4 py-3">
                  <div className="label-caps">Effective</div>
                  <div className="mt-2"><DispositionBadge value={f.effective_disposition} size="md" /></div>
                </div>
                <div className="bg-raised px-4 py-3">
                  <div className="label-caps">Severity</div>
                  <div className="mt-2.5"><SeverityBadge value={f.severity} /></div>
                </div>
                <div className="bg-raised px-4 py-3">
                  <div className="label-caps">Confidence</div>
                  <div className="mt-2.5"><ConfidenceMeter value={f.confidence} width={56} /></div>
                </div>
              </div>

              <section>
                <div className="label-caps mb-2">Reason</div>
                <p className="text-[15px] leading-relaxed text-ink">{f.reason}</p>
              </section>

              <section>
                <div className="label-caps mb-2">Affected asset</div>
                <div className="flex items-center gap-3 rounded-lg border border-line bg-raised/50 px-4 py-3">
                  <span className="rounded bg-canvas px-2 py-0.5 text-[11px] uppercase tracking-wider text-ink-3">{f.affected_asset.type.replace("_", " ")}</span>
                  <span className="font-medium text-ink">{f.asset_label}</span>
                  <span className="ml-auto font-mono text-[11.5px] text-ink-3">{f.affected_asset.id}</span>
                </div>
              </section>

              <section>
                <div className="label-caps mb-3">Evidence</div>
                <Evidence f={f} />
              </section>

              {f.limitations.length > 0 && (
                <section>
                  <div className="label-caps mb-2">Limitations of this finding</div>
                  <ul className="space-y-1.5 text-[13px] text-ink-2">
                    {f.limitations.map((l) => <li key={l} className="flex gap-2"><span className="text-ink-3">—</span>{l}</li>)}
                  </ul>
                </section>
              )}

              <DecisionForm finding={f} onDone={(nf) => { setF(nf); bump(); }} />

              <section>
                <div className="label-caps mb-3">Decision history</div>
                {f.decisions && f.decisions.length > 0 ? (
                  <ol className="space-y-3">
                    {f.decisions.map((d, i) => (
                      <li key={d.id} className="relative border-l border-line pl-4">
                        <span className={cx("absolute -left-[4.5px] top-1.5 h-2 w-2 rounded-full", i === 0 ? "bg-brand" : "bg-line")} />
                        <div className="flex items-center gap-2 text-[12px] text-ink-3">
                          <DispositionBadge value={d.decision} /> {d.analyst_name} · {dateTime(d.decided_at)} {i === 0 && <span className="text-brand">· effective</span>}
                        </div>
                        <p className="mt-1.5 text-[13px] text-ink-2">{d.justification}</p>
                      </li>
                    ))}
                  </ol>
                ) : <p className="text-[13px] text-ink-3">No decision yet. {f.unresolved && "This finding blocks report finalisation until decided."}</p>}
              </section>
              <div className="pb-4 font-mono text-[11px] text-ink-3">{f.id} · created {dateTime(f.created_at)}</div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
