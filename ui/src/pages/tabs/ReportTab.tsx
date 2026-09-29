import { useEffect, useState } from "react";
import { Download, FileCheck2, FilePlus2, Lock, Printer } from "lucide-react";
import type { Assessment } from "../../lib/api";
import { api, ApiError } from "../../lib/api";
import { useApp } from "../../lib/app";
import { dateTime, moduleNames } from "../../lib/format";
import { Button, Card, DigestText, DispositionBadge, EmptyState, KeyValue, Loading, Notice, SectionTitle, StatusPill } from "../../components/ui";

export interface ReportDoc {
  id: string; assessment_id: string; status: string; created_at: string; created_by_name?: string; report_digest: string; key_id: string; audit_head_hash: string;
  overall_disposition?: string; unresolved?: number; json: any; assessment_name?: string;
}

export function ReportPreview({ r }: { r: any }) {
  const mods = r.modules;
  const order: [string, string][] = [["data_integrity", "M1"], ["model_integrity", "M2"], ["inference_provenance", "M3"], ["distribution_shift", "M4"]];
  return (
    <article className="rounded-xl border border-line bg-[#0b0f15] p-8 text-[13.5px] leading-relaxed">
      {r.demo && <div className="mb-6 rounded border border-review/40 bg-review/10 px-3 py-2 text-[12px] font-medium text-review">{r.demo_notice}</div>}
      <div className="flex items-start justify-between gap-6 border-b border-line pb-5">
        <div>
          <div className="label-caps">AURA-CV Assurance Report · {r.status}</div>
          <h2 className="mt-1.5 text-[22px] font-semibold text-ink">{r.assessment.name}</h2>
          <div className="mt-1 text-ink-3">Generated {dateTime(r.generated_at)} · {r.tool.name} {r.tool.version} · schema {r.schema_version}</div>
        </div>
        <div className="text-right"><div className="label-caps mb-1.5">Overall</div><DispositionBadge value={r.summary.overall_disposition} size="lg" /></div>
      </div>

      <section className="mt-6">
        <h3 className="label-caps mb-3">Recommended actions</h3>
        <ol className="list-decimal space-y-1.5 pl-5 text-ink">{r.recommended_actions.map((a: string) => <li key={a}>{a}</li>)}</ol>
      </section>

      <section className="mt-7">
        <h3 className="label-caps mb-3">Asset verdicts</h3>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          {r.summary.asset_verdicts.map((t: any) => (
            <div key={t.key} className="rounded-lg border border-line p-3">
              <div className="text-[12px] text-ink-3">{t.label}</div>
              <div className="mt-2"><DispositionBadge value={t.disposition} /></div>
              <div className="mt-1.5 font-mono text-[11px] text-ink-3">conf {t.confidence?.toFixed(2) ?? "—"} · {t.findings} findings{t.coverage_gaps?.length ? ` · ${t.coverage_gaps.length} gap(s)` : ""}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-7">
        <h3 className="label-caps mb-3">Assessment context</h3>
        <KeyValue items={[
          ["Offline", r.assessment_context.offline ? "yes — no network access during assessment" : "no"],
          ["Model access level", <span className="font-mono">{r.assessment_context.model_access_level}</span>],
          ["Checks run", `${r.assessment_context.checks_run.length}`],
          ["Checks unavailable", r.assessment_context.checks_unavailable.length ? r.assessment_context.checks_unavailable.map((c: any) => `${c.check_id} (${c.reason}${c.fallback_used ? `; fallback ${c.fallback_used}` : ""})`).join("; ") : "none"],
          ["Inputs", r.inputs.map((i: any) => i.name).join(" · ")],
        ]} />
      </section>

      {order.map(([k, m]) => mods[k].status !== "NOT_RUN" && (
        <section key={k} className="mt-7">
          <h3 className="label-caps mb-3">{m} · {moduleNames[m]} · {mods[k].status}</h3>
          {k === "model_integrity" && <p className="mb-2 text-ink-2">Access {mods[k].access_level}; confidence {mods[k].confidence}. Limitations: {mods[k].limitations.join(" ")}</p>}
          {k === "distribution_shift" && <p className="mb-2 text-ink-2">{mods[k].characterisation} Calibrated risk {mods[k].calibrated_risk} (ECE {mods[k].calibration_quality?.ece}).</p>}
          {k === "inference_provenance" && <p className="mb-2 text-ink-2">{mods[k].records_total} records: {Object.entries(mods[k].status_counts ?? {}).map(([s, n]) => `${s} ${n}`).join(", ")}.</p>}
          <table className="w-full text-[12.5px]">
            <tbody>
              {mods[k].findings.slice(0, 12).map((f: any) => (
                <tr key={f.id} className="border-t border-line-soft align-top">
                  <td className="w-28 py-2 pr-3"><DispositionBadge value={f.effective_disposition} unavailable={f.status === "UNAVAILABLE"} /></td>
                  <td className="py-2 pr-3 text-ink-2"><span className="font-medium text-ink">{f.check_name}.</span> {f.reason}</td>
                  <td className="w-20 py-2 text-right font-mono text-ink-3">{f.severity} {f.confidence.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {mods[k].findings.length > 12 && <div className="mt-1 text-[12px] text-ink-3">+ {mods[k].findings.length - 12} more in the signed JSON.</div>}
        </section>
      ))}

      <section className="mt-7">
        <h3 className="label-caps mb-3">Analyst decisions</h3>
        <p className="text-ink-2">{mods.governance.analyst_decisions.length} decisions recorded, each with justification, in the audit log.</p>
      </section>

      <section className="mt-7 grid gap-5 md:grid-cols-2">
        {([["Not supported", "unsupported"], ["Partially supported", "partial"], ["Assumptions", "assumptions"], ["Known limitations", "known_limitations"]] as const).map(([t, key]) => (
          <div key={key}>
            <h3 className="label-caps mb-2">{t}</h3>
            <ul className="space-y-1 text-[12.5px] text-ink-2">{r.coverage_statement[key].map((x: string) => <li key={x}>— {x}</li>)}</ul>
          </div>
        ))}
      </section>

      <footer className="mt-8 space-y-1 border-t border-line pt-4 font-mono text-[11px] text-ink-3">
        <div>audit head {r.audit.log_head_hash} · {r.audit.entry_count} entries · chain {r.audit.chain_verified ? "verified" : "NOT verified"}</div>
        <div>signature {r.signature.algorithm} · key {r.signature.key_id}</div>
      </footer>
    </article>
  );
}

export default function ReportTab({ asm }: { asm: Assessment }) {
  const { bump, toast } = useApp();
  const [rep, setRep] = useState<ReportDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<any[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [check, setCheck] = useState<{ valid: boolean; checks: { step: string; passed: boolean | null }[] } | null>(null);
  useEffect(() => { if (rep) api.post<any>("/reports/verify", rep.json).then(setCheck).catch(() => setCheck(null)); }, [rep?.report_digest]);

  const load = async (rid?: string) => {
    setLoading(true);
    const id = rid ?? asm.report?.id;
    setRep(id ? await api.get<ReportDoc>(`/reports/${id}`) : null);
    setLoading(false);
  };
  useEffect(() => { load(); }, [asm.id]);

  const generate = async () => {
    setBusy(true);
    const r = await api.post<ReportDoc>(`/assessments/${asm.id}/reports`);
    await load(r.id);
    setBlocked(null);
    setBusy(false);
    bump();
    toast({ tone: "info", title: "Draft report generated", detail: "Signed with the local report key; its audit head hash is embedded." });
  };
  const finalise = async () => {
    if (!rep) return;
    setBusy(true);
    try {
      await api.post(`/reports/${rep.id}/finalise`);
      await load(rep.id);
      setBlocked(null);
      setMsg("Report finalised. It is now immutable and its signature covers the FINAL status.");
      toast({ tone: "ok", title: "Report finalised", detail: "FINAL and immutable. Download the signed JSON for submission." });
      bump();
    } catch (e) {
      const err = e as ApiError;
      setBlocked((err.details?.unresolved as any[]) ?? []);
      toast({ tone: "warn", title: "Finalisation blocked", detail: err.message });
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Loading />;
  if (!rep) {
    return <EmptyState title="No report yet" icon={<FilePlus2 size={22} />} action={<Button variant="primary" onClick={generate} disabled={busy}>Generate draft report</Button>}>
      A draft can be generated at any time. It becomes FINAL only once every REVIEW or QUARANTINE finding has an analyst decision.
    </EmptyState>;
  }
  const unresolved = asm.summary?.unresolved ?? 0;
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
      <div className="min-w-0"><ReportPreview r={rep.json} /></div>
      <div className="space-y-4">
        <Card>
          <div className="flex items-center justify-between"><div className="label-caps">Report</div><StatusPill status={rep.status} /></div>
          <div className="mt-2 font-mono text-[12px] text-ink-2">{rep.id}</div>
          <div className="mt-4 space-y-2 text-[12.5px]">
            <div className="flex justify-between"><span className="text-ink-3">Created</span><span>{dateTime(rep.created_at)}</span></div>
            <div className="flex justify-between"><span className="text-ink-3">Digest</span><DigestText value={rep.report_digest} n={8} /></div>
            <div className="flex justify-between"><span className="text-ink-3">Signing key</span><span className="font-mono text-[11.5px]">{rep.key_id}</span></div>
            <div className="flex justify-between"><span className="text-ink-3">Audit head</span><DigestText value={rep.audit_head_hash} n={8} /></div>
            {check?.checks.map((c) => (
              <div key={c.step} className="flex justify-between gap-2"><span className="text-ink-3">{c.step}</span><span className={c.passed ? "text-accept" : c.passed === false ? "text-quarantine" : "text-gap"}>{c.passed ? "pass" : c.passed === false ? "fail" : "n/a"}</span></div>
            ))}
          </div>
          <div className="mt-5 grid gap-2">
            {rep.status === "DRAFT" && (
              <>
                <Button variant="primary" icon={<Lock size={14} />} onClick={finalise} disabled={busy || unresolved > 0}>Finalise report</Button>
                {unresolved > 0 && <p className="text-[12px] text-review">{unresolved} findings still need a decision before this report can be finalised.</p>}
                <Button icon={<FilePlus2 size={14} />} onClick={generate} disabled={busy}>Regenerate draft</Button>
              </>
            )}
            <a href={`/api/v1/reports/${rep.id}/json`} className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-line bg-raised text-[13px] text-ink hover:bg-hover"><Download size={14} /> Signed JSON</a>
            <Button icon={<Printer size={14} />} onClick={() => window.print()}>Print / save as PDF</Button>
          </div>
        </Card>
        {msg && <Notice tone="ok" icon={<FileCheck2 size={16} className="text-accept" />}>{msg}</Notice>}
        {blocked && (
          <Card>
            <SectionTitle title="Finalisation blocked" hint="Decide these first:" />
            <ul className="space-y-1.5 text-[12.5px] text-ink-2">{blocked.map((b) => <li key={b.id}>· {b.check_name} — {b.asset_label}</li>)}</ul>
          </Card>
        )}
      </div>
    </div>
  );
}
