import { useEffect, useState } from "react";
import { FlaskConical, RotateCcw } from "lucide-react";
import type { Assessment, Finding, VerificationStep } from "../../lib/api";
import { api } from "../../lib/api";
import { useApp } from "../../lib/app";
import { useApi } from "../../lib/hooks";
import { dateTime } from "../../lib/format";
import { Button, Card, cx, DigestText, ErrorState, KeyValue, Loading, Notice, SectionTitle, VerificationChecklist } from "../../components/ui";

interface Prov { stream: { id: string; name: string; stream_id: string; n_records: number; signer_key_ids: string[] }; status_counts: Record<string, number>; total: number; verified: number }
interface Row { position: number; sequence: number; timestamp: string; status: string; model_id: string; input_sha256: string; top_class: string; top_score: number }
interface Detail { position: number; record: any; status: string; steps: VerificationStep[]; explanation: string }

const TONE: Record<string, string> = { VERIFIED: "text-accept border-accept/30 bg-accept/8" };
const tone = (s: string) => TONE[s] ?? "text-quarantine border-quarantine/35 bg-quarantine/8";

function StatusTag({ s }: { s: string }) {
  return <span className={cx("inline-flex rounded border px-1.5 py-0.5 text-[10.5px] font-semibold tracking-wider", tone(s))}>{s.replace("_", " ")}</span>;
}

function TamperPanel({ detail }: { detail: Detail }) {
  const [cls, setCls] = useState<string>(detail.record.output?.top_k?.[0]?.class ?? "");
  const [res, setRes] = useState<{ status: string; steps: VerificationStep[]; explanation: string } | null>(null);
  useEffect(() => { setCls(detail.record.output?.top_k?.[0]?.class ?? ""); setRes(null); }, [detail.position]);
  const verify = async () => {
    const copy = JSON.parse(JSON.stringify(detail.record));
    if (copy.output?.top_k?.[0]) copy.output.top_k[0].class = cls;
    setRes(await api.post("/provenance/verify-record", { record: copy }));
  };
  const classes = ["truck", "apc", "tank", "civilian_car", "pickup"];
  return (
    <div className="rounded-xl border border-dashed border-review/40 bg-review/[0.04] p-4">
      <div className="flex items-center gap-2 text-[12.5px] font-semibold tracking-wide text-review"><FlaskConical size={14} /> TAMPER DEMO · local copy only</div>
      <p className="mt-1 text-[12.5px] text-ink-3">Change the predicted class in a local copy and re-verify the signature. The stored record is never modified.</p>
      <div className="mt-3 flex items-center gap-2">
        <select value={cls} onChange={(e) => setCls(e.target.value)} className="h-8 rounded-md border border-line bg-raised px-2 text-[12.5px] text-ink">
          {classes.map((c) => <option key={c}>{c}</option>)}
        </select>
        <Button size="sm" variant="primary" onClick={verify}>Re-verify copy</Button>
        {res && <Button size="sm" variant="ghost" icon={<RotateCcw size={13} />} onClick={() => { setCls(detail.record.output.top_k[0].class); setRes(null); }}>Reset</Button>}
      </div>
      {res && (
        <div className="mt-3 flex items-start gap-3 rounded-lg border border-line bg-panel p-3">
          <StatusTag s={res.status} />
          <div className="text-[12.5px] text-ink-2">{res.explanation}<div className="mt-1 text-ink-3">{res.steps.find((s) => s.step.startsWith("2"))?.detail}</div></div>
        </div>
      )}
    </div>
  );
}

