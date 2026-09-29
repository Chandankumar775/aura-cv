export function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  const d = Math.round(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
}

export function pct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function shortDigest(d: string | null | undefined, n = 10): string {
  if (!d) return "—";
  const hex = d.startsWith("sha256:") ? d.slice(7) : d;
  return `${hex.slice(0, n)}…${hex.slice(-4)}`;
}

export const moduleNames: Record<string, string> = {
  M1: "Data integrity",
  M2: "Model integrity",
  M3: "Inference provenance",
  M4: "Distribution shift",
  M5: "Governance",
};

export const verdictText: Record<string, string> = {
  PROBABLE_OPERATIONAL_DRIFT: "Probable operational drift",
  SUSPICIOUS_MANIPULATION: "Suspicious manipulation",
  INCONCLUSIVE: "Inconclusive",
  NO_MATERIAL_SHIFT: "No material shift",
};

export function humanKey(k: string): string {
  return k.replace(/_/g, " ").replace(/\b(d|p|js|mmd2|ece|l1)\b/g, (m) => m.toUpperCase());
}

export function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString("en-IN");
    if (Math.abs(v) < 0.001 && v !== 0) return v.toExponential(1);
    return v.toFixed(Math.abs(v) < 1 ? 3 : 2);
  }
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return v.map(fmtValue).join(", ");
  if (typeof v === "object") return Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k}: ${fmtValue(x)}`).join(" · ");
  return String(v);
}
