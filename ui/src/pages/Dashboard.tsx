import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Aperture, CirclePlus, Cpu, Database, FlaskConical, Link2, Radio, FileCheck2 } from "lucide-react";
import type { Assessment, AssessmentRow, Finding } from "../lib/api";
import { useApp } from "../lib/app";
import { useApi } from "../lib/hooks";
import { pct, verdictText } from "../lib/format";
import { AssessmentTable, AttentionList, VerdictCard } from "../components/assessment";
import { Button, Card, cx, EmptyState, ErrorState, Loading, PageHeader, SectionTitle } from "../components/ui";

interface Dash {
  recent: AssessmentRow[];
  latest: null | {
    assessment: Assessment;
    attention: Finding[];
    attention_total: number;
    health: {
      data?: { worst: any; counts: Record<string, number>; flagged: number; images: number };
      model?: { access_level: string; digest_match: boolean; fingerprint: number; backdoor: any; unavailable: number };
      provenance?: { verified: number; total: number; failed: number; top_failure: string | null };
      shift?: { verdict: string; calibrated_risk: number; characterisation: string };
    };
  };
}

function Health({ icon, title, to, children, tone }: { icon: React.ReactNode; title: string; to: string; children: React.ReactNode; tone?: "q" | "r" | "a" }) {
  return (
    <Link to={to} className="glass glass-hover group flex flex-col rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[13px] font-medium text-ink-2">{icon}{title}</div>
        <span className={cx("h-2 w-2 rounded-full", tone === "q" ? "bg-quarantine" : tone === "r" ? "bg-review" : "bg-accept")} />
      </div>
      <div className="mt-4 flex-1">{children}</div>
    </Link>
  );
}

const BAR_LABELS: Record<string, string> = { trigger: "Trigger", systematic: "Systematic", duplicate: "Duplicate", flip: "Label flip", ood: "OOD", annotation: "Annotation" };

