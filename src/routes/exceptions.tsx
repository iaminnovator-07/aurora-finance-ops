import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge } from "@/components/ui-bits";
import { Plus } from "lucide-react";
import { useExceptions } from "@/lib/api/hooks";
import type { ExceptionItem } from "@/lib/api/hooks";

export const Route = createFileRoute("/exceptions")({ component: Exceptions });

const COLUMN_META = [
  { key: "needs_review", title: "Needs Review", tone: "warning" as const },
  { key: "waiting_approval", title: "Waiting Approval", tone: "primary" as const },
  { key: "rejected", title: "Rejected", tone: "destructive" as const },
  { key: "resolved", title: "Resolved", tone: "success" as const },
];

function riskTone(risk: string): "destructive" | "warning" | "default" {
  const r = risk.toLowerCase();
  if (r === "critical" || r === "high") return "destructive";
  if (r === "medium") return "warning";
  return "default";
}

function Exceptions() {
  const { data, isLoading } = useExceptions();
  const columns = data?.columns ?? {};

  return (
    <AppLayout>
      <PageHeader title="Exception Queue" subtitle="Invoices that need a human in the loop."
        actions={<button className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2"><Plus className="h-4 w-4" /> New exception</button>}
      />

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm mb-4">Loading exceptions…</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {COLUMN_META.map((col) => {
          const items = (columns[col.key] ?? []) as ExceptionItem[];
          return (
            <div key={col.key} className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${
                    col.tone === "warning" ? "bg-warning" : col.tone === "primary" ? "bg-primary" :
                    col.tone === "destructive" ? "bg-destructive" : "bg-success"}`} />
                  <h3 className="font-semibold text-sm">{col.title}</h3>
                </div>
                <span className="text-xs text-muted-foreground">{items.length}</span>
              </div>
              <div className="space-y-2 min-h-[200px]">
                {items.length === 0 && (
                  <div className="text-xs text-muted-foreground text-center py-8 border border-dashed border-border rounded-xl">No items</div>
                )}
                {items.map((it) => (
                  <Card key={it.id} className="!p-4 hover-glow cursor-grab">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold">{it.invoice_number ?? it.invoice_id}</span>
                      <Badge tone={riskTone(it.risk_level)}>{it.risk_level}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mb-3">{it.reason}</div>
                    {it.ai_suggestion && (
                      <div className="rounded-lg p-2 border border-[color:var(--ai)]/30 bg-[color:var(--ai)]/5 text-[11px]">
                        <b className="text-[color:var(--ai)]">Aurora:</b> {it.ai_suggestion}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </AppLayout>
  );
}
