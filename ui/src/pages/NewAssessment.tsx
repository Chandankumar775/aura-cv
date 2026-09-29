import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Aperture, Check, CircleCheck, CircleDashed, Cpu, Database, Radio } from "lucide-react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Button, Card, cx, DigestText, Loading, Notice, PageHeader, RequirementTag } from "../components/ui";

interface AssetT { id: string; type: string; name: string; digest?: string; format?: string; detected_access_level?: string; has_contributor_metadata?: boolean; n_images?: number; n_records?: number; validation_summary?: any; supplier?: string }
interface Preview {
  access_level: string;
  detected_access_level: string | null;
  modules: { module: string; name: string; available: boolean; reason: string; checks: { check_id: string; name: string; will_run: boolean; reason: string; fallback_check_id: string | null }[] }[];
}

const SLOTS: { field: string; type: string; label: string; icon: React.ReactNode; hint: string }[] = [
  { field: "dataset_id", type: "dataset", label: "Training dataset", icon: <Database size={16} />, hint: "COCO, YOLO or image-folder, with optional contributor metadata" },
  { field: "model_id", type: "model", label: "Model", icon: <Cpu size={16} />, hint: "ONNX, TorchScript or weights-only state dict" },
  { field: "record_stream_id", type: "record_stream", label: "Inference records", icon: <Radio size={16} />, hint: "Signed JSONL record stream" },
  { field: "input_batch_id", type: "input_batch", label: "Operational input batch", icon: <Aperture size={16} />, hint: "New images from the field" },
  { field: "reference_id", type: "reference", label: "Declared reference", icon: <Aperture size={16} />, hint: "Intended operating distribution" },
];
const STEPS = ["Select inputs", "Scope & access", "Review & start"];

