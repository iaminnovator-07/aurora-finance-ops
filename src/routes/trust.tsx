import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, TrustRing } from "@/components/ui-bits";
import { CheckCircle2, XCircle, Shield, FileSignature, Repeat, Network } from "lucide-react";
import { useEmails, useTrustCheck } from "@/lib/api/hooks";

export const Route = createFileRoute("/trust")({ component: Trust });

function Trust() {
  const { data: emails } = useEmails();
  const firstEmail = emails?.items?.[0];
  const { data: trust, isLoading } = useTrustCheck(firstEmail?.id);

  const checks = trust ? [
    { label: "SPF", ok: trust.checks?.spf === "pass" || trust.checks?.spf === "pass_strict", detail: String(trust.checks?.spf ?? "checking") },
    { label: "DKIM", ok: trust.checks?.dkim === "pass", detail: String(trust.checks?.dkim ?? "checking") },
    { label: "DMARC", ok: String(trust.checks?.dmarc ?? "").includes("pass"), detail: String(trust.checks?.dmarc ?? "checking") },
    { label: "Identity Score", ok: trust.identity_score >= 70, detail: `${trust.identity_score} / 100`, icon: FileSignature },
    { label: "Duplicate Detection", ok: trust.duplicate_score >= 80, detail: `Duplicate score: ${trust.duplicate_score}`, icon: Repeat },
    { label: "Vendor Reputation", ok: trust.vendor_reputation_score >= 70, detail: `Reputation: ${trust.vendor_reputation_score}`, icon: Network },
  ] : [];

  const timeline = (trust?.reasoning_timeline ?? []).map((e, i) => ({
    t: e.step ?? `step ${i}`,
    w: e.detail ?? e.w ?? "Check",
    d: e.score != null ? `${e.score} pts` : (e.d ?? ""),
    tone: (e.score ?? 0) >= 70 ? "success" : (e.score ?? 0) >= 50 ? "warning" : "primary",
  }));

  return (
    <AppLayout>
      <PageHeader title="Trust Engine" subtitle="How Aurora scores every invoice for fraud and risk." />

      {isLoading && <div className="text-sm text-muted-foreground mb-4">Computing trust score…</div>}

      <div className="grid lg:grid-cols-[360px_1fr] gap-4 mb-4">
        <Card className="grid place-items-center text-center">
          <TrustRing score={Math.round(trust?.overall_score ?? 0)} size={180} />
          <div className="mt-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Risk level</div>
            <div className={`text-2xl font-bold capitalize ${trust?.risk_level === "low" ? "text-success" : trust?.risk_level === "medium" ? "text-warning" : "text-destructive"}`}>
              {trust?.risk_level ?? "—"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">{firstEmail?.subject ?? "Select email in Inbox"}</div>
          </div>
          <div className="mt-4 w-full grid grid-cols-3 gap-2 text-[11px]">
            <div className="p-2 rounded-lg bg-success/10"><div className="font-bold text-success">{Math.round(trust?.overall_score ?? 0)}</div><div className="text-muted-foreground">Trust</div></div>
            <div className="p-2 rounded-lg bg-primary/10"><div className="font-bold text-primary">{Math.round(trust?.identity_score ?? 0)}</div><div className="text-muted-foreground">Identity</div></div>
            <div className="p-2 rounded-lg bg-[color:var(--ai)]/10"><div className="font-bold text-[color:var(--ai)]">{Math.round(trust?.content_score ?? 0)}</div><div className="text-muted-foreground">Content</div></div>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Shield className="h-4 w-4 text-primary" /> Verification Checks</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {checks.map((c) => {
              const Icon = c.icon ?? CheckCircle2;
              return (
                <div key={c.label} className="p-3 rounded-xl border border-border bg-background/30 flex items-start gap-3">
                  <div className={`h-9 w-9 rounded-lg grid place-items-center shrink-0 ${c.ok ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"}`}>
                    {c.ok ? <Icon className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold flex items-center gap-1">{c.label} {c.ok && <Badge tone="success">Pass</Badge>}</div>
                    <div className="text-[11px] text-muted-foreground truncate">{c.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold mb-4">Reasoning Timeline</h3>
        <div className="relative pl-6">
          <div className="absolute left-2 top-1 bottom-1 w-px bg-border" />
          {timeline.map((e, i) => (
            <div key={i} className="relative mb-4 last:mb-0">
              <div className={`absolute -left-[18px] top-1 h-3 w-3 rounded-full ring-4 ring-background ${
                e.tone === "success" ? "bg-success" : e.tone === "warning" ? "bg-warning" : "bg-primary"
              }`} />
              <div className="flex items-baseline justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">{e.w}</div>
                  <div className="text-[11px] text-muted-foreground">{e.t}</div>
                </div>
                <Badge tone={e.tone as "success" | "warning" | "primary"}>{e.d}</Badge>
              </div>
            </div>
          ))}
          {timeline.length === 0 && <p className="text-sm text-muted-foreground">Process an email to see trust reasoning.</p>}
        </div>
      </Card>
    </AppLayout>
  );
}
