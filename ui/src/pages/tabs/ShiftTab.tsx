import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { CircleCheck, CircleMinus } from "lucide-react";
import type { Assessment, Finding } from "../../lib/api";
import { useApi } from "../../lib/hooks";
import { verdictText } from "../../lib/format";
import { Card, cx, ErrorState, KeyValue, Loading, SectionTitle, Thumb } from "../../components/ui";
import { tooltipStyle } from "./ModelTab";

interface ShiftView {
  shift_detected: boolean;
  verdict: string;
  verdict_confidence: number;
  calibrated_risk: number;
  calibration: { method: string; ece: number; extrapolated: boolean; reliability: [number, number][] };
  tests: { mmd2: number; p_value: number; permutations: number; novel_fraction: number };
  characterisation: string;
  factors: Record<string, number>;
  descriptors: { name: string; factor: string; effect_size: number }[];
  spectrum: { band: string; reference: number; observed: number }[];
  projection: { reference: [number, number][]; observed: [number, number][] };
  rules: { rule: string; supports: string; fired: boolean }[];
  novel_samples: string[];
  metadata: Record<string, string>;
}

const VTONE: Record<string, string> = {
  PROBABLE_OPERATIONAL_DRIFT: "text-review border-review/40 bg-review/10",
  SUSPICIOUS_MANIPULATION: "text-quarantine border-quarantine/40 bg-quarantine/10",
  INCONCLUSIVE: "text-gap border-gap/50 bg-gap/10",
  NO_MATERIAL_SHIFT: "text-accept border-accept/40 bg-accept/10",
};
const FACTOR_ORDER = ["illumination", "season", "sensor", "acquisition", "terrain"];

