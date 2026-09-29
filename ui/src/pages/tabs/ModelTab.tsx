import { Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CircleCheck, CircleX, Eye, EyeOff, ShieldAlert } from "lucide-react";
import type { Assessment, CheckRunT, Finding } from "../../lib/api";
import { useApp } from "../../lib/app";
import { useApi } from "../../lib/hooks";
import { pct } from "../../lib/format";
import { Card, ConfidenceMeter, cx, DigestText, DispositionBadge, ErrorState, Loading, Notice, SectionTitle, UnavailableCard } from "../../components/ui";

interface ModelView {
  access_level: string;
  detected_access_level: string;
  access_banner: string;
  identity: { weight_digest: string; registered_digest: string; digest_match: boolean; structure_match: boolean | null; fingerprint_agreement: number; measured_accuracy: number; claimed_accuracy: number };
  battery: { version: string; digest: string; images: number };
  triggers: { class: string; class_index: number; anomaly_index: number; anomalous: boolean; mask_l1: number }[] | null;
  strip: { histogram: { bin: number; clean: number; patched: number }[]; threshold: number } | null;
  patch_probe: { patch: string; flip_rate: number; target: string }[] | null;
  confidence: number;
  limitations: string[];
  checks_run: CheckRunT[];
  checks_unavailable: CheckRunT[];
  model: { id: string; name: string; format: string; supplier: string; task: string };
}

export const tooltipStyle = { background: "#141a23", border: "1px solid #232c38", borderRadius: 8, fontSize: 12, color: "#e8edf4" };

function Check({ ok, label, detail }: { ok: boolean | null; label: string; detail: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-line bg-raised/40 px-4 py-3">
      {ok === null ? <EyeOff size={17} className="mt-0.5 text-gap" /> : ok ? <CircleCheck size={17} className="mt-0.5 text-accept" /> : <CircleX size={17} className="mt-0.5 text-quarantine" />}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2"><span className="text-[13px] font-medium text-ink">{label}</span>
          <span className={cx("text-[10.5px] font-semibold tracking-wider", ok === null ? "text-gap" : ok ? "text-accept" : "text-quarantine")}>{ok === null ? "NOT ASSESSED" : ok ? "MATCH" : "MISMATCH"}</span></div>
        <div className="mt-1 text-[12.5px] text-ink-3">{detail}</div>
      </div>
    </div>
  );
}

