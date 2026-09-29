import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight, BookOpen, CirclePlus, CornerDownLeft, Database, FileText, FlaskConical, FolderKanban, LayoutDashboard,
  Link2, ListChecks, ScrollText, Search, Settings, ShieldAlert, CircleCheck, CircleX, TriangleAlert, Info, X,
} from "lucide-react";
import { api, type AssessmentRow, type Finding } from "../lib/api";
import { useApp } from "../lib/app";
import { useKey } from "../lib/hooks";
import { cx, DispositionBadge } from "./ui";

interface Item {
  id: string;
  group: "Actions" | "Go to" | "Assessments" | "Findings";
  label: string;
  hint?: string;
  icon: React.ReactNode;
  badge?: React.ReactNode;
  run: () => void;
  keywords?: string;
}

function score(q: string, text: string): number {
  if (!q) return 1;
  const t = text.toLowerCase();
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  let s = 0;
  for (const w of words) {
    const i = t.indexOf(w);
    if (i < 0) return 0;
    s += i === 0 ? 3 : t[i - 1] === " " ? 2 : 1;
  }
  return s;
}

export function CommandPalette() {
  const { paletteOpen: open, setPaletteOpen, openFinding, user, toast, refreshStatus } = useApp();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const [asms, setAsms] = useState<AssessmentRow[]>([]);
  const [finds, setFinds] = useState<Finding[]>([]);
  const input = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useKey((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen(!open); }
    const tag = (e.target as HTMLElement)?.tagName;
    if (!open && e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") { e.preventDefault(); setPaletteOpen(true); }
  });

  useEffect(() => {
    if (!open) return;
    setQ("");
    setSel(0);
    setTimeout(() => input.current?.focus(), 10);
    api.get<{ items: AssessmentRow[] }>("/assessments").then((d) => setAsms(d.items)).catch(() => {});
    api.get<{ items: Finding[] }>("/findings").then((d) => setFinds(d.items)).catch(() => {});
  }, [open]);

  const close = () => setPaletteOpen(false);
  const go = (to: string) => () => { nav(to); close(); };

  const items: Item[] = useMemo(() => {
    const base: Item[] = [
      { id: "a-new", group: "Actions", label: "Start a new assessment", icon: <CirclePlus size={15} />, run: go("/assessments/new"), keywords: "create run assess" },
      { id: "a-verify", group: "Actions", label: "Verify the audit chain now", icon: <Link2 size={15} />, keywords: "integrity hash tamper",
        run: async () => {
          close();
          const r = await api.post<{ valid: boolean; entries_checked: number; first_failure_index: number | null; failure_reason: string | null }>("/audit/verify");
          refreshStatus();
          toast(r.valid ? { tone: "ok", title: "Audit chain valid", detail: `${r.entries_checked} entries recomputed: every hash link and signature confirmed.` }
            : { tone: "danger", title: `Audit chain broken at entry ${r.first_failure_index}`, detail: r.failure_reason ?? undefined });
        } },
      { id: "a-unres", group: "Actions", label: "Show unresolved findings", icon: <ShieldAlert size={15} />, run: go("/findings?unresolved=1"), keywords: "triage decide queue" },
      { id: "g-dash", group: "Go to", label: "Dashboard", icon: <LayoutDashboard size={15} />, run: go("/") },
      { id: "g-asm", group: "Go to", label: "Assessments", icon: <FolderKanban size={15} />, run: go("/assessments") },
      { id: "g-assets", group: "Go to", label: "Assets", icon: <Database size={15} />, run: go("/assets/dataset"), keywords: "dataset model records reference batch" },
      { id: "g-find", group: "Go to", label: "Findings", icon: <ListChecks size={15} />, run: go("/findings") },
      { id: "g-rep", group: "Go to", label: "Reports", icon: <FileText size={15} />, run: go("/reports"), keywords: "verify signed json" },
      { id: "g-audit", group: "Go to", label: "Audit log", icon: <ScrollText size={15} />, run: go("/audit") },
      { id: "g-cov", group: "Go to", label: "Coverage & limitations", icon: <BookOpen size={15} />, run: go("/coverage"), keywords: "unsupported assumptions" },
      ...(user?.role === "ADMIN" ? [
        { id: "g-lab", group: "Go to" as const, label: "Attack Lab", icon: <FlaskConical size={15} />, run: go("/attack-lab"), keywords: "scenario poison backdoor" },
        { id: "g-set", group: "Go to" as const, label: "Settings", icon: <Settings size={15} />, run: go("/settings/users"), keywords: "users keys policy thresholds" },
      ] : []),
    ];
    const a: Item[] = asms.map((x) => ({
      id: x.id, group: "Assessments", label: x.name, hint: x.modules.join(" "), icon: <FolderKanban size={15} />,
      badge: <DispositionBadge value={x.overall_disposition} />, run: go(`/assessments/${x.id}/overview`),
    }));
    const f: Item[] = finds.map((x) => ({
      id: x.id, group: "Findings", label: `${x.check_name} — ${x.asset_label}`, hint: x.reason, icon: <ListChecks size={15} />,
      badge: <DispositionBadge value={x.effective_disposition} unavailable={x.status === "UNAVAILABLE"} />,
      run: () => { close(); openFinding(x.id, finds.map((y) => y.id)); }, keywords: `${x.check_id} ${x.severity}`,
    }));
    return [...base, ...a, ...f];
  }, [asms, finds, user]);

  const results = useMemo(() => {
    const scored = items.map((it) => ({ it, s: score(q, `${it.label} ${it.hint ?? ""} ${it.keywords ?? ""} ${it.group}`) })).filter((x) => x.s > 0);
    if (!q) return scored.filter((x) => x.it.group !== "Findings").slice(0, 14).map((x) => x.it);
    return scored.sort((a, b) => b.s - a.s).slice(0, 30).map((x) => x.it);
  }, [items, q]);

  useEffect(() => { setSel(0); }, [q]);
  useEffect(() => { listRef.current?.querySelector(`[data-idx="${sel}"]`)?.scrollIntoView({ block: "nearest" }); }, [sel]);

  if (!open) return null;
  let lastGroup = "";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]" onKeyDown={(e) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(results.length - 1, s + 1)); }
      if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
      if (e.key === "Enter") { e.preventDefault(); results[sel]?.run(); }
    }}>
      <div className="absolute inset-0 bg-black/45 backdrop-blur-[3px]" onClick={close} />
      <div className="palette-in glass-strong relative w-full max-w-[640px] overflow-hidden rounded-2xl" role="dialog" aria-label="Command palette">
        <div className="flex items-center gap-3 px-4 py-3.5 shadow-[inset_0_-1px_0_rgb(255_255_255/0.06)]">
          <Search size={16} className="text-ink-3" />
          <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search assessments, findings, pages or actions…"
            className="flex-1 bg-transparent text-[15px] text-ink placeholder:text-ink-3 focus:outline-none focus-visible:outline-none" aria-label="Search" />
          <kbd className="rounded border border-line px-1.5 py-0.5 font-mono text-[10.5px] text-ink-3">Esc</kbd>
        </div>
        <div ref={listRef} className="max-h-[52vh] overflow-y-auto p-2">
          {results.length === 0 && <div className="px-3 py-10 text-center text-[13px] text-ink-3">Nothing matches “{q}”. Try a contributor, a check such as “patch”, or a record number.</div>}
          {results.map((it, i) => {
            const head = it.group !== lastGroup ? (lastGroup = it.group) : null;
            return (
              <div key={it.id}>
                {head && <div className="px-3 pb-1 pt-3 text-[11px] font-medium text-ink-3">{head}</div>}
                <button data-idx={i} onMouseMove={() => setSel(i)} onClick={it.run}
                  className={cx("flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors duration-150", i === sel ? "bg-brand/[0.12] text-ink" : "text-ink-2")}>
                  <span className={i === sel ? "text-brand" : "text-ink-3"}>{it.icon}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13.5px]">{it.label}</span>
                    {it.hint && <span className="block truncate text-[11.5px] text-ink-3">{it.hint}</span>}
                  </span>
                  {it.badge}
                  {i === sel && <CornerDownLeft size={13} className="text-ink-3" />}
                </button>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 px-4 py-2.5 text-[11px] text-ink-3 shadow-[inset_0_1px_0_rgb(255_255_255/0.06)]">
          <span><kbd className="font-mono">↑↓</kbd> move</span><span><kbd className="font-mono">Enter</kbd> open</span>
          <span className="ml-auto">In a finding: <kbd className="font-mono">A</kbd> <kbd className="font-mono">R</kbd> <kbd className="font-mono">Q</kbd> decide · <kbd className="font-mono">J</kbd>/<kbd className="font-mono">K</kbd> next/prev</span>
        </div>
      </div>
    </div>
  );
}

const TONE = {
  ok: { icon: <CircleCheck size={17} className="text-accept" />, ring: "shadow-[inset_3px_0_0_var(--color-accept)]" },
  warn: { icon: <TriangleAlert size={17} className="text-review" />, ring: "shadow-[inset_3px_0_0_var(--color-review)]" },
  danger: { icon: <CircleX size={17} className="text-quarantine" />, ring: "shadow-[inset_3px_0_0_var(--color-quarantine)]" },
  info: { icon: <Info size={17} className="text-brand" />, ring: "shadow-[inset_3px_0_0_var(--color-brand)]" },
};

export function Toasts() {
  const { toasts, dismiss } = useApp();
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[360px] flex-col gap-2.5" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className="toast-in glass-strong pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3.5">
          <span className="mt-0.5">{TONE[t.tone].icon}</span>
          <div className="min-w-0 flex-1">
            <div className="text-[13.5px] font-medium text-ink">{t.title}</div>
            {t.detail && <div className="mt-0.5 text-[12.5px] leading-snug text-ink-2">{t.detail}</div>}
          </div>
          <button onClick={() => dismiss(t.id)} className="rounded p-0.5 text-ink-3 hover:text-ink" aria-label="Dismiss"><X size={14} /></button>
        </div>
      ))}
    </div>
  );
}

export { ArrowRight };
