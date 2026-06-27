import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { ConfidenceBar, TrustRing } from "@/components/ui-bits";
import { CheckCircle2, XCircle, MessageSquare, Download, ZoomIn, ZoomOut, FileText, AlertTriangle, Eye, History } from "lucide-react";
import { useApprovals, useApprovalAction } from "@/lib/api/hooks";
import { formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/approvals")({ component: Approvals });

function recommendationTone(rec: string | null | undefined): "success" | "destructive" | "warning" | "default" {
  const r = (rec ?? "").toLowerCase();
  if (r.includes("approve")) return "success";
  if (r.includes("reject")) return "destructive";
  if (r.includes("review")) return "warning";
  return "default";
}

function Approvals() {
  const { data, isLoading } = useApprovals();
  const action = useApprovalAction();
  const approval = data?.items?.[0];

  const invoiceLabel = approval?.invoice_number ?? "—";
  const trust = Math.round(approval?.trust_score ?? 0);
  const confidence = Math.round(approval?.confidence_score ?? 0);
  const recommendation = approval?.ai_recommendation ?? "Review";
  const recTone = recommendationTone(approval?.ai_recommendation);

  const fields = approval ? [
    { label: "Invoice #", value: approval.invoice_number ?? "—", conf: confidence },
    { label: "Reason", value: approval.reason, conf: confidence },
    { label: "Risk Level", value: approval.risk_level, conf: confidence },
    { label: "Trust Score", value: String(trust), conf: trust },
    { label: "Confidence", value: `${confidence}%`, conf: confidence },
    { label: "Status", value: approval.approval_status.replace(/_/g, " "), conf: confidence },
  ] : [];

  const handleAction = (act: "approve" | "reject" | "request-review") => {
    if (!approval) return;
    action.mutate({ id: approval.id, action: act });
  };

  return (
    <AppLayout>
      <PageHeader
        title={isLoading ? "Approval Queue" : `Approval — ${invoiceLabel}`}
        subtitle={
          approval
            ? `${approval.reason} · ${formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}`
            : "Review invoices flagged by Aurora"
        }
      />

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm mb-4">Loading approvals…</div>
      )}

      {!isLoading && !approval && (
        <Card className="p-8 text-center text-sm text-muted-foreground">No items in the approval queue.</Card>
      )}

      {approval && (
        <div className="grid lg:grid-cols-[1fr_420px] gap-4">
          <Card className="!p-0 overflow-hidden">
            <div className="p-3 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4 text-primary" /> {invoiceLabel.toLowerCase()}.pdf</div>
              <div className="flex items-center gap-1">
                <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-accent"><ZoomOut className="h-4 w-4" /></button>
                <span className="text-xs px-1">100%</span>
                <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-accent"><ZoomIn className="h-4 w-4" /></button>
                <button className="h-8 w-8 grid place-items-center rounded-lg hover:bg-accent"><Download className="h-4 w-4" /></button>
              </div>
            </div>
            <div className="p-6 bg-background/30 min-h-[640px] relative">
              <div className="mx-auto max-w-[600px] bg-white text-slate-900 rounded-xl shadow-xl p-10 relative">
                <div className="flex items-start justify-between border-b border-slate-200 pb-4">
                  <div>
                    <div className="text-2xl font-bold tracking-tight">INVOICE PREVIEW</div>
                    <div className="text-xs text-slate-500 mt-1">{approval.reason}</div>
                  </div>
                  <div className="text-right rounded-md ring-2 ring-primary/50 bg-primary/5 px-3 py-1.5">
                    <div className="text-[10px] uppercase tracking-wider text-slate-400">Invoice</div>
                    <div className="text-lg font-bold leading-tight">{invoiceLabel}</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6 mt-6 text-xs">
                  <div className="rounded-md ring-2 ring-[color:var(--ai)]/40 bg-[color:var(--ai)]/5 px-2 py-1.5">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Risk</div>
                    <div className="font-semibold capitalize">{approval.risk_level}</div>
                  </div>
                  <div className="px-2 py-1.5">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Queue Status</div>
                    <div className="capitalize">{approval.status.replace(/_/g, " ")}</div>
                  </div>
                </div>

                {approval.ai_suggestion && (
                  <div className="mt-6 rounded-lg border border-slate-200 p-4 text-xs">
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">AI Suggestion</div>
                    <div>{approval.ai_suggestion}</div>
                  </div>
                )}
              </div>
            </div>
          </Card>

          <div className="space-y-4">
            <Card>
              <div className="flex items-center gap-4">
                <TrustRing score={trust} size={100} />
                <div className="flex-1">
                  <div className="text-xs uppercase tracking-wider text-muted-foreground">AI Recommendation</div>
                  <div className={`text-lg font-bold mt-1 capitalize ${recTone === "success" ? "text-success" : recTone === "destructive" ? "text-destructive" : recTone === "warning" ? "text-warning" : ""}`}>
                    {recommendation}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{confidence}% confidence · trust {trust}</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <button
                  onClick={() => handleAction("approve")}
                  disabled={action.isPending}
                  className="h-10 rounded-lg bg-success text-success-foreground text-xs font-semibold inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4" /> Approve
                </button>
                <button
                  onClick={() => handleAction("reject")}
                  disabled={action.isPending}
                  className="h-10 rounded-lg bg-destructive text-destructive-foreground text-xs font-semibold inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" /> Reject
                </button>
                <button
                  onClick={() => handleAction("request-review")}
                  disabled={action.isPending}
                  className="h-10 rounded-lg border border-border text-xs font-semibold inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <MessageSquare className="h-4 w-4" /> Request
                </button>
              </div>
            </Card>

            <Card>
              <h3 className="font-semibold mb-3 text-sm flex items-center gap-2"><Eye className="h-4 w-4" /> Extracted Fields</h3>
              <div className="space-y-3">
                {fields.map((f) => (
                  <div key={f.label}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground flex items-center gap-1">
                        {f.conf < 80 && <AlertTriangle className="h-3 w-3 text-warning" />}{f.label}
                      </span>
                      <span className="font-medium tabular-nums capitalize">{f.value}</span>
                    </div>
                    <ConfidenceBar value={f.conf} />
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <h3 className="font-semibold mb-3 text-sm flex items-center gap-2"><History className="h-4 w-4" /> Audit Trail</h3>
              <div className="space-y-3 text-xs">
                <div className="flex gap-3">
                  <div className="h-7 w-7 rounded-full grid place-items-center shrink-0 bg-[color:var(--ai)]/15 text-[color:var(--ai)]">AI</div>
                  <div className="flex-1">
                    <div className="font-medium">Aurora AI</div>
                    <div className="text-muted-foreground">{approval.reason}</div>
                    <div className="text-[10px] text-muted-foreground/70 mt-0.5">{formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}</div>
                  </div>
                </div>
                {approval.failed_rules && approval.failed_rules.length > 0 && (
                  <div className="flex gap-3">
                    <div className="h-7 w-7 rounded-full grid place-items-center shrink-0 bg-warning/15 text-warning">!</div>
                    <div className="flex-1">
                      <div className="font-medium">Business Rules</div>
                      <div className="text-muted-foreground">{approval.failed_rules.length} rule(s) failed</div>
                    </div>
                  </div>
                )}
                <div className="flex gap-3">
                  <div className="h-7 w-7 rounded-full grid place-items-center shrink-0 bg-muted text-muted-foreground">S</div>
                  <div className="flex-1">
                    <div className="font-medium">System</div>
                    <div className="text-muted-foreground">Routed to approval queue</div>
                    <div className="text-[10px] text-muted-foreground/70 mt-0.5">{formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}</div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