export default function ModelTab({ asm, findings }: { asm: Assessment; findings: Finding[] }) {
  const { openFinding } = useApp();
  const { data: v, error, loading } = useApi<ModelView>(`/assessments/${asm.id}/model`);
  if (loading) return <Loading />;
  if (error || !v) return <ErrorState error={error} />;
  const wb = v.access_level === "WB";
  const mf = findings.filter((f) => f.module === "M2" && f.status === "FLAGGED");

  return (
    <div className="space-y-6">
      <div className={cx("flex items-center gap-4 rounded-xl border px-5 py-4", wb ? "border-brand/30 bg-brand/[0.06]" : "border-review/35 bg-review/[0.07]")}>
        {wb ? <Eye size={20} className="text-brand" /> : <EyeOff size={20} className="text-review" />}
        <div className="flex-1">
          <div className="text-[14px] font-medium text-ink">{v.access_banner}</div>
          <div className="mt-0.5 text-[12.5px] text-ink-3">
            {v.model.name} · {v.model.format} · supplier {v.model.supplier} · detected access <span className="font-mono">{v.detected_access_level}</span>
            {v.access_level !== v.detected_access_level && <> · <span className="text-review">declared lower to simulate black-box conditions</span></>}
          </div>
        </div>
        <div className="text-right"><div className="label-caps">Assessment confidence</div><div className="mt-1"><ConfidenceMeter value={v.confidence} /></div></div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.3fr]">
        <Card>
          <SectionTitle title="Identity" hint="Is this the model that was registered?" />
          <div className="space-y-2.5">
            <Check ok={v.identity.digest_match} label="Weight digest" detail={<div className="space-y-0.5"><div>supplied <DigestText value={v.identity.weight_digest} /></div><div>registered <DigestText value={v.identity.registered_digest} /></div></div>} />
            <Check ok={v.identity.structure_match} label="Graph structure" detail={v.identity.structure_match === null ? "Needs white-box access to read the layer graph." : "Layer graph digest compared with registration."} />
            <Check ok={v.identity.fingerprint_agreement >= 0.98} label="Behavioural fingerprint" detail={<>Top-1 agreement on reference battery <span className="font-mono text-ink-2">{pct(v.identity.fingerprint_agreement)}</span> (expected ≥ 98%)</>} />
            <Check ok={v.identity.measured_accuracy >= v.identity.claimed_accuracy - 0.05} label="Reference accuracy" detail={<>Measured <span className="font-mono text-ink-2">{pct(v.identity.measured_accuracy)}</span> vs claimed <span className="font-mono text-ink-2">{pct(v.identity.claimed_accuracy)}</span></>} />
          </div>
          <div className="mt-4 text-[11.5px] text-ink-3">Battery {v.battery.version} · {v.battery.images} images · <DigestText value={v.battery.digest} n={8} /></div>
        </Card>

        <Card>
          <SectionTitle title="Backdoor search" icon={<ShieldAlert size={16} className="text-ink-3" />}
            hint={wb ? "Trigger reconstruction per target class. An anomaly index above 2.0 means one class is unusually easy to reach." : "White-box reconstruction unavailable — black-box probes shown instead."} />
          {v.triggers ? (
            <>
              <div className="h-[210px]">
                <ResponsiveContainer>
                  <BarChart data={v.triggers} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="class" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                    <ReferenceLine y={2} stroke="#e8ad3d" strokeDasharray="4 3" label={{ value: "threshold 2.0", fill: "#e8ad3d", fontSize: 10, position: "insideTopRight" }} />
                    <Bar dataKey="anomaly_index" name="Anomaly index" radius={[4, 4, 0, 0]}>
                      {v.triggers.map((t) => <Cell key={t.class} fill={t.anomalous ? "#ef5a5f" : "#3a4658"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid grid-cols-5 gap-2">
                {v.triggers.map((t) => (
                  <div key={t.class} className={cx("rounded-lg border p-1.5", t.anomalous ? "border-quarantine/60" : "border-line")}>
                    <img src={`/api/v1/images/trigger/${t.class_index}.png?anomalous=${t.anomalous}`} className="aspect-square w-full rounded bg-black" alt={`reconstructed trigger ${t.class}`} />
                    <div className="mt-1 truncate text-center text-[10.5px] text-ink-3">{t.class}</div>
                    <div className={cx("text-center font-mono text-[11px]", t.anomalous ? "text-quarantine" : "text-ink-2")}>{t.anomaly_index.toFixed(2)}</div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[11.5px] text-ink-3">Reconstructed trigger masks (illustrative rendering). A compact mask in one corner for 'civilian_car' matches contributor C's data patch.</p>
            </>
          ) : v.patch_probe ? (
            <div className="overflow-hidden rounded-lg border border-line">
              <table className="w-full text-[13px]">
                <thead><tr className="border-b border-line bg-raised/40 text-left">{["Probe patch", "Flip rate", "Target"].map((h) => <th key={h} className="label-caps px-4 py-2.5">{h}</th>)}</tr></thead>
                <tbody>{v.patch_probe.map((p) => (
                  <tr key={p.patch} className="border-b border-line-soft last:border-0">
                    <td className="px-4 py-2.5 text-ink">{p.patch}</td>
                    <td className="px-4 py-2.5"><div className="flex items-center gap-2"><div className="h-1.5 w-28 rounded-full bg-line"><div className={cx("h-full rounded-full", p.flip_rate > 0.3 ? "bg-quarantine" : "bg-ink-3")} style={{ width: `${p.flip_rate * 100}%` }} /></div><span className="font-mono text-[12px]">{pct(p.flip_rate)}</span></div></td>
                    <td className="px-4 py-2.5 font-mono text-ink-2">{p.target}</td>
                  </tr>))}</tbody>
              </table>
            </div>
          ) : <Notice tone="ok">No backdoor-like behaviour found by the checks available at this access level.</Notice>}
        </Card>
      </div>

      {v.strip && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card>
            <SectionTitle title="STRIP entropy" hint="Prediction entropy when clean images are superimposed. A spike near zero for patched inputs means the patch dominates." />
            <div className="h-[220px]">
              <ResponsiveContainer>
                <BarChart data={v.strip.histogram} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="bin" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="clean" name="Clean inputs" fill="#4d6a93" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="patched" name="Patched inputs" fill="#ef5a5f" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          {v.patch_probe && v.triggers && (
            <Card>
              <SectionTitle title="Patch probing" hint="Flip rate towards one class when patches are pasted onto clean battery images." />
              <div className="space-y-3">
                {v.patch_probe.map((p) => (
                  <div key={p.patch} className="grid grid-cols-[1fr_140px_56px] items-center gap-3 text-[12.5px]">
                    <span className="text-ink-2">{p.patch}</span>
                    <div className="h-1.5 rounded-full bg-line"><div className={cx("h-full rounded-full", p.flip_rate > 0.3 ? "bg-quarantine" : "bg-ink-3")} style={{ width: `${p.flip_rate * 100}%` }} /></div>
                    <span className="text-right font-mono">{pct(p.flip_rate)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {v.checks_unavailable.length > 0 && (
        <Card>
          <SectionTitle title="Checks unavailable at this access level" hint="Shown so the gap is never hidden (R-CON-5). Each also appears as an UNAVAILABLE finding." />
          <div className="grid gap-3 md:grid-cols-2">
            {v.checks_unavailable.map((c) => <UnavailableCard key={c.check_id} checkId={c.check_id} name={c.name} reason={c.message} fallback={c.fallback_used} requirement={c.requirement} />)}
          </div>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <SectionTitle title="Model findings" />
          <div className="space-y-2">
            {mf.length === 0 && <div className="text-[13px] text-ink-3">No model findings.</div>}
            {mf.map((f) => (
              <button key={f.id} onClick={() => openFinding(f.id, mf.map((x) => x.id))} className="flex w-full items-center gap-3 rounded-lg border border-line bg-raised/40 px-3.5 py-2.5 text-left hover:bg-hover">
                <DispositionBadge value={f.effective_disposition} />
                <div className="min-w-0 flex-1"><div className="text-[13px] text-ink">{f.check_name}</div><div className="truncate text-[11.5px] text-ink-3">{f.reason}</div></div>
                <ConfidenceMeter value={f.confidence} width={36} />
              </button>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle title="Limitations of this assessment" hint="Always shown (R-MOD-3)." />
          <ul className="space-y-2 text-[13px] text-ink-2">{v.limitations.map((l) => <li key={l} className="flex gap-2"><span className="text-ink-3">—</span>{l}</li>)}</ul>
          <div className="mt-4 text-[12px] text-ink-3">No check retrains or modifies the supplied model (R-CON-4).</div>
        </Card>
      </div>
    </div>
  );
}
