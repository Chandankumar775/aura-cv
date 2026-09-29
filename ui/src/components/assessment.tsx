import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, CircleDashed, Database, Cpu, Radio, Users, Aperture, TriangleAlert } from "lucide-react";
import type { Assessment, AssessmentRow, Disposition, Finding, Summary, Tile } from "../lib/api";
import { useApp } from "../lib/app";
import { moduleNames, relTime } from "../lib/format";
import { ConfidenceMeter, cx, DispositionBadge, SeverityBadge, StatusPill } from "./ui";

const VERDICT_COPY: Record<Disposition, { title: string; line: string; tone: string; glow: string }> = {
  ACCEPT: { title: "ACCEPT", line: "No finding requires action. Assets may be used for their declared purpose.", tone: "text-accept", glow: "from-accept/25" },
  REVIEW: { title: "REVIEW", line: "Findings need an analyst's judgement before the assets are used.", tone: "text-review", glow: "from-review/25" },
  QUARANTINE: { title: "QUARANTINE", line: "At least one asset shows evidence of compromise. Do not deploy until resolved.", tone: "text-quarantine", glow: "from-quarantine/30" },
};

const TILE_ICON: Record<string, React.ReactNode> = {
  dataset: <Database size={15} />, contributors: <Users size={15} />, model: <Cpu size={15} />, records: <Radio size={15} />, input_batch: <Aperture size={15} />,
};
const TILE_TAB: Record<string, string> = { dataset: "data", contributors: "data", model: "model", records: "provenance", input_batch: "shift" };

const CHAIN_ORDER = ["contributors", "dataset", "model", "records", "input_batch"];
const DOT: Record<string, string> = { ACCEPT: "var(--color-accept)", REVIEW: "var(--color-review)", QUARANTINE: "var(--color-quarantine)" };

export function AssetTile({ t, asmId, index = 0 }: { t: Tile; asmId: string; index?: number }) {
  const nav = useNavigate();
  const delay = { animationDelay: `${160 + index * 120}ms` };
  if (!t.assessed) {
    return (
      <div className="node-in glass-inset flex h-full min-h-[172px] flex-col rounded-xl p-3.5 opacity-70" style={delay}>
        <div className="flex items-center gap-2 text-[12.5px] text-ink-3">{TILE_ICON[t.key]} {t.label}</div>
        <div className="mt-auto text-[12px] leading-snug text-ink-3">Not in scope for this assessment</div>
      </div>
    );
  }
  return (
    <button onClick={() => nav(`/assessments/${asmId}/${TILE_TAB[t.key]}`)} style={delay}
      className="node-in glass-inset glass-hover group relative flex h-full min-h-[172px] w-full flex-col rounded-xl p-3.5 text-left">
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2 whitespace-nowrap text-[12.5px] font-medium text-ink-2"><span className="shrink-0 2xl:hidden">{TILE_ICON[t.key]}</span><span className="truncate">{t.label}</span></span>
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: DOT[t.disposition!], boxShadow: `0 0 12px 1px ${DOT[t.disposition!]}` }} />
      </div>
      <div className="mt-1 truncate text-[11.5px] text-ink-3" title={t.worst?.name ?? t.asset?.name}>
        {t.key === "contributors" ? (t.worst ? <>Worst: <span className="text-ink-2">{t.worst.name}</span></> : t.note ?? "All sources within tolerance") : t.asset?.name}
      </div>
      <div className="mt-3 min-h-[36px] text-[12.5px] font-medium leading-snug text-ink" title={t.top_reason ?? ""}>
        {t.top_issue ?? <span className="font-normal text-ink-3">No action needed</span>}
      </div>
      <div className="mt-auto pt-3">
        <DispositionBadge value={t.disposition} />
        <div className="mt-2 flex items-center justify-between gap-2">
          <ConfidenceMeter value={t.confidence ?? null} width={28} />
          <span className="whitespace-nowrap text-[11px] text-ink-3">{t.findings} findings</span>
        </div>
        {!!t.coverage_gaps?.length && (
          <div className="mt-2 inline-flex items-center gap-1 rounded border border-dashed border-gap/60 px-1.5 py-0.5 text-[10.5px] font-medium text-gap" title={t.coverage_gaps.join(", ")}>
            <CircleDashed size={10} /> {t.coverage_gaps.length} coverage gap{t.coverage_gaps.length > 1 ? "s" : ""}
          </div>
        )}
      </div>
    </button>
  );
}

