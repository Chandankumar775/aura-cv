import { useState } from "react";
import { X, Info } from "lucide-react";
import type { Assessment, Finding } from "../../lib/api";
import { useApp } from "../../lib/app";
import { useApi } from "../../lib/hooks";
import { Card, CanvasOverlay, cx, DispositionBadge, ErrorState, Loading, Notice, RiskBar, SectionTitle, Thumb } from "../../components/ui";

interface SourceRow { contributor_id: string; name: string; samples: number; flagged: number; risk: number; ci: [number, number]; breakdown: Record<string, number>; disposition: any }
interface DataView {
  has_metadata: boolean;
  classes: string[];
  totals: { images: number; flagged: number; contributors: number; batches: number };
  source_risk: SourceRow[];
  counts_by_attack: Record<string, number>;
  triggers: null | { location: { x: number; y: number; w: number; h: number; image_size: number; label: string }; label_concentration: Record<string, number>; samples: string[]; residual_samples: string[] };
  label_issues: { sample_id: string; contributor: string; given: string; consensus: string; agreement: number; neighbours: string[] }[];
  systematic: null | { contributor: string; source_class: string; target_class: string; rate: number; pooled_rate: number; samples: string[] };
  duplicate_clusters: { cluster_id: string; size: number; contributor: string; min_similarity: number; method: string; members: string[] }[];
  ood: { sample_id: string; contributor: string | null; score: number; threshold: number; nearest: string[] }[];
  confusion: Record<string, number[][]>;
}

const CHIP: Record<string, string> = { trigger: "Trigger", flip: "Flip", systematic: "Systematic", duplicate: "Duplicate", ood: "OOD" };

function Heatmap({ m, classes, highlight }: { m: number[][]; classes: string[]; highlight?: [number, number] }) {
  return (
    <div className="inline-block">
      <div className="grid gap-[3px]" style={{ gridTemplateColumns: `92px repeat(${classes.length}, 46px)` }}>
        <div />
        {classes.map((c) => <div key={c} className="truncate pb-1 text-center text-[10px] text-ink-3" title={c}>{c.replace("civilian_", "civ_")}</div>)}
        {m.map((row, i) => {
          const tot = row.reduce((a, b) => a + b, 0) || 1;
          return [
            <div key={`l${i}`} className="flex items-center justify-end pr-2 text-[10.5px] text-ink-3">{classes[i]}</div>,
            ...row.map((v, j) => {
              const r = v / tot;
              const hl = highlight && highlight[0] === i && highlight[1] === j;
              const diag = i === j;
              return (
                <div key={`${i}-${j}`} title={`given ${classes[j]} · looks like ${classes[i]}: ${v}`}
                  className={cx("flex h-9 items-center justify-center rounded font-mono text-[10.5px]", hl && "ring-2 ring-quarantine")}
                  style={{ background: diag ? `rgba(141,183,255,${0.12 + r * 0.5})` : `rgba(239,90,95,${Math.min(0.85, r * 4)})`, color: r > 0.12 || diag ? "#e8edf4" : "#6c7787" }}>
                  {v}
                </div>
              );
            }),
          ];
        })}
      </div>
      <div className="mt-2 text-[10.5px] text-ink-3">Rows: consensus class (what the image looks like) · Columns: label given by the contributor</div>
    </div>
  );
}

