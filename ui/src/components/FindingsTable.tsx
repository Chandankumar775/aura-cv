import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { Finding } from "../lib/api";
import { useApp } from "../lib/app";
import { moduleNames } from "../lib/format";
import { ConfidenceMeter, cx, DispositionBadge, EmptyState, SeverityBadge } from "./ui";

type Filter = { module: string; disp: string; status: string; unresolved: boolean; q: string };

function Select({ value, onChange, options, label }: { value: string; onChange: (v: string) => void; options: [string, string][]; label: string }) {
  return (
    <label className="flex items-center gap-2 text-[12px] text-ink-3">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="h-8 rounded-md border border-line bg-raised px-2 text-[12.5px] text-ink focus:outline-none">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}

export default function FindingsTable({ items, showAssessment, initialUnresolved = false }: { items: Finding[]; showAssessment?: boolean; initialUnresolved?: boolean }) {
  const { openFinding } = useApp();
  const [f, setF] = useState<Filter>({ module: "", disp: "", status: "", unresolved: initialUnresolved, q: "" });
  const rows = useMemo(() => items.filter((x) =>
    (!f.module || x.module === f.module) && (!f.disp || x.effective_disposition === f.disp) && (!f.status || x.status === f.status) &&
    (!f.unresolved || x.unresolved) && (!f.q || `${x.reason} ${x.check_id} ${x.asset_label} ${x.check_name}`.toLowerCase().includes(f.q.toLowerCase()))), [items, f]);
  const ids = rows.map((r) => r.id);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
          <input value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} placeholder="Search reason, check, asset…"
            className="h-8 w-64 rounded-md border border-line bg-raised pl-8 pr-3 text-[12.5px] text-ink placeholder:text-ink-3 focus:border-brand/50 focus:outline-none" />
        </div>
        <Select label="Module" value={f.module} onChange={(v) => setF({ ...f, module: v })} options={[["", "All"], ["M1", "M1 Data"], ["M2", "M2 Model"], ["M3", "M3 Provenance"], ["M4", "M4 Shift"]]} />
        <Select label="Effective" value={f.disp} onChange={(v) => setF({ ...f, disp: v })} options={[["", "All"], ["QUARANTINE", "Quarantine"], ["REVIEW", "Review"], ["ACCEPT", "Accept"]]} />
        <Select label="Status" value={f.status} onChange={(v) => setF({ ...f, status: v })} options={[["", "All"], ["FLAGGED", "Flagged"], ["UNAVAILABLE", "Unavailable"]]} />
        <label className="flex items-center gap-2 text-[12.5px] text-ink-2">
          <input type="checkbox" checked={f.unresolved} onChange={(e) => setF({ ...f, unresolved: e.target.checked })} className="accent-[var(--color-brand)]" /> Unresolved only
        </label>
        <span className="ml-auto text-[12px] text-ink-3">{rows.length} of {items.length}</span>
      </div>
      {rows.length === 0 ? <EmptyState title="No findings match these filters" /> : (
        <div className="glass overflow-hidden rounded-2xl">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line bg-raised/40 text-left">
                {["Severity", "Recommended", "Effective", "Finding", "Affected asset", "Confidence", ""].map((h) => <th key={h} className="label-caps px-3.5 py-2.5 font-semibold">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.id} onClick={() => openFinding(x.id, ids)} className={cx("cursor-pointer border-b border-line-soft last:border-0 hover:bg-hover", x.status === "UNAVAILABLE" && "bg-raised/30")}>
                  <td className="px-3.5 py-3"><SeverityBadge value={x.severity} /></td>
                  <td className="px-3.5 py-3"><DispositionBadge value={x.recommended_disposition} unavailable={x.status === "UNAVAILABLE"} /></td>
                  <td className="px-3.5 py-3"><DispositionBadge value={x.effective_disposition} /></td>
                  <td className="max-w-[460px] px-3.5 py-3">
                    <div className="font-medium text-ink">{x.check_name}</div>
                    <div className="mt-0.5 line-clamp-1 text-[12px] text-ink-3">{x.reason}</div>
                    {showAssessment && <div className="mt-0.5 text-[11px] text-ink-3/80">{x.assessment_name}</div>}
                  </td>
                  <td className="max-w-[220px] truncate px-3.5 py-3 text-ink-2" title={x.asset_label}>{x.asset_label}<div className="text-[11px] text-ink-3">{moduleNames[x.module]}</div></td>
                  <td className="px-3.5 py-3"><ConfidenceMeter value={x.confidence} width={44} /></td>
                  <td className="px-3.5 py-3 text-right">
                    {x.unresolved ? <span className="text-[11px] font-medium text-review">needs decision</span> : x.decision_count ? <span className="text-[11px] text-ink-3">decided</span> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