function Connector({ from, index }: { from?: Disposition; index: number }) {
  const c = from ? DOT[from] : "rgb(255 255 255 / 0.15)";
  const line = { ["--len" as string]: 22, animationDelay: `${260 + index * 120}ms`, opacity: 0.85 } as React.CSSProperties;
  const head = { ["--len" as string]: 12, animationDelay: `${420 + index * 120}ms`, opacity: 0.85 } as React.CSSProperties;
  return (
    <svg width="26" height="14" viewBox="0 0 26 14" className="hidden shrink-0 self-center xl:block" aria-hidden>
      <path d="M1 7 H21" stroke={c} strokeWidth="1.5" strokeLinecap="round" className="chain-line" style={line} />
      <path d="M18 3.5 L22.5 7 L18 10.5" fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="chain-line" style={head} />
    </svg>
  );
}

export function TrustChain({ tiles, asmId }: { tiles: Tile[]; asmId: string }) {
  const ordered = CHAIN_ORDER.map((k) => tiles.find((t) => t.key === k)).filter(Boolean) as Tile[];
  return (
    <div className="min-w-0">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:flex xl:items-stretch xl:gap-1">
        {ordered.map((t, i) => (
          <div key={t.key} className="contents xl:flex xl:min-w-0 xl:flex-1 xl:items-stretch xl:gap-1">
            <div className="min-w-0 xl:flex-1"><AssetTile t={t} asmId={asmId} index={i} /></div>
            {i < ordered.length - 1 && <Connector from={t.assessed ? t.disposition : undefined} index={i} />}
          </div>
        ))}
      </div>
      <p className="mt-3 text-[12px] text-ink-3">Trust chain, in pipeline order: where evidence of compromise enters, from contributed data to what the model sees in the field.</p>
    </div>
  );
}

export function VerdictCard({ asm, summary }: { asm: Assessment; summary: Summary; compact?: boolean }) {
  const d = summary.overall_disposition ?? "ACCEPT";
  const v = VERDICT_COPY[d];
  const c = summary.counts.by_effective_disposition;
  return (
    <section className="glass relative overflow-hidden rounded-2xl">
      <div className={cx("pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-gradient-to-br to-transparent blur-2xl", v.glow)} />
      <div className="relative grid gap-7 p-6 2xl:grid-cols-[272px_1fr]">
        <div className="flex flex-col">
          <Link to={`/assessments/${asm.id}/overview`} className="text-[16px] font-semibold leading-snug text-ink [text-wrap:balance] hover:text-brand">{asm.name}</Link>
          <div className="mt-1 text-[12.5px] text-ink-3">{asm.created_by_name} · finished {relTime(asm.finished_at)} · access {asm.access_level_used}</div>
          <div className="mt-7 text-[12px] text-ink-3">Overall disposition</div>
          <div className={cx("verdict-wipe mt-1 whitespace-nowrap text-[40px] font-semibold leading-none tracking-[-0.03em]", v.tone)}>{v.title}</div>
          <p className="mt-3 max-w-[34ch] text-[13px] leading-relaxed text-ink-2">{v.line}</p>
          <div className="mt-auto flex flex-wrap gap-x-5 gap-y-1 pt-5 text-[12.5px]">
            <span><span className="font-mono text-quarantine">{c.QUARANTINE}</span> <span className="text-ink-3">quarantine</span></span>
            <span><span className="font-mono text-review">{c.REVIEW}</span> <span className="text-ink-3">review</span></span>
            <span><span className="font-mono text-accept">{c.ACCEPT}</span> <span className="text-ink-3">accept</span></span>
            {summary.counts.unavailable > 0 && <span><span className="font-mono text-gap">{summary.counts.unavailable}</span> <span className="text-ink-3">unavailable</span></span>}
            <span><span className="font-mono text-ink">{summary.unresolved}</span> <span className="text-ink-3">awaiting decision</span></span>
          </div>
        </div>
        <TrustChain tiles={summary.tiles} asmId={asm.id} />
      </div>
    </section>
  );
}