function Drawer({ row, view, onClose, findings }: { row: SourceRow; view: DataView; onClose: () => void; findings: Finding[] }) {
  const { openFinding } = useApp();
  const mine = findings.filter((f) => f.affected_asset.id === row.contributor_id);
  const sys = view.systematic?.contributor === row.contributor_id ? view.systematic : null;
  const samples = mine.flatMap((f) => f.evidence.sample_ids).slice(0, 18);
  return (
    <div className="fixed inset-0 z-30 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <aside className="slide-in glass-strong relative h-full w-[min(700px,94vw)] overflow-y-auto p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="label-caps">Contributor</div>
            <h3 className="mt-1 text-[20px] font-semibold text-ink">{row.name}</h3>
            <div className="font-mono text-[12px] text-ink-3">{row.contributor_id}</div>
          </div>
          <button onClick={onClose} className="rounded p-1.5 text-ink-3 hover:bg-raised"><X size={17} /></button>
        </div>
        <div className="mt-5 grid grid-cols-4 gap-px overflow-hidden rounded-lg border border-line bg-line text-center">
          {[["Samples", row.samples], ["Flagged", row.flagged], ["Risk", row.risk.toFixed(1)], ["90% interval", `${row.ci[0]}–${row.ci[1]}`]].map(([k, v]) => (
            <div key={k as string} className="bg-raised px-2 py-3"><div className="label-caps">{k}</div><div className="mt-1 font-mono text-[16px] text-ink">{v}</div></div>
          ))}
        </div>
        <div className="mt-6">
          <div className="label-caps mb-2">Evidence by attack type</div>
          <div className="space-y-1.5">
            {Object.entries(row.breakdown).map(([k, v]) => (
              <div key={k} className="grid grid-cols-[90px_1fr_40px] items-center gap-3 text-[12.5px]">
                <span className="text-ink-3">{CHIP[k]}</span>
                <span className="h-1.5 rounded-full bg-line"><span className="block h-full rounded-full bg-quarantine/80" style={{ width: `${Math.min(100, (v / Math.max(1, row.flagged)) * 100)}%` }} /></span>
                <span className="text-right font-mono text-ink-2">{v}</span>
              </div>
            ))}
          </div>
        </div>
        {view.confusion[row.contributor_id] && (
          <div className="mt-7">
            <div className="label-caps mb-3">Confusion matrix · systematic mislabelling check</div>
            <Heatmap m={view.confusion[row.contributor_id]} classes={view.classes} highlight={sys ? [view.classes.indexOf(sys.source_class), view.classes.indexOf(sys.target_class)] : undefined} />
            {sys && <p className="mt-3 text-[12.5px] text-ink-2">Relabels <b className="text-ink">{sys.source_class}</b> → <b className="text-ink">{sys.target_class}</b> at <span className="font-mono text-quarantine">{(sys.rate * 100).toFixed(1)}%</span> vs <span className="font-mono">{(sys.pooled_rate * 100).toFixed(1)}%</span> for all other contributors.</p>}
          </div>
        )}
        {mine.length > 0 && (
          <div className="mt-7">
            <div className="label-caps mb-2">Findings for this contributor</div>
            <div className="space-y-2">
              {mine.map((f) => (
                <button key={f.id} onClick={() => openFinding(f.id, mine.map((x) => x.id))} className="flex w-full items-center gap-3 rounded-lg border border-line bg-raised/50 px-3 py-2.5 text-left hover:bg-hover">
                  <DispositionBadge value={f.effective_disposition} />
                  <span className="flex-1 text-[12.5px] text-ink">{f.check_name}</span>
                  <span className="font-mono text-[11px] text-ink-3">{f.confidence.toFixed(2)}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {samples.length > 0 && (
          <div className="mt-7">
            <div className="label-caps mb-2">Flagged samples</div>
            <div className="grid grid-cols-6 gap-2">{samples.map((s) => <Thumb key={s} id={s} size={96} overlay={s.includes("-trg-") ? view.triggers?.location : null} />)}</div>
          </div>
        )}
      </aside>
    </div>
  );
}

export default function DataTab({ asm, findings }: { asm: Assessment; findings: Finding[] }) {
  const { data: v, error, loading } = useApi<DataView>(`/assessments/${asm.id}/data`);
  const [sel, setSel] = useState<SourceRow | null>(null);
  const [sample, setSample] = useState<string | null>(null);
  if (loading) return <Loading />;
  if (error || !v) return <ErrorState error={error} />;
  const gaps = findings.filter((f) => f.module === "M1" && f.status === "UNAVAILABLE");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[["Images", v.totals.images.toLocaleString("en-IN")], ["Flagged", v.totals.flagged], ["Contributors", v.totals.contributors || "—"], ["Batches", v.totals.batches || "—"]].map(([k, x]) => (
          <Card key={k as string} className="!p-4"><div className="label-caps">{k}</div><div className="mt-1.5 font-mono text-[22px] text-ink">{x}</div></Card>
        ))}
      </div>

      {!v.has_metadata && (
        <Notice tone="warn" icon={<Info size={16} className="mt-0.5 text-review" />}>
          <b className="text-ink">Source-level risk unavailable:</b> no contributor / batch / source metadata was supplied, so sample-level evidence cannot be aggregated per source (R-DATA-6). Findings below are sample-level only.
        </Notice>
      )}
      {gaps.length > 0 && v.has_metadata && <Notice tone="warn">{gaps.length} data check(s) were unavailable — see Overview.</Notice>}

      {v.source_risk.length > 0 && (
        <Card>
          <SectionTitle title="Contributor risk" hint="Beta-Binomial posterior per contributor, using confidence-weighted flags. Click a row for the drill-down." />
          <div className="overflow-hidden rounded-lg border border-line">
            <table className="w-full text-[13px]">
              <thead><tr className="border-b border-line bg-raised/40 text-left">{["Contributor", "Samples", "Flagged", "Risk (0–100)", "Evidence", "Disposition"].map((h) => <th key={h} className="label-caps px-4 py-2.5 font-semibold">{h}</th>)}</tr></thead>
              <tbody>
                {v.source_risk.map((r, i) => (
                  <tr key={r.contributor_id} onClick={() => setSel(r)} className="cursor-pointer border-b border-line-soft last:border-0 hover:bg-hover">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">{i === 0 && r.risk > 70 && <span className="rounded bg-quarantine/15 px-1.5 py-0.5 text-[10px] font-semibold text-quarantine">RANK 1</span>}<span className="font-medium text-ink">{r.name}</span></div>
                      <div className="font-mono text-[11px] text-ink-3">{r.contributor_id}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-ink-2">{r.samples}</td>
                    <td className="px-4 py-3 font-mono text-ink-2">{r.flagged}</td>
                    <td className="px-4 py-3"><RiskBar value={r.risk} /><div className="mt-0.5 font-mono text-[10.5px] text-ink-3">90% CI {r.ci[0]}–{r.ci[1]}</div></td>
                    <td className="px-4 py-3"><div className="flex flex-wrap gap-1">{Object.entries(r.breakdown).filter(([, n]) => n > 0).map(([k, n]) => <span key={k} className="rounded border border-line bg-raised px-1.5 py-0.5 text-[11px] text-ink-2">{CHIP[k]} <span className="font-mono">{n}</span></span>)}</div></td>
                    <td className="px-4 py-3"><DispositionBadge value={r.disposition} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {v.triggers && (
        <Card>
          <SectionTitle title="Trigger injection" hint={`Repeated patch at ${v.triggers.location.label}; label concentration ${Object.entries(v.triggers.label_concentration).map(([k, n]) => `${k} ${n}`).join(", ")}.`} />
          <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
            <div>
              <CanvasOverlay id={sample ?? v.triggers.samples[0]} size={300} boxes={[{ ...v.triggers.location, label: "repeated patch" }]} />
              <div className="mt-2 font-mono text-[11px] text-ink-3">{sample ?? v.triggers.samples[0]}</div>
            </div>
            <div>
              <div className="label-caps mb-2">Patch occurrences</div>
              <div className="flex flex-wrap gap-2">{v.triggers.samples.map((s) => <Thumb key={s} id={s} size={84} overlay={v.triggers!.location} onClick={() => setSample(s)} />)}</div>
              <div className="label-caps mb-2 mt-5">High-frequency residue (same region)</div>
              <div className="flex flex-wrap gap-2">{v.triggers.residual_samples.map((s) => <Thumb key={s} id={s} size={84} overlay={v.triggers!.location} onClick={() => setSample(s)} />)}</div>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        {v.label_issues.length > 0 && (
          <Card>
            <SectionTitle title="Label issues" hint="Given label vs neighbour consensus." />
            <div className="space-y-2.5">
              {v.label_issues.slice(0, 5).map((l) => (
                <div key={l.sample_id} className="flex items-center gap-3 rounded-lg border border-line bg-raised/40 p-2.5">
                  <Thumb id={l.sample_id} size={60} />
                  <div className="min-w-[120px] text-[12.5px]">
                    <div><span className="text-ink-3">given</span> <span className="text-quarantine line-through decoration-quarantine/50">{l.given}</span></div>
                    <div><span className="text-ink-3">consensus</span> <span className="font-medium text-accept">{l.consensus}</span></div>
                    <div className="font-mono text-[11px] text-ink-3">agreement {(l.agreement * 100).toFixed(0)}%</div>
                  </div>
                  <div className="ml-auto flex gap-1.5">{l.neighbours.map((n) => <Thumb key={n} id={n} size={44} />)}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
        {v.duplicate_clusters.length > 0 && (
          <Card>
            <SectionTitle title="Near-duplicate clusters" hint="Groups of near-identical images; flooding inflates a scene's weight." />
            <div className="space-y-4">
              {v.duplicate_clusters.map((c) => (
                <div key={c.cluster_id}>
                  <div className="mb-1.5 flex items-center justify-between text-[12.5px]">
                    <span className="text-ink"><span className="font-mono text-ink-3">{c.cluster_id}</span> · {c.size} images · {c.contributor.replace("contributor_", "contributor ")}</span>
                    <span className="font-mono text-[11px] text-ink-3">{c.method} · sim ≥ {c.min_similarity}</span>
                  </div>
                  <div className="flex gap-1.5 overflow-hidden">{c.members.map((m) => <Thumb key={m} id={m} size={58} />)}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
        {v.ood.length > 0 && (
          <Card>
            <SectionTitle title="Out-of-distribution insertion" hint="Samples far from the reference, next to their nearest in-distribution images." />
            <div className="space-y-2.5">
              {v.ood.slice(0, 4).map((o) => (
                <div key={o.sample_id} className="flex items-center gap-3 rounded-lg border border-line bg-raised/40 p-2.5">
                  <Thumb id={o.sample_id} size={60} />
                  <div className="text-[12.5px]"><div className="font-mono text-quarantine">score {o.score.toFixed(2)}</div><div className="text-ink-3">threshold {o.threshold.toFixed(2)}</div></div>
                  <div className="ml-auto flex gap-1.5">{o.nearest.map((n) => <Thumb key={n} id={n} size={44} />)}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
      {sel && <Drawer row={sel} view={v} findings={findings} onClose={() => setSel(null)} />}
    </div>
  );
}