export default function Dashboard() {
  const { version, user } = useApp();
  const nav = useNavigate();
  const { data, error, loading, reload } = useApi<Dash>("/dashboard");
  useEffect(() => { if (version) reload(); }, [version]);

  if (loading) return <Loading label="Loading assurance overview" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;

  const L = data.latest;
  const header = (
    <PageHeader title="What needs your attention"
      sub={L ? <>Triage view of the most recent full assessment. Every verdict links to the evidence behind it.</> : "No assessments yet."}
      right={<>
        <Button icon={<Link2 size={15} />} onClick={() => nav("/audit")}>Verify audit chain</Button>
        <Button icon={<FileCheck2 size={15} />} onClick={() => nav("/reports")}>Verify a report</Button>
        {user?.role === "ADMIN" && <Button icon={<FlaskConical size={15} />} onClick={() => nav("/attack-lab")}>Attack Lab</Button>}
        <Button variant="primary" icon={<CirclePlus size={15} />} onClick={() => nav("/assessments/new")}>New assessment</Button>
      </>} />
  );

  if (!L || !L.assessment.summary) {
    return (
      <>
        {header}
        <EmptyState title="Run your first assessment" icon={<CirclePlus size={22} />} action={<Button variant="primary" onClick={() => nav("/assessments/new")}>New assessment</Button>}>
          Register a dataset, a model, an inference record stream and an input batch, then assess them together.
        </EmptyState>
      </>
    );
  }
  const asm = L.assessment;
  const h = L.health;
  const maxCount = Math.max(1, ...Object.values(h.data?.counts ?? {}));

  return (
    <div className="space-y-6">
      {header}
      <VerdictCard asm={asm} summary={asm.summary!} />

      <div className="grid items-start gap-6 xl:grid-cols-[1.75fr_1fr]">
      <Card className="min-w-0">
        <TriageProgress total={asm.summary!.counts.by_recommended_disposition.REVIEW + asm.summary!.counts.by_recommended_disposition.QUARANTINE} open={asm.summary!.unresolved} />
        <SectionTitle title="Needs attention" hint="Unresolved findings recommending REVIEW or QUARANTINE, most severe first, alternating modules."
          right={<Link to={`/assessments/${asm.id}/findings`} className="whitespace-nowrap text-[12.5px] text-brand hover:underline">All findings →</Link>} />
        <AttentionList items={L.attention} total={L.attention_total} unresolved={asm.summary!.unresolved} />
      </Card>

      <div className="grid content-start gap-4 md:grid-cols-2 xl:grid-cols-1">
        {h.data && (
          <Health icon={<Database size={15} />} title="Data integrity" to={`/assessments/${asm.id}/data`} tone={h.data.worst?.risk >= 70 ? "q" : h.data.worst?.risk >= 35 ? "r" : "a"}>
            {h.data.worst && (
              <>
                <div className="text-[12px] text-ink-3">Highest-risk contributor</div>
                <div className="mt-0.5 flex items-baseline justify-between gap-2">
                  <span className="truncate text-[14px] font-medium text-ink">{h.data.worst.name}</span>
                  <span className="font-mono text-[20px] font-semibold text-quarantine">{h.data.worst.risk.toFixed(1)}</span>
                </div>
              </>
            )}
            <div className="mt-4 space-y-1.5">
              {Object.entries(h.data.counts).filter(([, v]) => v > 0).map(([k, v]) => (
                <div key={k} className="grid grid-cols-[76px_1fr_32px] items-center gap-2 text-[11.5px]">
                  <span className="text-ink-3">{BAR_LABELS[k] ?? k}</span>
                  <span className="h-1 rounded-full bg-line"><span className="block h-full rounded-full bg-ink-3" style={{ width: `${(v / maxCount) * 100}%` }} /></span>
                  <span className="text-right font-mono text-ink-2">{v}</span>
                </div>
              ))}
            </div>
          </Health>
        )}
        {h.model && (
          <Health icon={<Cpu size={15} />} title="Model integrity" to={`/assessments/${asm.id}/model`} tone={h.model.backdoor || !h.model.digest_match ? "q" : "a"}>
            <div className="space-y-2.5 text-[12.5px]">
              <Row k="Access used" v={<span className="font-mono">{h.model.access_level}</span>} />
              <Row k="Weight digest" v={h.model.digest_match ? <span className="text-accept">matches registered</span> : <span className="text-quarantine">MISMATCH</span>} />
              <Row k="Fingerprint" v={<span className="font-mono">{pct(h.model.fingerprint)}</span>} />
              <Row k="Backdoor" v={h.model.backdoor ? <span className="text-quarantine">→ {h.model.backdoor.class} · index {h.model.backdoor.anomaly_index}</span> : <span className="text-accept">none found</span>} />
              <Row k="Unavailable checks" v={<span className={cx("font-mono", h.model.unavailable ? "text-gap" : "text-ink-2")}>{h.model.unavailable}</span>} />
            </div>
          </Health>
        )}
        {h.provenance && (
          <Health icon={<Radio size={15} />} title="Inference provenance" to={`/assessments/${asm.id}/provenance`} tone={h.provenance.failed ? "q" : "a"}>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[28px] font-semibold text-ink">{h.provenance.verified}</span>
              <span className="text-[12.5px] text-ink-3">of {h.provenance.total} records verified</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-quarantine/70">
              <div className="h-full bg-accept" style={{ width: `${(h.provenance.verified / h.provenance.total) * 100}%` }} />
            </div>
            <div className="mt-4 text-[12.5px] text-ink-2">
              <span className="font-mono text-quarantine">{h.provenance.failed}</span> failed verification
              {h.provenance.top_failure && <> · most common: <span className="text-ink">{h.provenance.top_failure.replace("_", " ").toLowerCase()}</span></>}
            </div>
          </Health>
        )}
        {h.shift && (
          <Health icon={<Aperture size={15} />} title="Distribution shift" to={`/assessments/${asm.id}/shift`} tone={h.shift.verdict === "SUSPICIOUS_MANIPULATION" ? "q" : "r"}>
            <div className="text-[14px] font-medium text-ink">{verdictText[h.shift.verdict]}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-mono text-[28px] font-semibold text-review">{h.shift.calibrated_risk.toFixed(2)}</span>
              <span className="text-[12px] text-ink-3">calibrated risk of operational harm</span>
            </div>
            <p className="mt-3 line-clamp-3 text-[12.5px] leading-relaxed text-ink-3">{h.shift.characterisation}</p>
          </Health>
        )}
      </div>

      </div>

      <Card>
        <SectionTitle title="Recent assessments" right={<Link to="/assessments" className="text-[12.5px] text-brand hover:underline">View all →</Link>} />
        <AssessmentTable rows={data.recent} />
      </Card>
    </div>
  );
}

function TriageProgress({ total, open }: { total: number; open: number }) {
  const done = Math.max(0, total - open);
  return (
    <div className="mb-5 flex items-center gap-4">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
        <div className="h-full rounded-full bg-gradient-to-r from-brand-deep to-brand transition-[width] duration-500 ease-out" style={{ width: `${total ? (done / total) * 100 : 100}%` }} />
      </div>
      <span className="whitespace-nowrap text-[12px] text-ink-3"><span className="font-mono text-ink">{done}</span> of <span className="font-mono">{total}</span> actionable findings decided</span>
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-3"><span className="text-ink-3">{k}</span><span className="text-right text-ink-2">{v}</span></div>;
}
