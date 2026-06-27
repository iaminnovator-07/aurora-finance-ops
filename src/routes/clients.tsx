import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, TrustRing } from "@/components/ui-bits";
import { ResponsiveContainer, Line, LineChart, XAxis, Tooltip } from "recharts";
import { Building2, MapPin, Mail, Phone, ExternalLink } from "lucide-react";
import { useClients } from "@/lib/api/hooks";

export const Route = createFileRoute("/clients")({ component: Clients });

function formatUsd(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function riskLabel(risk: string) {
  return risk.charAt(0).toUpperCase() + risk.slice(1);
}

function riskTone(risk: string): "success" | "warning" | "destructive" | "default" {
  const r = risk.toLowerCase();
  if (r === "low") return "success";
  if (r === "medium") return "warning";
  if (r === "high" || r === "critical") return "destructive";
  return "default";
}

function trustColor(trust: number | null) {
  if (trust == null) return "text-muted-foreground";
  if (trust >= 80) return "text-success";
  if (trust >= 60) return "text-warning";
  return "text-destructive";
}

function Clients() {
  const { data, isLoading } = useClients();
  const clients = data?.items ?? [];
  const featured = clients[0];
  const spark = Array.from({ length: 12 }, (_, i) => ({
    x: i,
    y: featured?.trust_score ?? 0,
  }));

  return (
    <AppLayout>
      <PageHeader title="Vendors & Clients" subtitle="Trust profiles, spend, and risk across your network." />

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm mb-4">Loading clients…</div>
      )}

      {featured && (
        <Card className="mb-6 grid lg:grid-cols-[auto_1fr_auto] gap-6 items-center">
          <TrustRing score={Math.round(featured.trust_score ?? 0)} size={130} />
          <div>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-bold">{featured.name}</h2>
              <Badge tone={riskTone(featured.risk_level)}>{riskLabel(featured.risk_level)} risk</Badge>
            </div>
            <div className="mt-2 grid sm:grid-cols-3 gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" /> {[featured.city, featured.country].filter(Boolean).join(", ") || "—"}</span>
              <span className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" /> {featured.email ?? featured.domain ?? "—"}</span>
              <span className="flex items-center gap-1.5"><Phone className="h-3.5 w-3.5" /> {featured.phone ?? "—"}</span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
              <div><div className="text-muted-foreground text-[10px] uppercase tracking-wider">Invoices</div><div className="font-bold">{featured.invoice_count}</div></div>
              <div><div className="text-muted-foreground text-[10px] uppercase tracking-wider">Spend YTD</div><div className="font-bold">{formatUsd(featured.spend_ytd)}</div></div>
              <div><div className="text-muted-foreground text-[10px] uppercase tracking-wider">Trust</div><div className="font-bold">{featured.trust_score ?? "—"}</div></div>
            </div>
          </div>
          <div className="w-56">
            <div className="text-xs text-muted-foreground mb-1">Trust trend (12mo)</div>
            <ResponsiveContainer width="100%" height={80}>
              <LineChart data={spark}><Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 11 }} /><Line dataKey="y" stroke="var(--success)" strokeWidth={2} dot={false} /></LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {!isLoading && clients.length === 0 && (
        <Card className="mb-6 p-8 text-center text-sm text-muted-foreground">No vendors yet — process invoices to build vendor profiles.</Card>
      )}

      <Card className="!p-0 overflow-hidden">
        <div className="p-4 border-b border-border"><h3 className="font-semibold">All Vendors</h3></div>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wider text-muted-foreground bg-muted/30">
            <tr><th className="text-left px-5 py-3 font-medium">Vendor</th><th className="text-left px-5 py-3 font-medium">Trust</th><th className="text-right px-5 py-3 font-medium">Invoices</th><th className="text-right px-5 py-3 font-medium">Spend YTD</th><th className="text-left px-5 py-3 font-medium">Risk</th><th className="px-5 py-3"></th></tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id} className="border-t border-border hover:bg-accent/30">
                <td className="px-5 py-3 font-medium">{c.name}</td>
                <td className="px-5 py-3"><span className={`font-semibold ${trustColor(c.trust_score)}`}>{c.trust_score ?? "—"}</span></td>
                <td className="px-5 py-3 text-right tabular-nums">{c.invoice_count}</td>
                <td className="px-5 py-3 text-right tabular-nums font-semibold">{formatUsd(c.spend_ytd)}</td>
                <td className="px-5 py-3"><Badge tone={riskTone(c.risk_level)}>{riskLabel(c.risk_level)}</Badge></td>
                <td className="px-5 py-3"><button className="text-muted-foreground hover:text-primary"><ExternalLink className="h-4 w-4" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </AppLayout>
  );
}