export default function NewAssessment() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const assets = useApi<{ items: AssetT[] }>("/assets");
  const [step, setStep] = useState(0);
  const [sel, setSel] = useState<Record<string, string>>({});
  const [modules, setModules] = useState<string[]>([]);
  const [override, setOverride] = useState<string>("");
  const [seed, setSeed] = useState(1337);
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const prevAvail = useRef<string[]>([]);

  useEffect(() => {
    const pre: Record<string, string> = {};
    SLOTS.forEach((s) => { const v = params.get(s.field); if (v) pre[s.field] = v; });
    if (Object.keys(pre).length) setSel(pre);
  }, []);

  const body = useMemo(() => ({ ...sel, access_level_override: override || null, seed }), [sel, override, seed]);
  useEffect(() => {
    api.post<Preview>("/assessments/preview", body).then((p) => {
      setPreview(p);
      const avail = p.modules.filter((m) => m.available).map((m) => m.module);
      const fresh = avail.filter((m) => !prevAvail.current.includes(m));
      prevAvail.current = avail;
      // Keep the user's choices, drop modules that lost their inputs, add ones that just became possible.
      setModules((ms) => [...ms.filter((m) => avail.includes(m)), ...fresh.filter((m) => !ms.includes(m))].sort());
    }).catch((e) => setErr(e.message));
  }, [JSON.stringify(body)]);

  useEffect(() => {
    const byId = Object.fromEntries((assets.data?.items ?? []).map((a) => [a.id, a]));
    const parts = [byId[sel.model_id]?.name?.split(" (")[0], byId[sel.dataset_id]?.name?.split(" (")[0], byId[sel.input_batch_id]?.name].filter(Boolean);
    if (!name || name.startsWith("Assessment · ")) setName(parts.length ? `Assessment · ${parts.join(" + ")}` : "");
  }, [sel, assets.data]);

  if (assets.loading) return <Loading />;
  const all = assets.data?.items ?? [];
  const model = all.find((a) => a.id === sel.model_id);

  const start = async () => {
    setBusy(true);
    setErr(null);
    try {
      const a = await api.post<{ id: string }>("/assessments", { ...body, name, modules });
      await api.post(`/assessments/${a.id}/start`);
      nav(`/assessments/${a.id}/run`);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader title="Assess contributed assets" sub="Select what to assess, set the scope and model access, review which checks will run, then start." />
      <ol className="mb-7 flex items-center gap-3">
        {STEPS.map((s, i) => (
          <li key={s} className="flex items-center gap-3">
            <button onClick={() => i < step && setStep(i)} className={cx("flex items-center gap-2.5 text-[13px]", i === step ? "text-ink" : i < step ? "text-ink-2 hover:text-ink" : "text-ink-3")}>
              <span className={cx("flex h-6 w-6 items-center justify-center rounded-full border text-[11.5px] font-semibold", i < step ? "border-accept/50 bg-accept/15 text-accept" : i === step ? "border-brand bg-brand/15 text-brand" : "border-line")}>
                {i < step ? <Check size={13} /> : i + 1}
              </span>{s}
            </button>
            {i < STEPS.length - 1 && <span className="h-px w-12 bg-line" />}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <div className="space-y-4">
          {SLOTS.map((slot) => {
            const opts = all.filter((a) => a.type === slot.type);
            const chosen = opts.find((o) => o.id === sel[slot.field]);
            return (
              <Card key={slot.field} className="!p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex w-[230px] items-center gap-3">
                    <span className="text-ink-3">{slot.icon}</span>
                    <div><div className="text-[13.5px] font-medium text-ink">{slot.label}</div><div className="text-[11.5px] text-ink-3">{slot.hint}</div></div>
                  </div>
                  <div className="flex flex-1 flex-wrap gap-2">
                    <button onClick={() => setSel((s) => { const n = { ...s }; delete n[slot.field]; return n; })}
                      className={cx("rounded-lg border px-3 py-2 text-[12.5px]", !chosen ? "border-brand/50 bg-brand/10 text-ink" : "border-line text-ink-3 hover:text-ink-2")}>None</button>
                    {opts.map((o) => (
                      <button key={o.id} onClick={() => setSel((s) => ({ ...s, [slot.field]: o.id }))}
                        className={cx("rounded-lg border px-3 py-2 text-left text-[12.5px] transition-colors", chosen?.id === o.id ? "border-brand/60 bg-brand/10 text-ink" : "border-line text-ink-2 hover:bg-raised")}>
                        <div className="font-medium">{o.name}</div>
                        <div className="text-[11px] text-ink-3">
                          {o.type === "dataset" && `${o.format?.toUpperCase()} · ${o.n_images?.toLocaleString("en-IN")} images · ${o.has_contributor_metadata ? "contributor metadata" : "no metadata"}`}
                          {o.type === "model" && `${o.format} · detected ${o.detected_access_level}`}
                          {o.type === "record_stream" && `${o.n_records} records`}
                          {(o.type === "input_batch" || o.type === "reference") && `${o.n_images?.toLocaleString("en-IN")} images`}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
                {chosen?.validation_summary && (
                  <div className="mt-3 flex flex-wrap gap-4 border-t border-line-soft pt-3 text-[12px] text-ink-3">
                    <span>Format detected <span className="text-ink-2">{chosen.validation_summary.format_detected}</span></span>
                    <span>Contributors <span className="text-ink-2">{chosen.validation_summary.contributors}</span></span>
                    <span>Sanity issues <span className={chosen.validation_summary.sanity_issues ? "text-review" : "text-ink-2"}>{chosen.validation_summary.sanity_issues}</span></span>
                    <DigestText value={chosen.digest} />
                  </div>
                )}
              </Card>
            );
          })}
          <div className="flex justify-end"><Button variant="primary" disabled={!Object.keys(sel).length} onClick={() => setStep(1)}>Continue</Button></div>
        </div>
      )}

      {step === 1 && preview && (
        <div className="space-y-5">
          <Card>
            <div className="label-caps mb-3">Modules</div>
            <div className="grid gap-3 md:grid-cols-2">
              {preview.modules.map((m) => {
                const on = modules.includes(m.module);
                return (
                  <button key={m.module} disabled={!m.available} onClick={() => setModules((ms) => on ? ms.filter((x) => x !== m.module) : [...ms, m.module])}
                    className={cx("flex items-start gap-3 rounded-lg border p-3.5 text-left transition-colors disabled:cursor-not-allowed",
                      !m.available ? "border-dashed border-line opacity-60" : on ? "border-brand/50 bg-brand/[0.07]" : "border-line hover:bg-raised")}>
                    <span className={cx("mt-0.5 flex h-4 w-4 items-center justify-center rounded border", on ? "border-brand bg-brand text-canvas" : "border-ink-3")}>{on && <Check size={11} strokeWidth={3} />}</span>
                    <div>
                      <div className="text-[13.5px] font-medium text-ink"><span className="font-mono text-[11px] text-ink-3">{m.module}</span> {m.name}</div>
                      <div className="mt-0.5 text-[12px] text-ink-3">{m.available ? `${m.checks.length} checks` : m.reason}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
          {model && (
            <Card>
              <div className="label-caps mb-1">Model access</div>
              <p className="mb-3 text-[12.5px] text-ink-3">Detected from the model file: <span className="font-mono text-ink">{model.detected_access_level}</span>. You may declare a lower level to simulate black-box conditions; checks that need more access will be reported as UNAVAILABLE, never skipped silently.</p>
              <div className="flex flex-wrap gap-2">
                {["", "BB-S", "BB-L"].map((lvl) => {
                  const rank = { WB: 3, "BB-S": 2, "BB-L": 1 } as Record<string, number>;
                  const disabled = lvl !== "" && rank[lvl] > rank[model.detected_access_level ?? "BB-L"];
                  return (
                    <button key={lvl} disabled={disabled} onClick={() => setOverride(lvl)}
                      className={cx("rounded-lg border px-3.5 py-2 text-[12.5px] disabled:opacity-40", override === lvl ? "border-brand/60 bg-brand/10 text-ink" : "border-line text-ink-2 hover:bg-raised")}>
                      {lvl === "" ? `As detected (${model.detected_access_level})` : lvl === "BB-S" ? "Black-box · scores (BB-S)" : "Black-box · labels (BB-L)"}
                    </button>
                  );
                })}
              </div>
            </Card>
          )}
          <Card>
            <div className="grid gap-4 md:grid-cols-[1fr_160px]">
              <label><span className="label-caps">Assessment name</span>
                <input value={name} onChange={(e) => setName(e.target.value)} className="mt-2 h-10 w-full rounded-lg border border-line bg-canvas px-3 text-[13.5px] text-ink focus:border-brand/60 focus:outline-none" /></label>
              <label><span className="label-caps">Seed</span>
                <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="mt-2 h-10 w-full rounded-lg border border-line bg-canvas px-3 font-mono text-[13.5px] text-ink focus:border-brand/60 focus:outline-none" /></label>
            </div>
          </Card>
          <div className="flex justify-between"><Button onClick={() => setStep(0)}>Back</Button><Button variant="primary" disabled={!modules.length || !name.trim()} onClick={() => setStep(2)}>Review</Button></div>
        </div>
      )}

      {step === 2 && preview && (
        <div className="space-y-5">
          <Notice tone="info">Access level for this run: <span className="font-mono text-ink">{preview.access_level}</span>. The plan below comes from the scheduler — every check that cannot run is listed with its reason and fallback.</Notice>
          <div className="grid gap-4 xl:grid-cols-2">
            {preview.modules.filter((m) => modules.includes(m.module)).map((m) => (
              <Card key={m.module} className="!p-4">
                <div className="mb-3 flex items-center justify-between"><div className="text-[14px] font-medium text-ink"><span className="font-mono text-[11px] text-ink-3">{m.module}</span> {m.name}</div>
                  <span className="text-[12px] text-ink-3">{m.checks.filter((c) => c.will_run).length} run · {m.checks.filter((c) => !c.will_run).length} unavailable</span></div>
                <div className="space-y-1">
                  {m.checks.map((c) => (
                    <div key={c.check_id} className={cx("flex items-start gap-2.5 rounded-md px-2 py-1.5 text-[12.5px]", !c.will_run && "bg-raised/60")}>
                      {c.will_run ? <CircleCheck size={14} className="mt-0.5 text-accept/80" /> : <CircleDashed size={14} className="mt-0.5 text-gap" />}
                      <div className="flex-1"><span className={c.will_run ? "text-ink" : "text-ink-2"}>{c.name}</span>
                        {!c.will_run && <div className="text-[11.5px] text-gap">UNAVAILABLE — {c.reason}{c.fallback_check_id && ` · fallback ${c.fallback_check_id}`}</div>}</div>
                      <span className="font-mono text-[10.5px] text-ink-3">{c.check_id}</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
          {err && <Notice tone="danger">{err}</Notice>}
          <div className="flex justify-between"><Button onClick={() => setStep(1)}>Back</Button><Button variant="primary" onClick={start} disabled={busy}>{busy ? "Starting…" : "Start assessment"}</Button></div>
        </div>
      )}
    </div>
  );
}

export { RequirementTag };
