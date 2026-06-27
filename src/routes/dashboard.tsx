import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout, Card } from "@/components/app-layout";
import { StatCard, Badge, ConfidenceBar, ThinkingDots, TrustRing } from "@/components/ui-bits";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, PieChart, Pie,
  ResponsiveContainer, Tooltip, XAxis, YAxis, Line, LineChart,
} from "recharts";
import { ArrowUpRight, Bot, CheckCircle2, Clock, FileText, Shield, ShieldAlert,
  Sparkles, TrendingUp, Zap, Mail, Brain, ScanLine, Building2, RefreshCw,
} from "lucide-react";
import { useDashboard, useAgentsStatus } from "@/lib/api/hooks";

export const Route = createFileRoute("/dashboard")({ component: Dashboard });

const AGENT_ICONS: Record<string, typeof Mail> = {
  "Mail Intelligence": Mail,
  "Trust Verification": Shield,
  "Document Understanding": Brain,
  "OCR Extraction": ScanLine,
};

function statusTone(status: string) {
  if (status === "auto_approved" || status === "approved" || status === "dispatched") return "success";
  if (status === "in_review" || status === "draft") return "warning";
  if (status === "rejected" || status === "flagged") return "destructive";
  return "default";
}

function Dashboard() {
  const { data: dash, isLoading, refetch } = useDashboard();
  const { data: agentsData } = useAgentsStatus();

  const trend = dash?.throughput_trend ?? [];
  const vendors = dash?.vendor_breakdown ?? [];
  const approval = dash?.approval_breakdown ?? [];
  const recent = dash?.recent_invoices ?? [];
  const agents = agentsData?.agents?.slice(0, 4) ?? [];

  return (
    <AppLayout>
      <div className="relative overflow-hidden rounded-3xl glass p-8 mb-6">
        <div className="absolute inset-0 opacity-60" style={{ background: "var(--gradient-glow)" }} />
        <div className="relative grid lg:grid-cols-[1fr_auto] gap-8 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-medium text-[color:var(--ai)] bg-[color:var(--ai)]/10 border border-[color:var(--ai)]/20 px-3 py-1 rounded-full">
              <Sparkles className="h-3 w-3" /> Aurora is online · <ThinkingDots />
              <button onClick={() => refetch()} className="ml-1 opacity-70 hover:opacity-100"><RefreshCw className="h-3 w-3" /></button>
            </div>
            <h1 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight">
              Welcome back, <span className="text-gradient">Anya</span>
            </h1>
            <p className="mt-2 text-muted-foreground max-w-xl">
              Aurora processed <b className="text-foreground">{dash?.processed_today ?? "—"} invoices</b> today —{" "}
              <b className="text-success">{dash?.touchless_percentage?.toFixed(1) ?? "—"}% touchless</b>,
              saving your team an estimated <b className="text-success">{dash?.hours_saved_today ?? "—"} hours</b>.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link to="/approvals" className="inline-flex items-center gap-2 h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover-glow">
                Review Queue <ArrowUpRight className="h-4 w-4" />
              </Link>
              <Link to="/copilot" className="inline-flex items-center gap-2 h-10 px-4 rounded-xl border border-border text-sm font-medium hover:bg-accent">
                Open Copilot
              </Link>
            </div>
          </div>
          <div className="hidden lg:flex items-center gap-6 px-6 py-5 rounded-2xl border border-border bg-background/40">
            <TrustRing score={Math.round(dash?.trust_avg ?? 0)} size={110} />
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">Tenant Trust</div>
              <div className="text-2xl font-bold">{(dash?.trust_avg ?? 0) >= 70 ? "Healthy" : "Review"}</div>
              <div className="text-xs text-success mt-1">Live from database</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-6">
        <StatCard label="Processed" value={String(dash?.processed_today ?? "—")} delta="Today" icon={FileText} tone="primary" />
        <StatCard label="Auto Approved" value={String(dash?.auto_approved ?? "—")} delta={`${dash?.touchless_percentage?.toFixed(1) ?? "—"}% touchless`} icon={CheckCircle2} tone="success" />
        <StatCard label="Pending Review" value={String(dash?.pending_review ?? "—")} delta="Live queue" icon={Clock} tone="warning" />
        <StatCard label="Fraud Alerts" value={String(dash?.fraud_alerts ?? "—")} delta="Spam flagged" icon={ShieldAlert} tone="destructive" />
        <StatCard label="Trust Avg." value={String(Math.round(dash?.trust_avg ?? 0))} delta="All invoices" icon={Shield} tone="ai" />
        <StatCard label="AI Accuracy" value={`${dash?.ai_accuracy?.toFixed(1) ?? "—"}%`} delta="Avg confidence" icon={Zap} tone="ai" />
      </div>

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm">Loading dashboard…</div>
      )}

      <div className="grid lg:grid-cols-3 gap-4 mb-6">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold">Invoice Throughput</h3>
              <p className="text-xs text-muted-foreground">Last 14 days · processed vs auto-approved</p>
            </div>
            <Badge tone="primary">Live</Badge>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={trend}>
              <defs>
                <linearGradient id="g1" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="g2" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="var(--success)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="var(--success)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Area type="monotone" dataKey="processed" stroke="var(--primary)" fill="url(#g1)" strokeWidth={2} />
              <Area type="monotone" dataKey="auto" stroke="var(--success)" fill="url(#g2)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 className="font-semibold mb-1">Approval Breakdown</h3>
          <p className="text-xs text-muted-foreground mb-2">From database</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={approval} dataKey="value" innerRadius={50} outerRadius={75} paddingAngle={3} stroke="none">
                {approval.map((e, i) => <Cell key={i} fill={e.color ?? "var(--primary)"} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {approval.map((a) => (
              <div key={a.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: a.color }} /> {a.name}</span>
                <span className="font-semibold tabular-nums">{a.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mb-6">
        <Card>
          <h3 className="font-semibold mb-3">Top Vendors</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={vendors} layout="vertical" margin={{ left: 8 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} width={110} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Bar dataKey="value" fill="var(--primary)" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="font-semibold mb-3">Fraud Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12 }} />
              <Line type="monotone" dataKey="processed" stroke="var(--destructive)" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="font-semibold mb-3">Processing Stats</h3>
          <div className="text-4xl font-bold tracking-tight">{dash?.touchless_percentage?.toFixed(0) ?? "—"}<span className="text-lg text-muted-foreground ml-1">% touchless</span></div>
          <div className="text-xs text-success mt-1 flex items-center gap-1"><TrendingUp className="h-3 w-3" /> Live automation rate</div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Live Invoice Queue</h3>
            <Badge tone="success">Real-time</Badge>
          </div>
          <div className="divide-y divide-border -mx-5">
            {recent.length === 0 && (
              <div className="px-5 py-8 text-center text-sm text-muted-foreground">No invoices yet — sync inbox to start processing.</div>
            )}
            {recent.map((r) => (
              <div key={r.id} className="px-5 py-3 grid grid-cols-[auto_1fr_auto_auto] items-center gap-4 hover:bg-accent/30 transition">
                <div className="h-9 w-9 rounded-lg grid place-items-center bg-primary/10 text-primary"><FileText className="h-4 w-4" /></div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <span>{r.id}</span>
                    <Badge tone={statusTone(r.status)}>{r.status.replace(/_/g, " ")}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2"><Building2 className="h-3 w-3" /> {r.vendor}</div>
                </div>
                <div className="w-24"><ConfidenceBar value={r.trust} /></div>
                <div className="font-semibold tabular-nums text-sm">{r.amount}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">AI Agents</h3>
            <Badge tone="ai"><Bot className="h-3 w-3" /> {agents.filter((a) => a.status === "active").length} active</Badge>
          </div>
          <div className="space-y-3">
            {agents.map((a) => {
              const Icon = AGENT_ICONS[a.name] ?? Bot;
              return (
                <div key={a.name} className="p-3 rounded-xl border border-border bg-background/30">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-lg grid place-items-center bg-[color:var(--ai)]/15 text-[color:var(--ai)]"><Icon className="h-4 w-4" /></div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{a.name}</div>
                      <div className="text-[11px] text-muted-foreground truncate">{a.task}</div>
                    </div>
                    {a.status === "thinking" ? <ThinkingDots /> : <span className={`h-2 w-2 rounded-full ${a.status === "active" ? "bg-success" : "bg-muted-foreground/40"}`} />}
                  </div>
                  <div className="mt-2"><ConfidenceBar value={a.conf} /></div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
