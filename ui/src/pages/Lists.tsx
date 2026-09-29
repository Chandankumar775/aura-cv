import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CirclePlus, Download, FileCheck2, Link2, Search, ShieldCheck, TriangleAlert, Upload } from "lucide-react";
import type { AssessmentRow, Finding } from "../lib/api";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { useApi } from "../lib/hooks";
import { dateTime, relTime, shortDigest } from "../lib/format";
import { AssessmentTable } from "../components/assessment";
import FindingsTable from "../components/FindingsTable";
import { Button, Card, cx, DigestText, DispositionBadge, ErrorState, Loading, Notice, PageHeader, SectionTitle, StatusPill, VerificationChecklist } from "../components/ui";
import { ReportPreview, type ReportDoc } from "./tabs/ReportTab";

export function Assessments() {
  const nav = useNavigate();
  const { data, loading, error, reload } = useApi<{ items: AssessmentRow[] }>("/assessments");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div>
      <PageHeader title="All assessments" sub="Each assessment pins its inputs by digest and its configuration by snapshot, so it can be reproduced."
        right={<Button variant="primary" icon={<CirclePlus size={15} />} onClick={() => nav("/assessments/new")}>New assessment</Button>} />
      <AssessmentTable rows={data.items} />
    </div>
  );
}

export function Findings() {
  const { version } = useApp();
  const [params] = useSearchParams();
  const { data, loading, error, reload } = useApi<{ items: Finding[] }>("/findings");
  useEffect(() => { if (version) reload(); }, [version]);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div>
      <PageHeader title="Findings across all assessments"
        sub="Every flag carries a reason, evidence, confidence and severity, the affected asset and a recommended disposition. Unavailable checks are listed too." />
      <FindingsTable items={data.items} showAssessment initialUnresolved={params.get("unresolved") === "1"} />
    </div>
  );
}

function VerifyReportTool() {
  const [res, setRes] = useState<{ valid: boolean; checks: any[] } | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const onFile = async (f: File) => {
    setName(f.name);
    setErr(null);
    try {
      setRes(await api.post("/reports/verify", JSON.parse(await f.text())));
    } catch (e) {
      setErr(`Could not read this file as a report: ${(e as Error).message}`);
      setRes(null);
    }
  };
  return (
    <Card>
      <SectionTitle title="Verify a report" icon={<FileCheck2 size={16} className="text-ink-3" />} hint="Upload a signed JSON report: schema, signature, signing key and audit head are checked locally." />
      <input ref={input} type="file" accept=".json,application/json" className="hidden" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
      <Button icon={<Upload size={14} />} onClick={() => input.current?.click()}>Choose report JSON…</Button>
      {name && <div className="mt-3 font-mono text-[12px] text-ink-3">{name}</div>}
      {err && <div className="mt-3"><Notice tone="danger">{err}</Notice></div>}
      {res && (
        <div className="mt-4 space-y-3">
          <Notice tone={res.valid ? "ok" : "danger"}>{res.valid ? "Report is authentic: signature valid under a registered report key, and its audit head is present in this log." : "Report failed verification — see the failing step below."}</Notice>
          <VerificationChecklist steps={res.checks} />
        </div>
      )}
    </Card>
  );
}