export default function ProvenanceTab({ asm }: { asm: Assessment; findings: Finding[] }) {
  const { openFinding } = useApp();
  const prov = useApi<Prov>(`/assessments/${asm.id}/provenance`);
  const [filter, setFilter] = useState<string>("FAILED");
  const rows = useApi<{ items: Row[] }>(`/assessments/${asm.id}/provenance/records`);
  const [sel, setSel] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);

  useEffect(() => {
    if (sel === null) return;
    api.get<Detail>(`/assessments/${asm.id}/provenance/records/${sel}`).then(setDetail);
  }, [sel]);
  useEffect(() => {
    const first = rows.data?.items.find((r) => r.status !== "VERIFIED");
    if (first && sel === null) setSel(first.position);
  }, [rows.data]);

  if (prov.loading || rows.loading) return <Loading />;
  if (prov.error || !prov.data) return <ErrorState error={prov.error} />;
  const p = prov.data;
  const list = (rows.data?.items ?? []).filter((r) => filter === "ALL" || (filter === "FAILED" ? r.status !== "VERIFIED" : r.status === filter));

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="label-caps">Record stream</div>
            <div className="mt-1 text-[16px] font-medium text-ink">{p.stream.name}</div>
            <div className="mt-0.5 font-mono text-[12px] text-ink-3">{p.stream.stream_id} · keys named in records: {p.stream.signer_key_ids.join(", ")}</div>
          </div>
          <div className="text-right">
            <div className="font-mono text-[28px] font-semibold text-ink">{p.verified}<span className="text-[16px] text-ink-3"> / {p.total}</span></div>
            <div className="text-[12px] text-ink-3">records verified (Ed25519 · RFC 8785 · hash chain)</div>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {[["FAILED", "All failures", p.total - p.verified], ["ALL", "All records", p.total], ...Object.entries(p.status_counts).map(([k, n]) => [k, k.replace("_", " "), n])].map(([k, label, n]) => (
            <button key={k as string} onClick={() => setFilter(k as string)}
              className={cx("flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[12px] transition-colors", filter === k ? "border-brand/50 bg-brand/10 text-ink" : "border-line text-ink-2 hover:bg-raised")}>
              <span className={cx("h-1.5 w-1.5 rounded-full", k === "VERIFIED" ? "bg-accept" : k === "ALL" ? "bg-ink-3" : "bg-quarantine")} />
              {label as string} <span className="font-mono text-ink-3">{n as number}</span>
            </button>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.1fr]">
        <Card pad={false}>
          <div className="max-h-[680px] overflow-y-auto">
            <table className="w-full text-[12.5px]">
              <thead className="sticky top-0 bg-[#0d131b]"><tr className="border-b border-line text-left">{["Pos", "Seq", "Timestamp", "Output", "Status"].map((h) => <th key={h} className="label-caps px-3.5 py-2.5">{h}</th>)}</tr></thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.position} onClick={() => setSel(r.position)} className={cx("cursor-pointer border-b border-line-soft hover:bg-hover", sel === r.position && "bg-raised")}>
                    <td className="px-3.5 py-2 font-mono text-ink-3">{r.position}</td>
                    <td className="px-3.5 py-2 font-mono text-ink">{r.sequence}</td>
                    <td className="px-3.5 py-2 font-mono text-[11.5px] text-ink-3">{r.timestamp ? new Date(r.timestamp).toLocaleTimeString("en-GB", { hour12: false }) : "—"}</td>
                    <td className="px-3.5 py-2 text-ink-2">{r.top_class} <span className="font-mono text-ink-3">{r.top_score?.toFixed(3)}</span></td>
                    <td className="px-3.5 py-2"><StatusTag s={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <div className="space-y-4">
          {!detail ? <Card><div className="text-[13px] text-ink-3">Select a record to see every verification step.</div></Card> : (
            <>
              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div><div className="label-caps">Record</div><div className="mt-1 text-[18px] font-semibold text-ink">Sequence {detail.record.sequence} <span className="font-mono text-[13px] text-ink-3">· position {detail.position}</span></div></div>
                  <StatusTag s={detail.status} />
                </div>
                <div className="mt-3"><Notice tone={detail.status === "VERIFIED" ? "ok" : "danger"}>{detail.explanation}</Notice></div>
                <div className="mt-4">
                  <KeyValue items={[
                    ["Stream", <span className="font-mono">{detail.record.stream_id}</span>],
                    ["Timestamp", dateTime(detail.record.timestamp)],
                    ["Nonce", <span className="font-mono text-[12px]">{detail.record.nonce}</span>],
                    ["Input image", <DigestText value={detail.record.input?.sha256} />],
                    ["Model", <span>{detail.record.model?.id} · <DigestText value={detail.record.model?.weight_digest} n={8} /></span>],
                    ["Config", <DigestText value={detail.record.config?.sha256} n={8} />],
                    ["Output", <span className="font-mono text-[12px]">{detail.record.output?.top_k?.map((t: any) => `${t.class} ${t.score}`).join(" · ")}</span>],
                    ["Prev hash", <DigestText value={detail.record.prev_record_hash} n={8} />],
                    ["Signer", <span className="font-mono text-[12px]">{detail.record.signer?.key_id} ({detail.record.signer?.algorithm})</span>],
                  ]} />
                </div>
              </Card>
              <Card>
                <SectionTitle title="Verification checklist" hint="Ten steps, each reported separately (R-INF-2)." />
                <VerificationChecklist steps={detail.steps} />
              </Card>
              <TamperPanel detail={detail} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
