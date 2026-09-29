import { CircleCheck, CircleDashed, CircleX } from "lucide-react";
import type { Assessment, Finding } from "../../lib/api";
import { fmtValue, humanKey } from "../../lib/format";
import { AttentionList, VerdictCard } from "../../components/assessment";
import { Card, cx, DigestText, KeyValue, RequirementTag, SectionTitle, StatusPill } from "../../components/ui";

export default function Overview({ asm, findings }: { asm: Assessment; findings: Finding[] }) {
  const attention = findings.filter((f) => f.unresolved);
  return (
    <div className="space-y-6">
      {asm.summary && <VerdictCard asm={asm} summary={asm.summary} compact />}
      <Card>
        <SectionTitle title="Needs attention" hint="Unresolved REVIEW / QUARANTINE findings in this assessment." />
        <AttentionList items={attention.slice(0, 14)} total={attention.length} unresolved={attention.length} />
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card>
          <SectionTitle title="Checks executed" hint="Every check appears here — including those that could not run, with the reason and any fallback." />
          <div className="space-y-5">
            {asm.module_runs.map((m) => (
              <div key={m.module}>
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-mono text-[11px] text-ink-3">{m.module}</span>
                  <span className="text-[13px] font-medium text-ink">{m.name}</span>
                  <StatusPill status={m.status} />
                </div>
                <div className="overflow-hidden rounded-lg border border-line">
                  {m.checks.map((c, i) => (
                    <div key={c.check_id} className={cx("grid grid-cols-[18px_1fr_auto_auto] items-center gap-3 px-3.5 py-2", i > 0 && "border-t border-line-soft", c.status !== "COMPLETED" && "bg-raised/40")}>
                      {c.status === "COMPLETED" ? <CircleCheck size={14} className="text-accept/80" /> : c.status === "ERROR" ? <CircleX size={14} className="text-quarantine" /> : <CircleDashed size={14} className="text-gap" />}
                      <div className="min-w-0">
                        <div className="text-[12.5px] text-ink">{c.name} <span className="ml-1 font-mono text-[10.5px] text-ink-3">{c.check_id}</span></div>
                        {c.status !== "COMPLETED" && <div className="text-[11.5px] text-gap">Unavailable: {c.message}{c.fallback_used && <> · fallback <span className="font-mono">{c.fallback_used}</span></>}</div>}
                      </div>
                      <RequirementTag id={c.requirement} />
                      <span className={cx("w-16 text-right font-mono text-[11.5px]", c.findings ? "text-review" : "text-ink-3")}>{c.status === "COMPLETED" ? `${c.findings} flag${c.findings === 1 ? "" : "s"}` : "—"}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <div className="space-y-6">
          <Card>
            <SectionTitle title="Inputs" hint="Digests bind this assessment to the exact artefacts assessed." />
            <div className="space-y-3">
              {asm.inputs_detail.map((i) => (
                <div key={i.id} className="rounded-lg border border-line bg-raised/40 px-3.5 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13px] font-medium text-ink">{i.name}</span>
                    <span className="text-[10.5px] uppercase tracking-wider text-ink-3">{i.type.replace("_", " ")}</span>
                  </div>
                  <div className="mt-1"><DigestText value={i.digest} /></div>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <SectionTitle title="Configuration snapshot" hint="Recorded so the run can be reproduced." />
            <KeyValue items={Object.entries(asm.config_snapshot).map(([k, v]) => [humanKey(k), typeof v === "string" && v.startsWith("sha256:") ? <DigestText value={v} /> : <span className="font-mono text-[12.5px]">{fmtValue(v)}</span>])} />
          </Card>
        </div>
      </div>
    </div>
  );
}
