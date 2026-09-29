import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CircleAlert, CircleCheck, CircleHelp, CircleX, FlaskConical, LoaderCircle, Play } from "lucide-react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { useApp } from "../lib/app";
import { dateTime, fmtValue, humanKey, relTime } from "../lib/format";
import { Button, Card, cx, DigestText, DispositionBadge, ErrorState, KeyValue, Loading, Notice, PageHeader, RequirementTag, SectionTitle, StatusPill, Tabs } from "../components/ui";

/* ------------------------------------------------------------------ Assets */

const ASSET_TABS = [
  { id: "dataset", label: "Datasets" }, { id: "model", label: "Models" }, { id: "record_stream", label: "Record streams" },
  { id: "input_batch", label: "Input batches" }, { id: "reference", label: "References" },
] as const;

export function Assets() {
  const { type = "dataset" } = useParams();
  const nav = useNavigate();
  const { data, loading, error } = useApi<{ items: any[] }>(`/assets?type=${type}`);
  return (
    <div>
      <PageHeader title="Registered assets" sub="Everything assessed is registered first, pinned by SHA-256 digest. Registration is written to the audit log." />
      <Tabs tabs={ASSET_TABS.map((t) => ({ id: t.id, label: t.label }))} value={type as any} onChange={(t) => nav(`/assets/${t}`)} />
      {loading ? <Loading /> : error ? <ErrorState error={error} /> : (
        <div className="grid gap-4 xl:grid-cols-2">
          {data!.items.map((a) => (
            <Card key={a.id}>
              <div className="flex items-start justify-between gap-3">
                <div><div className="text-[15px] font-medium text-ink">{a.name}</div><div className="mt-0.5 font-mono text-[11.5px] text-ink-3">{a.id}</div></div>
                <span className="rounded border border-line bg-raised px-2 py-0.5 font-mono text-[11px] uppercase text-ink-2">{a.format}</span>
              </div>
              <div className="mt-4">
                <KeyValue items={[
                  ["Digest", <DigestText value={a.digest} />],
                  ...(a.type === "dataset" ? [["Images", a.n_images.toLocaleString("en-IN")], ["Classes", a.class_names.join(", ")], ["Contributor metadata", a.has_contributor_metadata ? `yes · ${a.contributors.length} contributors` : <span className="text-review">not supplied</span>], ["Sanity issues", a.validation_summary.sanity_issues]] : []),
                  ...(a.type === "model" ? [["Task", a.task], ["Supplier", a.supplier], ["Detected access", <span className="font-mono">{a.detected_access_level}</span>], ["Registered digest", a.weight_digest === a.registered_digest ? <span className="text-accept">matches supplied weights</span> : <span className="text-quarantine">differs from supplied weights</span>], ["Claimed accuracy", `${(a.claimed_accuracy * 100).toFixed(1)}%`]] : []),
                  ...(a.type === "record_stream" ? [["Stream id", <span className="font-mono">{a.stream_id}</span>], ["Records", a.n_records], ["Signer keys", <span className="font-mono text-[12px]">{a.signer_key_ids?.join(", ")}</span>]] : []),
                  ...(a.type === "input_batch" ? [["Images", a.n_images], ["Acquisition metadata", Object.keys(a.acquisition_metadata).length ? fmtValue(a.acquisition_metadata) : <span className="text-review">none supplied</span>]] : []),
                  ...(a.type === "reference" ? [["Images", a.n_images.toLocaleString("en-IN")], ["Default", a.is_default ? "yes" : "no"], ["Embeddings", <DigestText value={a.embedding_digest} n={8} />], ["Calibration set", <DigestText value={a.calibration_set_digest} n={8} />]] : []),
                  ["Registered", `${dateTime(a.registered_at)} by ${a.registered_by}`],
                ] as any} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- Attack Lab */

export function AttackLab() {
  const nav = useNavigate();
  const sc = useApi<{ items: any[] }>("/attack-lab/scenarios");
  const runs = useApi<{ items: any[] }>("/attack-lab/runs");
  const [sel, setSel] = useState<any | null>(null);
  const [seed, setSeed] = useState(1337);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<any | null>(null);
  const { toast } = useApp();
  if (sc.loading) return <Loading />;
  if (sc.error) return <ErrorState error={sc.error} />;
  const groups = [...new Set(sc.data!.items.map((s) => s.group))];
  const run = async () => {
    setBusy(true);
    const r = await api.post("/attack-lab/runs", { scenario_id: sel.id, seed });
    setLast(r);
    setBusy(false);
    runs.reload();
    toast({ tone: "info", title: `Scenario ${sel.id} generated`, detail: "Ground-truth manifest stored apart from the detectors." });
  };
  const assessLink = (ids: string[]) => {
    const f: Record<string, string> = { ds: "dataset_id", mdl: "model_id", rs: "record_stream_id", ib: "input_batch_id" };
    const q = new URLSearchParams();
    ids.forEach((i) => q.set(f[i.split("_")[0]], i));
    if (ids.some((i) => i.startsWith("ib_"))) q.set("reference_id", "ref_plains_summer");
    return `/assessments/new?${q}`;
  };
  return (
    <div>
      <PageHeader title="Reproducible attack scenarios"
        sub="Generate poisoning, backdoor, substitution, tampering and shift scenarios from a seed. Ground-truth manifests are kept apart from detectors and read only by the evaluation harness." />
      <Notice tone="warn" icon={<FlaskConical size={16} className="mt-0.5 text-review" />}>Test-asset creation only. Model scenario M1 fine-tunes a <b>clean</b> model to create a backdoored test model; the contributed model is never retrained during assessment (R-CON-4).</Notice>
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <div className="space-y-5">
          {groups.map((g) => (
            <div key={g}>
              <div className="label-caps mb-2">{g}</div>
              <div className="grid gap-2 md:grid-cols-2">
                {sc.data!.items.filter((s) => s.group === g).map((s) => (
                  <button key={s.id} onClick={() => { setSel(s); setLast(null); }}
                    className={cx("rounded-lg border p-3 text-left transition-colors", sel?.id === s.id ? "border-brand/60 bg-brand/[0.07]" : "border-line bg-panel hover:bg-raised")}>
                    <div className="flex items-center gap-2"><span className="rounded bg-raised px-1.5 font-mono text-[11px] text-ink-2">{s.id}</span><span className="text-[13px] font-medium text-ink">{s.name}</span></div>
                    <div className="mt-1 text-[12px] text-ink-3">{s.description}</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="space-y-5">
          <Card>
            {!sel ? <div className="text-[13px] text-ink-3">Select a scenario to configure and generate it.</div> : (
              <>
                <div className="label-caps">Scenario {sel.id}</div>
                <div className="mt-1 text-[17px] font-semibold text-ink">{sel.name}</div>
                <p className="mt-1 text-[12.5px] text-ink-3">{sel.description}</p>
                <div className="mt-4">
                  <KeyValue items={[...Object.entries(sel.params).map(([k, v]) => [humanKey(k), <span className="font-mono text-[12.5px]">{fmtValue(v)}</span>] as [string, React.ReactNode]),
                    ["Seed", <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="h-8 w-28 rounded-md border border-line bg-canvas px-2 font-mono text-[12.5px] text-ink" />]]} />
                </div>
                <div className="mt-5"><Button variant="primary" icon={busy ? <LoaderCircle size={14} className="animate-spin" /> : <Play size={14} />} onClick={run} disabled={busy}>{busy ? "Generating…" : "Generate"}</Button></div>
                {last && (
                  <div className="mt-5 rounded-lg border border-accept/30 bg-accept/[0.06] p-3.5 text-[12.5px]">
                    <div className="font-medium text-ink">Run {last.id} complete</div>
                    <div className="mt-1 text-ink-3">Outputs: {last.output_asset_ids.join(", ") || "copy of audit log"} · manifest <DigestText value={last.manifest_digest} n={8} /></div>
                    {last.output_asset_ids.length > 0 && <div className="mt-3"><Button size="sm" onClick={() => nav(assessLink(last.output_asset_ids))}>Assess these assets →</Button></div>}
                  </div>
                )}
              </>
            )}
          </Card>
          <Card>
            <SectionTitle title="Previous runs" />
            <div className="space-y-2">
              {runs.data?.items.map((r) => (
                <div key={r.id} className="flex items-center justify-between rounded-lg border border-line bg-raised/40 px-3 py-2 text-[12.5px]">
                  <div><span className="rounded bg-canvas px-1.5 font-mono text-[11px] text-ink-2">{r.scenario_id}</span> <span className="ml-1 font-mono text-ink-3">seed {r.seed}</span></div>
                  <div className="text-ink-3">{relTime(r.created_at)}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Settings */

export function Settings() {
  const { section = "users" } = useParams();
  const nav = useNavigate();
  const users = useApi<{ items: any[] }>(section === "users" ? "/users" : null);
  const keys = useApi<{ items: any[] }>(section === "keys" ? "/keys" : null);
  const policy = useApi<any>(section === "policy" ? "/config/policy" : null);
  const thresholds = useApi<{ items: any[] }>(section === "thresholds" ? "/config/thresholds" : null);
  const selfcheck = useApi<{ items: any[] }>(section === "system" ? "/system/selfcheck" : null);
  const bands = ["LOW", "MEDIUM", "HIGH"];
  return (
    <div>
      <PageHeader title="Settings" sub="Every change to users, keys, policy or thresholds is recorded in the audit log." />
      <Tabs tabs={[{ id: "users", label: "Users" }, { id: "keys", label: "Keys" }, { id: "policy", label: "Disposition policy" }, { id: "thresholds", label: "Thresholds" }, { id: "system", label: "Self-check" }]} value={section as any} onChange={(s) => nav(`/settings/${s}`)} />
      {section === "users" && users.data && (
        <Card pad={false}><table className="w-full text-[13px]"><thead><tr className="border-b border-line text-left">{["User", "Role", "Created", "Status"].map((h) => <th key={h} className="label-caps px-4 py-2.5">{h}</th>)}</tr></thead>
          <tbody>{users.data.items.map((u) => <tr key={u.id} className="border-b border-line-soft last:border-0"><td className="px-4 py-3"><div className="text-ink">{u.display}</div><div className="font-mono text-[11.5px] text-ink-3">{u.username}</div></td><td className="px-4 py-3 font-mono text-[12px]">{u.role}</td><td className="px-4 py-3 text-ink-2">{dateTime(u.created_at)}</td><td className="px-4 py-3"><StatusPill status={u.disabled ? "CANCELLED" : "COMPLETED"} /></td></tr>)}</tbody></table></Card>
      )}
      {section === "keys" && keys.data && (
        <div className="grid gap-4 md:grid-cols-3">
          {keys.data.items.map((k) => (
            <Card key={k.key_id}>
              <div className="flex items-center justify-between"><span className="label-caps">{k.purpose} key</span><StatusPill status={k.retired_at ? "CANCELLED" : "COMPLETED"} /></div>
              <div className="mt-2 font-mono text-[12.5px] text-ink">{k.key_id}</div>
              <div className="mt-3 break-all font-mono text-[11px] text-ink-3">{k.public_key}</div>
              <div className="mt-3 text-[12px] text-ink-3">{k.algorithm} · created {dateTime(k.created_at)}</div>
            </Card>
          ))}
        </div>
      )}
      {section === "policy" && policy.data && (
        <Card>
          <SectionTitle title="Severity × confidence → recommended disposition" hint={`Version ${policy.data.version} · confidence bands: low < ${policy.data.low_below}, high > ${policy.data.high_above}`} />
          <table className="text-[13px]"><thead><tr><th />{bands.map((b) => <th key={b} className="label-caps px-5 py-2 text-center">{b} confidence</th>)}</tr></thead>
            <tbody>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => <tr key={s}><td className="label-caps pr-5">{s}</td>{bands.map((b) => <td key={b} className="px-5 py-2 text-center"><DispositionBadge value={policy.data.matrix[s][b]} size="md" /></td>)}</tr>)}</tbody></table>
          <div className="mt-5 text-[13px] text-ink-2">Hard overrides (always): {Object.entries(policy.data.hard_overrides).map(([k, v]) => `${humanKey(k.toLowerCase())} → ${v}`).join(" · ")}. UNAVAILABLE checks → {policy.data.unavailable_disposition}, never ACCEPT.</div>
          <div className="mt-2"><DigestText value={policy.data.digest} /></div>
        </Card>
      )}
      {section === "thresholds" && thresholds.data && (
        <Card pad={false}><table className="w-full text-[12.5px]"><thead><tr className="border-b border-line text-left">{["Check", "Module", "Min access", "Parameters", ""].map((h) => <th key={h} className="label-caps px-4 py-2.5">{h}</th>)}</tr></thead>
          <tbody>{thresholds.data.items.map((t) => <tr key={t.check_id} className="border-b border-line-soft last:border-0"><td className="px-4 py-2.5"><div className="text-ink">{t.name}</div><div className="font-mono text-[11px] text-ink-3">{t.check_id}</div></td><td className="px-4 py-2.5 font-mono">{t.module}</td><td className="px-4 py-2.5 font-mono">{t.requires_access}</td><td className="px-4 py-2.5 font-mono text-[11.5px] text-ink-2">{Object.keys(t.parameters).length ? fmtValue(t.parameters) : "—"}</td><td className="px-4 py-2.5"><RequirementTag id={t.requirement} /></td></tr>)}</tbody></table></Card>
      )}
      {section === "system" && (selfcheck.loading ? <Loading /> : selfcheck.data && (
        <Card pad={false}>
          {selfcheck.data.items.map((i) => (
            <div key={i.id} className="flex items-start gap-3 border-b border-line-soft px-5 py-3 last:border-0">
              {i.state === "PASS" ? <CircleCheck size={16} className="mt-0.5 text-accept" /> : i.state === "WARN" ? <CircleAlert size={16} className="mt-0.5 text-review" /> : <CircleX size={16} className="mt-0.5 text-quarantine" />}
              <div className="flex-1"><div className="font-mono text-[12.5px] text-ink">{i.id}</div><div className="text-[12.5px] text-ink-3">{i.detail}</div></div>
              <span className={cx("text-[11px] font-semibold tracking-wider", i.state === "PASS" ? "text-accept" : i.state === "WARN" ? "text-review" : "text-quarantine")}>{i.state}</span>
            </div>
          ))}
        </Card>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- Coverage */

export function Coverage() {
  const { data, loading } = useApi<Record<string, string[]>>("/coverage");
  if (loading || !data) return <Loading />;
  const sections: [string, string, React.ReactNode, string][] = [
    ["supported", "Supported", <CircleCheck size={16} className="text-accept" />, "border-accept/25"],
    ["partial", "Partially supported", <CircleHelp size={16} className="text-review" />, "border-review/25"],
    ["unsupported", "Not supported", <CircleX size={16} className="text-quarantine" />, "border-quarantine/30"],
    ["assumptions", "Assumptions", <CircleAlert size={16} className="text-brand" />, "border-brand/25"],
    ["known_limitations", "Known limitations", <CircleAlert size={16} className="text-gap" />, "border-line"],
  ];
  return (
    <div>
      <PageHeader title="Coverage & limitations"
        sub="What AURA-CV can and cannot detect, stated explicitly. This statement is embedded in every exported report so no result can be read without its limits." />
      <div className="grid gap-5 xl:grid-cols-2">
        {sections.map(([k, t, icon, border]) => (
          <section key={k} className={cx("glass rounded-2xl p-5", border, k === "supported" && "xl:row-span-2")}>
            <h2 className="mb-3 flex items-center gap-2 text-[15px] font-semibold text-ink">{icon}{t}</h2>
            <ul className="space-y-2 text-[13px] text-ink-2">{data[k].map((x) => <li key={x} className="flex gap-2.5"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-3" />{x}</li>)}</ul>
          </section>
        ))}
      </div>
    </div>
  );
}
