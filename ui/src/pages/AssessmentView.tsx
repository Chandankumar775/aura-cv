import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { Assessment, Finding } from "../lib/api";
import { useApp } from "../lib/app";
import { useApi } from "../lib/hooks";
import { dateTime } from "../lib/format";
import { EmptyState, ErrorState, Loading, PageHeader, StatusPill, Tabs } from "../components/ui";
import FindingsTable from "../components/FindingsTable";
import Overview from "./tabs/Overview";
import DataTab from "./tabs/DataTab";
import ModelTab from "./tabs/ModelTab";
import ProvenanceTab from "./tabs/ProvenanceTab";
import ShiftTab from "./tabs/ShiftTab";
import ReportTab from "./tabs/ReportTab";

type TabId = "overview" | "data" | "model" | "provenance" | "shift" | "findings" | "report";

export default function AssessmentView() {
  const { id = "", tab = "overview" } = useParams();
  const nav = useNavigate();
  const { version } = useApp();
  const asm = useApi<Assessment>(`/assessments/${id}`);
  const findings = useApi<{ items: Finding[] }>(`/assessments/${id}/findings`);
  useEffect(() => { if (version) { asm.reload(); findings.reload(); } }, [version]);

  if (asm.loading) return <Loading />;
  if (asm.error?.status === 404) {
    return <EmptyState title="This assessment is no longer on the server" action={<Link to="/assessments" className="text-brand hover:underline">Back to assessments</Link>}>
      The hosted demo keeps its data in temporary storage, which resets when the server instance restarts. The seeded assessments are always available; re-run your own from New assessment.
    </EmptyState>;
  }
  if (asm.error || !asm.data) return <ErrorState error={asm.error} onRetry={asm.reload} />;
  const a = asm.data;
  if (a.status === "RUNNING" || a.status === "QUEUED") {
    nav(`/assessments/${id}/run`, { replace: true });
    return null;
  }
  const byModule = a.summary?.counts.by_module ?? {};
  const has = (m: string) => a.modules.includes(m);
  const count = (m: string) => byModule[m] ? <span className="rounded bg-raised px-1.5 font-mono text-[10.5px] text-ink-3">{byModule[m]}</span> : null;
  const tabs: { id: TabId; label: string; badge?: React.ReactNode }[] = [
    { id: "overview", label: "Overview" },
    ...(has("M1") ? [{ id: "data" as TabId, label: "Data", badge: count("M1") }] : []),
    ...(has("M2") ? [{ id: "model" as TabId, label: "Model", badge: count("M2") }] : []),
    ...(has("M3") ? [{ id: "provenance" as TabId, label: "Provenance", badge: count("M3") }] : []),
    ...(has("M4") ? [{ id: "shift" as TabId, label: "Shift", badge: count("M4") }] : []),
    { id: "findings", label: "Findings", badge: a.summary ? <span className="rounded bg-raised px-1.5 font-mono text-[10.5px] text-ink-3">{a.summary.counts.total}</span> : null },
    { id: "report", label: "Report" },
  ];
  const t = tab as TabId;

  return (
    <div>
      <div className="mb-3 flex items-center gap-1.5 text-[12.5px] text-ink-3">
        <Link to="/assessments" className="hover:text-ink-2">Assessments</Link><ChevronRight size={13} /><span className="truncate text-ink-2">{a.name}</span>
      </div>
      <PageHeader title={a.name}
        sub={<span className="flex flex-wrap items-center gap-x-3 gap-y-1"><StatusPill status={a.status} /> <span>Run by {a.created_by_name}</span><span>·</span><span>{dateTime(a.finished_at)}</span><span>·</span><span>Access <span className="font-mono text-ink">{a.access_level_used}</span>{a.access_level_override && " (declared lower)"}</span><span>·</span><span>Seed <span className="font-mono">{a.seed}</span></span></span>} />
      <Tabs tabs={tabs} value={t} onChange={(x) => nav(`/assessments/${id}/${x}`)} />
      {a.status === "FAILED" && <ErrorState error={{ message: a.error ?? "Assessment failed" }} />}
      {t === "overview" && <Overview asm={a} findings={findings.data?.items ?? []} />}
      {t === "data" && <DataTab asm={a} findings={findings.data?.items ?? []} />}
      {t === "model" && <ModelTab asm={a} findings={findings.data?.items ?? []} />}
      {t === "provenance" && <ProvenanceTab asm={a} findings={findings.data?.items ?? []} />}
      {t === "shift" && <ShiftTab asm={a} findings={findings.data?.items ?? []} />}
      {t === "findings" && (findings.data ? <FindingsTable items={findings.data.items} /> : <Loading />)}
      {t === "report" && <ReportTab asm={a} />}
      <div className="mt-10 border-t border-line pt-4 text-[12px] text-ink-3">
        What this assessment cannot detect is stated in the <Link to="/coverage" className="text-brand hover:underline">coverage statement</Link>, embedded in every report.
      </div>
    </div>
  );
}