export function Reports() {
  const { data, loading, error, reload } = useApi<{ items: ReportDoc[] }>("/reports");
  const [open, setOpen] = useState<ReportDoc | null>(null);
  const nav = useNavigate();
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div>
      <PageHeader title="Assurance reports" sub="Signed with the local report key. DRAFT until every REVIEW / QUARANTINE finding is decided; FINAL reports are immutable." />
      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card pad={false}>
          <table className="w-full text-[13px]">
            <thead><tr className="border-b border-line bg-raised/40 text-left">{["Report", "Assessment", "Overall", "Status", "Digest", ""].map((h) => <th key={h} className="label-caps px-4 py-2.5">{h}</th>)}</tr></thead>
            <tbody>
              {data.items.map((r) => (
                <tr key={r.id} className="border-b border-line-soft last:border-0 hover:bg-hover">
                  <td className="px-4 py-3"><div className="font-mono text-[12px] text-ink">{r.id}</div><div className="text-[11.5px] text-ink-3">{r.created_by_name} · {relTime(r.created_at)}</div></td>
                  <td className="max-w-[260px] truncate px-4 py-3 text-ink-2">{r.assessment_name}</td>
                  <td className="px-4 py-3"><DispositionBadge value={r.overall_disposition as any} /></td>
                  <td className="px-4 py-3"><StatusPill status={r.status} /></td>
                  <td className="px-4 py-3"><DigestText value={r.report_digest} n={8} /></td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1.5">
                      <Button size="sm" variant="ghost" onClick={async () => setOpen(await api.get<ReportDoc>(`/reports/${r.id}`))}>Preview</Button>
                      <Button size="sm" variant="ghost" onClick={() => nav(`/assessments/${r.assessment_id}/report`)}>Open</Button>
                      <a href={`/api/v1/reports/${r.id}/json`} className="inline-flex h-8 items-center rounded-lg px-2 text-ink-3 hover:bg-raised hover:text-ink" title="Download signed JSON"><Download size={14} /></a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <VerifyReportTool />
      </div>
      {open && <div className="mt-6"><ReportPreview r={open.json} /></div>}
    </div>
  );
}

interface AuditRow { index: number; timestamp: string; actor: { type: string; id: string }; actor_name: string; event: string; payload: Record<string, unknown>; entry_hash: string; prev_entry_hash: string; key_id: string }
interface VerifyRes { valid: boolean; entries_checked: number; head_hash: string; first_failure_index: number | null; failure_reason: string | null; verified_at: string }

const EVENTS = ["", "USER_LOGIN", "ASSET_REGISTERED", "ASSESSMENT_CREATED", "ASSESSMENT_STARTED", "CHECK_STARTED", "CHECK_COMPLETED", "CHECK_UNAVAILABLE", "FINDING_CREATED", "ANALYST_DECISION", "REPORT_GENERATED", "REPORT_FINALISED", "REPORT_EXPORTED", "KEY_CREATED", "ATTACK_SCENARIO_GENERATED"];

export function Audit() {
  const { refreshStatus, toast } = useApp();
  const [event, setEvent] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [ver, setVer] = useState<VerifyRes | null>(null);
  const [busy, setBusy] = useState(false);
  const qs = `/audit?page=${page}&page_size=40${event ? `&event=${event}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`;
  const { data, loading, error } = useApi<{ items: AuditRow[]; total: number; page: number; page_size: number }>(qs);
  const head = useApi<{ head_hash: string; entry_count: number }>("/audit/head");

  const verify = async () => {
    setBusy(true);
    const r = await api.post<VerifyRes>("/audit/verify");
    setVer(r);
    setBusy(false);
    refreshStatus();
    toast(r.valid ? { tone: "ok", title: "Audit chain valid", detail: `${r.entries_checked} entries recomputed from the first entry.` } : { tone: "danger", title: `Chain broken at entry ${r.first_failure_index}`, detail: r.failure_reason ?? undefined });
  };

  return (
    <div>
      <PageHeader title="Audit log"
        sub="Append-only, hash-chained and Ed25519-signed. Tamper-evident: any edit, deletion or reordering is detected on verification; truncation is detected against an exported head hash."
        right={<>
          <a href="/api/v1/audit/export" className="inline-flex h-9 items-center gap-2 rounded-lg border border-line bg-raised px-3.5 text-[13px] text-ink hover:bg-hover"><Download size={15} /> Export JSONL</a>
          <Button variant="primary" icon={<Link2 size={15} />} onClick={verify} disabled={busy}>{busy ? "Verifying chain…" : "Verify chain"}</Button>
        </>} />
      <div className="mb-6 grid gap-4 md:grid-cols-[1fr_2fr]">
        <Card className="!p-4">
          <div className="label-caps">Head</div>
          <div className="mt-1.5"><DigestText value={head.data?.head_hash} n={16} /></div>
          <div className="mt-1 text-[12px] text-ink-3">{head.data?.entry_count} entries</div>
        </Card>
        {ver ? (
          <div className={cx("fade-up flex items-center gap-4 rounded-xl border px-5 py-4", ver.valid ? "border-accept/35 bg-accept/[0.07]" : "border-quarantine/40 bg-quarantine/[0.08]")}>
            {ver.valid ? <ShieldCheck size={26} className="text-accept" /> : <TriangleAlert size={26} className="text-quarantine" />}
            <div>
              <div className="text-[15px] font-semibold text-ink">{ver.valid ? "Chain valid" : `Verification failed at entry ${ver.first_failure_index}`}</div>
              <div className="mt-0.5 text-[12.5px] text-ink-2">{ver.valid ? `${ver.entries_checked} entries: every hash link, payload digest and signature recomputed and confirmed.` : ver.failure_reason}</div>
              <div className="mt-0.5 text-[11.5px] text-ink-3">Verified {dateTime(ver.verified_at)}</div>
            </div>
          </div>
        ) : <div className="flex items-center rounded-xl border border-dashed border-line px-5 text-[13px] text-ink-3">Run "Verify chain" to recompute every hash and signature from the first entry.</div>}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="relative"><Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
          <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search payload or actor…" className="h-8 w-64 rounded-md border border-line bg-raised pl-8 pr-3 text-[12.5px] text-ink placeholder:text-ink-3 focus:outline-none" /></div>
        <select value={event} onChange={(e) => { setEvent(e.target.value); setPage(1); }} className="h-8 rounded-md border border-line bg-raised px-2 text-[12.5px] text-ink">
          {EVENTS.map((e) => <option key={e} value={e}>{e || "All events"}</option>)}
        </select>
        {data && <span className="ml-auto text-[12px] text-ink-3">{data.total} entries</span>}
      </div>
      {loading && !data ? <Loading /> : error ? <ErrorState error={error} /> : data && (
        <Card pad={false}>
          <table className="w-full text-[12.5px]">
            <thead><tr className="border-b border-line bg-raised/40 text-left">{["#", "Time", "Actor", "Event", "Payload", "Entry hash"].map((h) => <th key={h} className="label-caps px-3.5 py-2.5">{h}</th>)}</tr></thead>
            <tbody>
              {data.items.map((e) => (
                <tr key={e.index} className={cx("border-b border-line-soft last:border-0", ver && !ver.valid && ver.first_failure_index === e.index && "bg-quarantine/10")}>
                  <td className="px-3.5 py-2 font-mono text-ink-3">{e.index}</td>
                  <td className="whitespace-nowrap px-3.5 py-2 font-mono text-[11.5px] text-ink-2">{dateTime(e.timestamp)}</td>
                  <td className="px-3.5 py-2 text-ink-2">{e.actor.type === "system" ? <span className="text-ink-3">system</span> : e.actor_name}</td>
                  <td className="px-3.5 py-2"><span className="rounded bg-raised px-1.5 py-0.5 font-mono text-[10.5px] text-ink">{e.event}</span></td>
                  <td className="max-w-[420px] truncate px-3.5 py-2 font-mono text-[11px] text-ink-3" title={JSON.stringify(e.payload)}>{JSON.stringify(e.payload)}</td>
                  <td className="px-3.5 py-2 font-mono text-[11px] text-ink-3" title={e.entry_hash}>{shortDigest(e.entry_hash, 8)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-line px-4 py-2.5 text-[12px] text-ink-3">
            <span>Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))}</span>
            <div className="flex gap-2"><Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Newer</Button><Button size="sm" disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}>Older</Button></div>
          </div>
        </Card>
      )}
    </div>
  );
}
