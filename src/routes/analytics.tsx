import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { StatCard } from "@/components/ui-bits";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Clock, DollarSign, ShieldCheck, TrendingUp } from "lucide-react";
import { useAnalyticsMonthly, useAnalyticsRoi, useDashboard } from "@/lib/api/hooks";

export const Route = createFileRoute("/analytics")({ component: Analytics });

function formatUsd(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function Analytics() {
  const { data: monthly, isLoading: monthlyLoading } = useAnalyticsMonthly();
  const { data: roi, isLoading: roiLoading } = useAnalyticsRoi();
  const { data: dash, isLoading: dashLoading } = useDashboard();

  const isLoading = monthlyLoading || roiLoading || dashLoading;

  const series = (monthly?.months ?? []).map((m, i) => ({
    m,
    invoices: monthly?.invoices[i] ?? 0,
    savings: monthly?.savings_usd[i] ?? 0,
    hours: monthly?.hours_saved[i] ?? 0,
    fraud: monthly?.fraud_prevented[i] ?? 0,
  }));
  const depts = monthly?.by_department ?? [];
  const heat = monthly?.fraud_heatmap ?? [];

  return (
    <AppLayout>
      <PageHeader title="Analytics" subtitle="Aurora's impact on your finance operations." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Hours Saved (mo)" value={roi ? String(roi.hours_saved_month) : "—"} delta={`${dash?.touchless_percentage?.toFixed(1) ?? "—"}% touchless`} icon={Clock} tone="success" />
        <StatCard label="$ Saved (mo)" value={roi ? formatUsd(roi.dollars_saved_month) : "—"} delta="OPEX reduction" icon={DollarSign} tone="primary" />
        <StatCard label="Fraud Prevented" value={roi ? formatUsd(roi.fraud_prevented_ytd) : "—"} delta="YTD" icon={ShieldCheck} tone="ai" />
        <StatCard label="ROI" value={roi ? `${roi.roi_multiplier}×` : "—"} delta={`${dash?.processed_today ?? "—"} processed today`} icon={TrendingUp} tone="success" />
      </div>

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm mb-4">Loading analytics…</div>
      )}

      <div className="grid lg:grid-cols-2 gap-4 mb-4">
        <Card>
          <h3 className="font-semibold mb-3">Invoice Volume Trend</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={series}>
              <defs><linearGradient id="ag1" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--primary)" stopOpacity={0.5} /><stop offset="100%" stopColor="var(--primary)" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="m" stroke="var(--muted-foreground)" fontSize={11} axisLine={false} tickLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Area dataKey="invoices" stroke="var(--primary)" fill="url(#ag1)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="font-semibold mb-3">Cost Savings vs. Manual Hours</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="m" stroke="var(--muted-foreground)" fontSize={11} axisLine={false} tickLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Line dataKey="savings" stroke="var(--success)" strokeWidth={2.5} dot={false} />
              <Line dataKey="hours" stroke="var(--ai)" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card>
          <h3 className="font-semibold mb-3">By Department</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={depts} layout="vertical" margin={{ left: 8 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} width={90} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                {depts.map((_, i) => <Cell key={i} fill={i === 0 ? "var(--primary)" : i === 1 ? "var(--ai)" : "var(--success)"} fillOpacity={1 - i * 0.12} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="font-semibold mb-3">Fraud Heatmap</h3>
          {heat.length === 0 ? (
            <div className="py-16 text-center text-sm text-muted-foreground">No heatmap data available.</div>
          ) : (
            <>
              <div className="grid gap-1" style={{ gridTemplateColumns: "repeat(12, 1fr)" }}>
                {heat.map((c, i) => (
                  <div key={i} className="aspect-square rounded-sm" title={`${c.v.toFixed(2)}`}
                    style={{ background: `oklch(${0.25 + c.v * 0.5} ${0.04 + c.v * 0.2} ${268 - c.v * 60})` }} />
                ))}
              </div>
              <div className="flex items-center justify-between mt-3 text-[10px] text-muted-foreground">
                <span>Mon</span><span>Wed</span><span>Fri</span><span>Sun</span>
                <span className="ml-auto flex items-center gap-1">Low <span className="inline-block h-2 w-12 rounded" style={{ background: "linear-gradient(90deg, oklch(0.25 0.04 268), oklch(0.7 0.22 25))" }} /> High</span>
              </div>
            </>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