export function AttentionList({ items, total, unresolved, emptyText }: { items: Finding[]; total: number; unresolved: number; emptyText?: string }) {
  const { openFinding } = useApp();
  const ids = items.map((f) => f.id);
  if (!items.length) {
    return <div className="rounded-lg border border-dashed border-line px-5 py-8 text-center text-[13px] text-ink-3">{emptyText ?? "Nothing needs attention. Every REVIEW or QUARANTINE finding has an analyst decision."}</div>;
  }
  return (
    <div>
      <div className="glass-inset overflow-hidden rounded-xl">
        {items.map((f, i) => (
          <button key={f.id} onClick={() => openFinding(f.id, ids)}
            className={cx("group grid w-full grid-cols-[104px_1fr_18px] items-center gap-4 px-4 py-3 text-left transition-colors duration-150 hover:bg-hover", i > 0 && "border-t border-line-soft")}>
            <div className="space-y-1.5">
              <SeverityBadge value={f.severity} />
              <div><DispositionBadge value={f.recommended_disposition} unavailable={f.status === "UNAVAILABLE"} /></div>
            </div>
            <div className="min-w-0">
              <div className="flex items-baseline gap-2"><span className="shrink-0 text-[13px] font-medium text-ink">{f.check_name}</span><span className="truncate text-[11.5px] text-ink-3">{moduleNames[f.module]} · {f.asset_label}</span></div>
              <div className="mt-0.5 line-clamp-2 text-[12.5px] leading-snug text-ink-2">{f.reason}</div>
            </div>
            <ArrowRight size={14} className="text-ink-3 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-brand" />
          </button>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-[12.5px] text-ink-3">
        <TriangleAlert size={13} className="text-review" />
        <span><span className="font-medium text-ink-2">{unresolved} unresolved</span>{total > items.length && ` (${items.length} shown)`}; the report cannot be finalised until each has an analyst decision.</span>
      </div>
    </div>
  );
}

export function AssessmentTable({ rows }: { rows: AssessmentRow[] }) {
  const nav = useNavigate();
  return (
    <div className="glass-inset overflow-x-auto rounded-xl">
      <table className="w-full min-w-[720px] text-[13px]">
        <thead>
          <tr className="border-b border-line bg-raised/40 text-left">
            {["Assessment", "Modules", "Finished", "Verdict", "Unresolved", "Report"].map((h) => <th key={h} className="label-caps px-4 py-2.5 font-semibold">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.id} onClick={() => nav(a.status === "RUNNING" || a.status === "QUEUED" ? `/assessments/${a.id}/run` : `/assessments/${a.id}/overview`)}
              className="cursor-pointer border-b border-line-soft last:border-0 hover:bg-hover">
              <td className="px-4 py-3">
                <div className="font-medium text-ink">{a.name}</div>
                <div className="text-[11.5px] text-ink-3">{a.created_by_name}</div>
              </td>
              <td className="px-4 py-3"><div className="flex gap-1">{a.modules.map((m) => <span key={m} className="rounded bg-raised px-1.5 py-0.5 font-mono text-[10.5px] text-ink-2" title={moduleNames[m]}>{m}</span>)}</div></td>
              <td className="px-4 py-3 text-ink-2">{a.status === "COMPLETED" ? relTime(a.finished_at) : <StatusPill status={a.status} />}</td>
              <td className="px-4 py-3"><DispositionBadge value={a.overall_disposition} /></td>
              <td className="px-4 py-3 font-mono text-ink-2">{a.status === "COMPLETED" ? a.unresolved : "—"}</td>
              <td className="px-4 py-3">{a.report_status ? <StatusPill status={a.report_status} /> : <span className="text-ink-3">none</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
