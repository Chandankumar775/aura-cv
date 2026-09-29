import { useEffect, useRef, useState, type ReactNode } from "react";
import { Check, CircleCheck, CircleDashed, CircleHelp, CircleX, Copy, LoaderCircle, TriangleAlert } from "lucide-react";
import type { Disposition, Severity, VerificationStep } from "../lib/api";
import { imageUrl } from "../lib/api";
import { shortDigest } from "../lib/format";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

/* ---------------------------------------------------------------- badges */

const DISP: Record<Disposition, { text: string; ring: string; bg: string; dot: string }> = {
  ACCEPT: { text: "text-accept", ring: "border-accept/35", bg: "bg-accept/10", dot: "bg-accept" },
  REVIEW: { text: "text-review", ring: "border-review/35", bg: "bg-review/10", dot: "bg-review" },
  QUARANTINE: { text: "text-quarantine", ring: "border-quarantine/40", bg: "bg-quarantine/10", dot: "bg-quarantine" },
};

export function DispositionBadge({ value, size = "sm", unavailable }: { value: Disposition | null | undefined; size?: "sm" | "md" | "lg"; unavailable?: boolean }) {
  if (unavailable) {
    return (
      <span className={cx("inline-flex items-center gap-1.5 rounded-md border border-dashed border-gap/60 font-semibold tracking-wide text-gap", size === "sm" ? "px-1.5 py-0.5 text-[10.5px]" : "px-2.5 py-1 text-xs")}>
        <CircleDashed size={size === "sm" ? 11 : 13} /> UNAVAILABLE
      </span>
    );
  }
  if (!value) return <span className="text-ink-3">—</span>;
  const s = DISP[value];
  const sz = size === "lg" ? "px-3 py-1.5 text-sm" : size === "md" ? "px-2.5 py-1 text-xs" : "px-1.5 py-0.5 text-[10.5px]";
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-md border font-semibold tracking-[0.06em]", s.text, s.ring, s.bg, sz)}>
      <span className={cx("h-1.5 w-1.5 rounded-full", s.dot)} />
      {value}
    </span>
  );
}

const SEV: Record<Severity, string> = {
  CRITICAL: "text-critical",
  HIGH: "text-quarantine",
  MEDIUM: "text-review",
  LOW: "text-ink-2",
};
const SEV_BARS: Record<Severity, number> = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };

export function SeverityBadge({ value }: { value: Severity }) {
  const n = SEV_BARS[value];
  return (
    <span className={cx("inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wide", SEV[value])} title={`Severity ${value}`}>
      <span className="flex items-end gap-[2px]">
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={cx("w-[3px] rounded-sm", i <= n ? "bg-current" : "bg-line")} style={{ height: 4 + i * 2 }} />
        ))}
      </span>
      {value}
    </span>
  );
}

export function ConfidenceMeter({ value, width = 64 }: { value: number | null | undefined; width?: number }) {
  if (value === null || value === undefined) return <span className="text-ink-3">—</span>;
  return (
    <span className="inline-flex items-center gap-2" title={`Confidence ${value.toFixed(2)}`}>
      <span className="relative h-1.5 overflow-hidden rounded-full bg-line" style={{ width }}>
        <span className="absolute inset-y-0 left-0 rounded-full bg-ink-2" style={{ width: `${Math.round(value * 100)}%` }} />
      </span>
      <span className="font-mono text-xs text-ink-2">{value.toFixed(2)}</span>
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    COMPLETED: "text-accept border-accept/30",
    RUNNING: "text-brand border-brand/40",
    QUEUED: "text-brand border-brand/30",
    PARTIAL: "text-review border-review/35",
    UNAVAILABLE: "text-gap border-gap/50 border-dashed",
    ERROR: "text-quarantine border-quarantine/40",
    FAILED: "text-quarantine border-quarantine/40",
    CANCELLED: "text-gap border-gap/40",
    DRAFT: "text-ink-2 border-line",
    FINAL: "text-accept border-accept/35",
    PENDING: "text-ink-3 border-line",
  };
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10.5px] font-semibold tracking-wider", map[status] ?? "text-ink-2 border-line")}>
      {status === "RUNNING" && <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-brand" />}
      {status}
    </span>
  );
}

export function RequirementTag({ id }: { id: string }) {
  if (!id) return null;
  return <span className="rounded border border-line bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{id}</span>;
}

/* ---------------------------------------------------------------- layout */

export function Card({ children, className, pad = true }: { children: ReactNode; className?: string; pad?: boolean }) {
  return <section className={cx("glass rounded-2xl", pad && "p-5", className)}>{children}</section>;
}

export function SectionTitle({ title, hint, right, icon }: { title: string; hint?: ReactNode; right?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2 className="flex items-center gap-2 text-[15px] font-semibold text-ink">
          {icon}
          {title}
        </h2>
        {hint && <p className="mt-0.5 text-[13px] text-ink-3">{hint}</p>}
      </div>
      {right}
    </div>
  );
}

