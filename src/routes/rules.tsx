import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge } from "@/components/ui-bits";
import { GripVertical, Plus, Zap } from "lucide-react";

export const Route = createFileRoute("/rules")({ component: Rules });

const rules = [
  { name: "Auto-approve under $1,000", when: "amount < 1000 AND vendor.trust > 85", then: "approve + push ERP", on: true },
  { name: "Flag duplicate within 30d", when: "similar(invoice) > 0.95", then: "queue: needs_review", on: true },
  { name: "Reject unknown domain + urgent keywords", when: "vendor.unknown AND subject matches /urgent|wire/i", then: "reject + alert security", on: true },
  { name: "Multi-level approval > $10k", when: "amount > 10000", then: "request approval: manager → CFO", on: true },
  { name: "Hold if PO mismatch", when: "po.amount != invoice.amount", then: "queue: waiting_approval", on: false },
];

function Rules() {
  return (
    <AppLayout>
      <PageHeader title="Business Rules" subtitle="Define when Aurora acts autonomously vs. escalates."
        actions={<button className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2"><Plus className="h-4 w-4" /> New rule</button>}
      />

      <div className="grid lg:grid-cols-[1fr_360px] gap-4">
        <Card className="!p-0 overflow-hidden">
          <div className="divide-y divide-border">
            {rules.map((r, i) => (
              <div key={i} className="p-4 flex items-center gap-3 hover:bg-accent/30">
                <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2"><span className="text-sm font-semibold">{r.name}</span>{r.on ? <Badge tone="success">Active</Badge> : <Badge>Paused</Badge>}</div>
                  <div className="mt-1 text-xs text-muted-foreground"><b className="text-foreground/80">When</b> <code className="px-1 py-0.5 rounded bg-muted text-[11px]">{r.when}</code> <b className="text-foreground/80 ml-2">→</b> <code className="px-1 py-0.5 rounded bg-muted text-[11px]">{r.then}</code></div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked={r.on} className="sr-only peer" />
                  <div className="w-10 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition relative after:absolute after:top-0.5 after:left-0.5 after:bg-white after:h-4 after:w-4 after:rounded-full after:transition-all peer-checked:after:translate-x-5" />
                </label>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap className="h-4 w-4 text-warning" /> Rule Impact (30d)</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Auto-approvals</span><span className="font-bold">1,842</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Duplicates blocked</span><span className="font-bold">38</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Fraud rejected</span><span className="font-bold text-destructive">12</span></div>
            <div className="flex items-center justify-between"><span className="text-muted-foreground">Escalations</span><span className="font-bold">214</span></div>
          </div>
          <div className="mt-5 p-3 rounded-xl border border-[color:var(--ai)]/30 bg-[color:var(--ai)]/5 text-xs">
            <b className="text-[color:var(--ai)]">Aurora suggests</b> a new rule: <i>"Auto-approve recurring SaaS subscriptions from verified vendors under $500"</i> — would have auto-cleared 84 invoices this month.
            <button className="mt-2 text-[color:var(--ai)] font-semibold hover:underline">Review suggestion →</button>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