export default function ShiftTab({ asm }: { asm: Assessment; findings: Finding[] }) {
  const { data: v, error, loading } = useApi<ShiftView>(`/assessments/${asm.id}/shift`);
  if (loading) return <Loading />;
  if (error || !v) return <ErrorState error={error} />;
  const desc = [...v.descriptors].sort((a, b) => FACTOR_ORDER.indexOf(a.factor) - FACTOR_ORDER.indexOf(b.factor));
  const batch = asm.inputs_detail.find((i) => i.role === "input_batch");
  const ref = asm.inputs_detail.find((i) => i.role === "reference");
  const groups = ["PROBABLE_OPERATIONAL_DRIFT", "SUSPICIOUS_MANIPULATION", "INCONCLUSIVE"];

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <Card>
          <div className="label-caps">Verdict · {batch?.name} vs {ref?.name}</div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className={cx("rounded-lg border px-3 py-1.5 text-[15px] font-semibold", VTONE[v.verdict])}>{verdictText[v.verdict]}</span>
            <span className="text-[12.5px] text-ink-3">verdict confidence <span className="font-mono text-ink-2">{v.verdict_confidence.toFixed(2)}</span></span>
          </div>
          <p className="mt-4 text-[14px] leading-relaxed text-ink-2">{v.characterisation}</p>
          <p className="mt-3 text-[12px] text-ink-3">Plain-language summary generated from the top descriptors (template-based, not free text generation).</p>
        </Card>
        <Card>
          <div className="label-caps">Calibrated risk of operational harm</div>
          <div className="mt-2 flex items-end gap-3">
            <span className={cx("font-mono text-[46px] font-semibold leading-none", v.calibrated_risk > 0.75 ? "text-quarantine" : "text-review")}>{v.calibrated_risk.toFixed(2)}</span>
            <span className="pb-1 text-[12.5px] text-ink-3">probability the model degrades materially on this batch</span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-gradient-to-r from-accept/60 via-review/60 to-quarantine/70">
            <div className="relative h-full" style={{ width: `${v.calibrated_risk * 100}%` }}><span className="absolute -right-1 -top-1 h-4 w-2 rounded-sm bg-ink shadow" /></div>
          </div>
          <div className="mt-5">
            <KeyValue items={[
              ["Calibration", `${v.calibration.method} · ECE ${v.calibration.ece.toFixed(3)} on held-out scenarios`],
              ["Extrapolated", v.calibration.extrapolated ? <span className="text-review">yes — outside calibration range, confidence lowered</span> : "no — within calibration range"],
              ["MMD² (embeddings)", <span className="font-mono">{v.tests.mmd2} · p {v.tests.p_value <= 0.001 ? "< 0.001" : v.tests.p_value} · {v.tests.permutations} permutations</span>],
              ["Novel samples", <span className="font-mono">{(v.tests.novel_fraction * 100).toFixed(0)}%</span>],
            ]} />
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <SectionTitle title="What changed" hint="Standardised effect size per descriptor, grouped by factor (R-SHIFT-2)." />
          <div className="h-[330px]">
            <ResponsiveContainer>
              <BarChart data={desc} layout="vertical" margin={{ left: 40, right: 16, top: 4, bottom: 4 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" domain={[-3, 3]} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" width={150} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
                <ReferenceLine x={0} stroke="#3a4658" />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} formatter={(x: number, _n, p: any) => [`${x > 0 ? "+" : ""}${x}σ`, p.payload.factor]} />
                <Bar dataKey="effect_size" radius={3} barSize={13}>
                  {desc.map((d) => <Cell key={d.name} fill={Math.abs(d.effect_size) >= 1.5 ? "#ef5a5f" : Math.abs(d.effect_size) >= 0.5 ? "#e8ad3d" : "#3a4658"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {FACTOR_ORDER.map((f) => (
              <span key={f} className="rounded border border-line bg-raised px-2 py-1 text-[11.5px] text-ink-2">{f} <span className={cx("font-mono", Math.abs(v.factors[f]) >= 1 ? "text-review" : "text-ink-3")}>{v.factors[f] > 0 ? "+" : ""}{v.factors[f]}σ</span></span>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle title="Embedding projection" hint="Reference vs new batch in the frozen feature space (2-D projection)." />
          <div className="h-[330px]">
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid />
                <XAxis type="number" dataKey="0" tickLine={false} axisLine={false} domain={[-4, 5]} />
                <YAxis type="number" dataKey="1" tickLine={false} axisLine={false} domain={[-4, 4]} />
                <ZAxis range={[18, 18]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Scatter name="Reference" data={v.projection.reference} fill="#4d6a93" fillOpacity={0.65} />
                <Scatter name="Input batch" data={v.projection.observed} fill="#e8ad3d" fillOpacity={0.75} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
        <Card>
          <SectionTitle title="Radial frequency spectrum" hint="Band energy, reference vs batch. Excess high-frequency energy can indicate manipulation." />
          <div className="h-[240px]">
            <ResponsiveContainer>
              <LineChart data={v.spectrum} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="band" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line dataKey="reference" name="Reference" stroke="#8db7ff" strokeWidth={2} dot={{ r: 3 }} />
                <Line dataKey="observed" name="Input batch" stroke="#e8ad3d" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <SectionTitle title="Evidence rules" hint="Drift vs manipulation is decided only where the evidence supports it; conflicts give INCONCLUSIVE (R-SHIFT-4)." />
          <div className="space-y-4">
            {groups.map((g) => {
              const rs = v.rules.filter((r) => r.supports === g);
              if (!rs.length) return null;
              return (
                <div key={g}>
                  <div className="mb-1.5 text-[11.5px] font-medium text-ink-3">Supports: {verdictText[g]}</div>
                  <div className="space-y-1">
                    {rs.map((r) => (
                      <div key={r.rule} className={cx("flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[12.5px]", r.fired ? "bg-raised text-ink" : "text-ink-3")}>
                        {r.fired ? <CircleCheck size={14} className="text-brand" /> : <CircleMinus size={14} />}
                        {r.rule}
                        <span className="ml-auto text-[10.5px] font-semibold tracking-wider">{r.fired ? "FIRED" : "not fired"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle title="Most novel samples" hint={Object.keys(v.metadata).length ? `Acquisition metadata: ${Object.entries(v.metadata).map(([k, x]) => `${k.replace(/_/g, " ")} ${x}`).join(" · ")}` : "No acquisition metadata supplied with this batch."} />
        <div className="grid grid-cols-4 gap-3 md:grid-cols-8">{v.novel_samples.map((s) => <Thumb key={s} id={s} size={130} />)}</div>
      </Card>
    </div>
  );
}