export function PageHeader({ eyebrow, title, sub, right }: { eyebrow?: ReactNode; title: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  return (
    <header className="mb-8 mt-2 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[28px] font-semibold tracking-[-0.02em] text-ink [text-wrap:balance]">{title}</h1>
        {sub && <div className="mt-1.5 text-[13.5px] text-ink-2">{sub}</div>}
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </header>
  );
}

export function Button({
  children, onClick, variant = "secondary", disabled, type = "button", icon, title, size = "md",
}: {
  children?: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost" | "danger"; disabled?: boolean;
  type?: "button" | "submit"; icon?: ReactNode; title?: string; size?: "sm" | "md";
}) {
  const v = {
    primary: "bg-brand text-[#07101f] hover:bg-[#a9c9ff] border-transparent font-semibold",
    secondary: "bg-raised text-ink hover:bg-hover border-line",
    ghost: "bg-transparent text-ink-2 hover:bg-raised hover:text-ink border-transparent",
    danger: "bg-quarantine/15 text-quarantine hover:bg-quarantine/25 border-quarantine/30",
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title}
      className={cx("inline-flex items-center justify-center gap-2 rounded-lg border transition-colors disabled:cursor-not-allowed disabled:opacity-45",
        size === "sm" ? "h-8 px-2.5 text-[12.5px]" : "h-9 px-3.5 text-[13px]", v)}>
      {icon}
      {children}
    </button>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: ReactNode; badge?: ReactNode }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="mb-6 flex gap-1 border-b border-line">
      {tabs.map((t) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={cx("relative -mb-px flex items-center gap-2 border-b-2 px-3.5 pb-2.5 pt-1 text-[13.5px] transition-colors",
            value === t.id ? "border-brand font-medium text-ink" : "border-transparent text-ink-3 hover:text-ink-2")}>
          {t.label}
          {t.badge}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "accept" | "review" | "quarantine" }) {
  return (
    <div>
      <div className="label-caps">{label}</div>
      <div className={cx("mt-1.5 text-[22px] font-semibold tabular-nums tracking-tight", tone === "accept" && "text-accept", tone === "review" && "text-review", tone === "quarantine" && "text-quarantine")}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-ink-3">{sub}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- states */

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-16 text-sm text-ink-3">
      <LoaderCircle size={16} className="animate-spin" /> {label}…
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: { message: string } | null; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-quarantine/30 bg-quarantine/5 p-5">
      <TriangleAlert size={18} className="mt-0.5 text-quarantine" />
      <div>
        <div className="font-medium text-ink">Could not load this view</div>
        <div className="mt-1 text-sm text-ink-2">{error?.message ?? "Unknown error"}</div>
        {onRetry && <div className="mt-3"><Button size="sm" onClick={onRetry}>Retry</Button></div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-line px-6 py-12 text-center">
      {icon && <div className="mb-3 text-ink-3">{icon}</div>}
      <div className="font-medium text-ink">{title}</div>
      {children && <div className="mt-1.5 max-w-md text-sm text-ink-3">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function UnavailableCard({ checkId, name, reason, fallback, requirement }: { checkId: string; name: string; reason: string; fallback?: string | null; requirement?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gap/50 bg-raised/40 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[13px] font-medium text-ink-2">
          <CircleDashed size={14} className="text-gap" /> {name}
        </div>
        <DispositionBadge value={null} unavailable />
      </div>
      <div className="mt-1 font-mono text-[11px] text-ink-3">{checkId} {requirement && <>· {requirement}</>}</div>
      <p className="mt-2 text-[13px] text-ink-2">Could not run: {reason}.</p>
      <p className="mt-1 text-[12.5px] text-ink-3">{fallback ? <>Fallback used: <span className="font-mono text-ink-2">{fallback}</span></> : "No fallback available; this aspect is not assessed."}</p>
    </div>
  );
}

/* ------------------------------------------------------------ primitives */

export function DigestText({ value, n = 10 }: { value: string | null | undefined; n?: number }) {
  const [copied, setCopied] = useState(false);
  if (!value) return <span className="text-ink-3">—</span>;
  return (
    <button type="button" title={value}
      onClick={(e) => { e.stopPropagation(); navigator.clipboard?.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
      className="group inline-flex items-center gap-1.5 rounded font-mono text-[11.5px] text-ink-2 hover:text-ink">
      <span className="text-ink-3">sha256:</span>{shortDigest(value, n)}
      {copied ? <Check size={11} className="text-accept" /> : <Copy size={11} className="opacity-0 transition-opacity group-hover:opacity-60" />}
    </button>
  );
}

export function Thumb({ id, size = 88, overlay, onClick, label }: { id: string; size?: number; overlay?: { x: number; y: number; w: number; h: number; image_size: number } | null; onClick?: () => void; label?: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="group relative shrink-0 overflow-hidden rounded-md border border-line bg-raised text-left" style={{ width: size }}>
      <img src={imageUrl(id, 224)} alt={id} loading="lazy" className="block aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-[1.04]" />
      {overlay && (
        <span className="pointer-events-none absolute border-2 border-quarantine shadow-[0_0_0_2px_rgba(0,0,0,0.35)]"
          style={{ left: `${(overlay.x / overlay.image_size) * 100 - 3}%`, top: `${(overlay.y / overlay.image_size) * 100 - 3}%`, width: `${(overlay.w / overlay.image_size) * 100 + 6}%`, height: `${(overlay.h / overlay.image_size) * 100 + 6}%` }} />
      )}
      {label !== undefined && <span className="block truncate px-1.5 py-1 font-mono text-[10px] text-ink-3">{label}</span>}
    </button>
  );
}

/** Canvas overlay: draws the image and marks trigger / box locations (A12.5 CanvasOverlay). */
export function CanvasOverlay({ id, boxes = [], size = 360 }: { id: string; boxes?: { x: number; y: number; w: number; h: number; label?: string }[]; size?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const img = new Image();
    img.src = imageUrl(id, 448);
    img.onload = () => {
      const c = ref.current;
      if (!c) return;
      const ctx = c.getContext("2d")!;
      const dpr = window.devicePixelRatio || 1;
      c.width = size * dpr;
      c.height = size * dpr;
      ctx.scale(dpr, dpr);
      ctx.drawImage(img, 0, 0, size, size);
      const k = size / 224;
      boxes.forEach((b) => {
        ctx.strokeStyle = "#ef5a5f";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.strokeRect(b.x * k - 4, b.y * k - 4, b.w * k + 8, b.h * k + 8);
        if (b.label) {
          ctx.setLineDash([]);
          ctx.font = "600 11px 'IBM Plex Sans'";
          const w = ctx.measureText(b.label).width + 10;
          const lx = Math.max(0, Math.min(size - w, b.x * k + b.w * k + 4 - w));
          const ly = b.y * k - 26;
          ctx.fillStyle = "#ef5a5f";
          ctx.fillRect(lx, ly, w, 18);
          ctx.fillStyle = "#1a0405";
          ctx.fillText(b.label, lx + 5, ly + 13);
        }
      });
    };
  }, [id, size, JSON.stringify(boxes)]);
  return <canvas ref={ref} style={{ width: size, height: size }} className="rounded-lg border border-line" />;
}

export function VerificationChecklist({ steps }: { steps: VerificationStep[] }) {
  return (
    <ol className="divide-y divide-line-soft overflow-hidden rounded-lg border border-line">
      {steps.map((s) => (
        <li key={s.step} className={cx("flex items-start gap-3 px-3.5 py-2.5", s.passed === false && "bg-quarantine/[0.06]")}>
          <span className="mt-0.5">
            {s.passed === true && <CircleCheck size={16} className="text-accept" />}
            {s.passed === false && <CircleX size={16} className="text-quarantine" />}
            {s.passed === null && <CircleHelp size={16} className="text-gap" />}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[13px] font-medium text-ink">{s.step}</span>
              <span className={cx("text-[10.5px] font-semibold tracking-wider", s.passed === true ? "text-accept" : s.passed === false ? "text-quarantine" : "text-gap")}>
                {s.passed === true ? "PASS" : s.passed === false ? "FAIL" : "NOT PERFORMED"}
              </span>
            </div>
            <div className="mt-0.5 break-all text-[12.5px] text-ink-3">{s.detail}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function KeyValue({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(120px,auto)_1fr] gap-x-6 gap-y-2.5 text-[13px]">
      {items.map(([k, v], i) => (
        <div key={i} className="contents">
          <dt className="text-ink-3">{k}</dt>
          <dd className="min-w-0 text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function RiskBar({ value, max = 100 }: { value: number; max?: number }) {
  const tone = value >= 70 ? "bg-quarantine" : value >= 35 ? "bg-review" : "bg-accept";
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-line">
        <div className={cx("h-full rounded-full", tone)} style={{ width: `${(value / max) * 100}%` }} />
      </div>
      <span className="w-9 text-right font-mono text-[12.5px] text-ink">{value.toFixed(1)}</span>
    </div>
  );
}

export function Notice({ tone = "info", children, icon }: { tone?: "info" | "warn" | "danger" | "ok"; children: ReactNode; icon?: ReactNode }) {
  const t = {
    info: "border-brand/25 bg-brand/[0.06] text-ink-2",
    warn: "border-review/30 bg-review/[0.07] text-ink-2",
    danger: "border-quarantine/30 bg-quarantine/[0.07] text-ink-2",
    ok: "border-accept/30 bg-accept/[0.07] text-ink-2",
  }[tone];
  return <div className={cx("flex items-start gap-3 rounded-lg border px-4 py-3 text-[13px]", t)}>{icon}<div className="min-w-0 flex-1">{children}</div></div>;
}
