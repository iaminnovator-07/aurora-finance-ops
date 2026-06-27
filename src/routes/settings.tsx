import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge } from "@/components/ui-bits";
import { useState } from "react";
import { Plug, Key, Users, Shield, Mail, Workflow } from "lucide-react";

export const Route = createFileRoute("/settings")({ component: SettingsPage });

const tabs = [
  { key: "rules", label: "Approval Matrix", icon: Workflow },
  { key: "roles", label: "Roles", icon: Users },
  { key: "integrations", label: "Integrations", icon: Plug },
  { key: "api", label: "API Keys", icon: Key },
  { key: "security", label: "Security", icon: Shield },
  { key: "email", label: "Email", icon: Mail },
];

const erps = [
  { name: "SAP S/4HANA", connected: true, env: "Prod · EU" },
  { name: "Oracle NetSuite", connected: true, env: "Prod" },
  { name: "Microsoft Dynamics 365", connected: false },
  { name: "Workday", connected: false },
  { name: "QuickBooks Enterprise", connected: true, env: "Prod" },
  { name: "Xero", connected: false },
];

function SettingsPage() {
  const [tab, setTab] = useState("integrations");
  return (
    <AppLayout>
      <PageHeader title="Settings" subtitle="Configure Aurora for your enterprise." />
      <div className="grid lg:grid-cols-[220px_1fr] gap-4">
        <Card className="!p-2 h-fit">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${tab === t.key ? "bg-primary/15 text-primary font-medium" : "hover:bg-accent text-muted-foreground"}`}>
              <t.icon className="h-4 w-4" /> {t.label}
            </button>
          ))}
        </Card>

        <div className="space-y-4">
          {tab === "integrations" && (
            <Card>
              <h3 className="font-semibold mb-1">ERP Integrations</h3>
              <p className="text-xs text-muted-foreground mb-4">Push approved invoices directly to your system of record.</p>
              <div className="grid sm:grid-cols-2 gap-3">
                {erps.map((e) => (
                  <div key={e.name} className="p-4 rounded-xl border border-border bg-background/40 flex items-center justify-between hover-glow">
                    <div>
                      <div className="font-semibold text-sm">{e.name}</div>
                      {e.connected && <div className="text-[11px] text-muted-foreground">{e.env}</div>}
                    </div>
                    {e.connected ? <Badge tone="success">Connected</Badge> :
                      <button className="text-xs px-3 py-1.5 rounded-lg bg-primary text-primary-foreground">Connect</button>}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tab === "rules" && (
            <Card>
              <h3 className="font-semibold mb-1">Approval Matrix</h3>
              <p className="text-xs text-muted-foreground mb-4">Multi-level routing based on invoice amount.</p>
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="text-left py-2">Amount</th><th className="text-left">Approver L1</th><th className="text-left">Approver L2</th><th className="text-left">SLA</th></tr></thead>
                <tbody className="divide-y divide-border">
                  {[
                    ["< $1,000","Aurora AI","—","Instant"],
                    ["$1,000 – $10,000","Team Lead","—","4h"],
                    ["$10,000 – $50,000","Finance Manager","Director","1d"],
                    ["> $50,000","Director","CFO","2d"],
                  ].map((r) => <tr key={r[0]}><td className="py-3 font-medium">{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>)}
                </tbody>
              </table>
            </Card>
          )}

          {tab === "roles" && (
            <Card>
              <h3 className="font-semibold mb-4">Team & Roles</h3>
              <div className="space-y-3">
                {[
                  { name: "Anya Kapoor", role: "Finance Lead", email: "anya@company.com" },
                  { name: "Marco Lin", role: "AP Manager", email: "marco@company.com" },
                  { name: "Sara Vega", role: "AP Specialist", email: "sara@company.com" },
                  { name: "David Chen", role: "Controller", email: "david@company.com" },
                ].map((m) => (
                  <div key={m.email} className="flex items-center gap-3 p-3 rounded-xl border border-border">
                    <div className="h-9 w-9 rounded-lg grid place-items-center text-xs font-bold" style={{ background: "var(--gradient-aurora)" }}>{m.name.split(" ").map(n=>n[0]).join("")}</div>
                    <div className="flex-1"><div className="text-sm font-semibold">{m.name}</div><div className="text-xs text-muted-foreground">{m.email}</div></div>
                    <Badge tone="primary">{m.role}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tab === "api" && (
            <Card>
              <h3 className="font-semibold mb-1">API Keys</h3>
              <p className="text-xs text-muted-foreground mb-4">Programmatic access to Aurora's invoice & analytics APIs.</p>
              <div className="space-y-2">
                {[{n:"Production",k:"aur_live_a8x...c12f"},{n:"Staging",k:"aur_test_b3k...9281"}].map(k => (
                  <div key={k.n} className="flex items-center justify-between p-3 rounded-xl border border-border bg-background/40">
                    <div><div className="text-sm font-semibold">{k.n}</div><code className="text-xs text-muted-foreground">{k.k}</code></div>
                    <button className="text-xs px-3 py-1.5 rounded-lg border border-border">Rotate</button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tab === "security" && (
            <Card>
              <h3 className="font-semibold mb-4">Security</h3>
              <div className="space-y-3">
                {[
                  ["SSO (SAML 2.0)","Okta · enforced"],
                  ["MFA","Required for all admins"],
                  ["IP allowlist","3 corporate ranges"],
                  ["Audit log retention","7 years"],
                  ["SOC 2 Type II","Compliant"],
                ].map(([k,v]) => (
                  <div key={k} className="flex items-center justify-between p-3 rounded-xl border border-border">
                    <span className="text-sm font-medium">{k}</span>
                    <span className="text-xs text-muted-foreground">{v}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tab === "email" && (
            <Card>
              <h3 className="font-semibold mb-1">Email Channels</h3>
              <p className="text-xs text-muted-foreground mb-4">Mailboxes Aurora monitors for invoice ingestion.</p>
              <div className="space-y-2">
                {["ap@yourcompany.com","invoices@yourcompany.com","billing@yourcompany.com"].map((e) => (
                  <div key={e} className="flex items-center justify-between p-3 rounded-xl border border-border">
                    <div className="flex items-center gap-2 text-sm"><Mail className="h-4 w-4 text-primary" /> {e}</div>
                    <Badge tone="success">Active</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
