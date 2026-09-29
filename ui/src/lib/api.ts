// Typed client for the local AURA-CV API. Same-origin only; no remote hosts.

export type Disposition = "ACCEPT" | "REVIEW" | "QUARANTINE";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ModuleId = "M1" | "M2" | "M3" | "M4" | "M5";

export interface User {
  id: string;
  username: string;
  role: "ADMIN" | "ANALYST";
  display: string;
}

export interface AssetRef {
  type: string;
  id: string;
  digest?: string | null;
}

export interface VerificationStep {
  step: string;
  passed: boolean | null;
  detail: string;
}

export interface Finding {
  id: string;
  assessment_id: string;
  assessment_name?: string;
  module: ModuleId;
  check_id: string;
  check_name: string;
  check_description: string;
  requirement: string;
  created_at: string;
  status: "FLAGGED" | "UNAVAILABLE";
  reason: string;
  evidence: {
    metrics: Record<string, unknown>;
    thresholds: Record<string, unknown>;
    sample_ids: string[];
    artefact_ids: string[];
    verification_steps?: VerificationStep[] | null;
    [k: string]: unknown;
  };
  confidence: number;
  severity: Severity;
  affected_asset: AssetRef;
  asset_label: string;
  recommended_disposition: Disposition;
  effective_disposition: Disposition;
  unresolved: boolean;
  limitations: string[];
  decision_count: number;
  latest_decision: DecisionT | null;
  decisions?: DecisionT[];
}

export interface DecisionT {
  id: string;
  finding_id: string;
  analyst_id: string;
  analyst_name?: string;
  decision: Disposition;
  justification: string;
  decided_at: string;
}

export interface Tile {
  key: string;
  label: string;
  assessed: boolean;
  module?: string;
  disposition?: Disposition;
  confidence?: number | null;
  findings?: number;
  coverage_gaps?: string[];
  asset?: { id: string; name: string } | null;
  worst?: { id: string; name: string; disposition: Disposition };
  note?: string;
  top_issue?: string | null;
  top_reason?: string | null;
}

export interface Summary {
  assessment_id: string;
  overall_disposition: Disposition | null;
  tiles: Tile[];
  counts: {
    total: number;
    by_effective_disposition: Record<Disposition, number>;
    by_recommended_disposition: Record<Disposition, number>;
    by_severity: Record<Severity, number>;
    by_module: Record<string, number>;
    unavailable: number;
  };
  unresolved: number;
}

export interface CheckRunT {
  check_id: string;
  name: string;
  requirement: string;
  status: "COMPLETED" | "UNAVAILABLE" | "ERROR";
  duration_ms: number;
  message: string;
  fallback_used: string | null;
  findings: number;
  parameters: Record<string, unknown>;
}

export interface Assessment {
  id: string;
  name: string;
  status: string;
  created_at: string;
  created_by: string;
  created_by_name: string;
  started_at: string | null;
  finished_at: string | null;
  modules: string[];
  inputs: Record<string, string>;
  inputs_detail: { role: string; id: string; name: string; type: string; digest?: string }[];
  access_level_used: string;
  detected_access_level: string | null;
  access_level_override: string | null;
  seed: number;
  config_snapshot: Record<string, unknown>;
  module_runs: { module: string; name: string; status: string; progress: number; checks: CheckRunT[] }[];
  summary: Summary | null;
  report: { id: string; status: string } | null;
  error: string | null;
}

export interface AssessmentRow {
  id: string;
  name: string;
  status: string;
  created_at: string;
  finished_at: string | null;
  created_by_name: string;
  modules: string[];
  overall_disposition: Disposition | null;
  unresolved: number;
  findings: number;
  report_status: string | null;
  access_level_used: string;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    window.dispatchEvent(new CustomEvent("aura:unauthenticated"));
  }
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = data?.error ?? {};
    throw new ApiError(res.status, err.code ?? "ERROR", err.message ?? res.statusText, err.details ?? {});
  }
  return data as T;
}

export const api = {
  get: <T,>(p: string) => request<T>("GET", p),
  post: <T,>(p: string, b: unknown = {}) => request<T>("POST", p, b),
};

export const imageUrl = (sampleId: string, size = 224) => `/api/v1/images/${sampleId}.png?size=${size}`;
