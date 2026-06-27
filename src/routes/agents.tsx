import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, ConfidenceBar, ThinkingDots } from "@/components/ui-bits";
import { Mail, Shield, Brain, ScanLine, ScrollText, FileCheck, Plug, BarChart3, Activity, Bot } from "lucide-react";
import { useAgentsStatus } from "@/lib/api/hooks";

export const Route = createFileRoute("/agents")({ component: Agents });

const AGENT_ICONS: Record<string, typeof Mail> = {
  "Mail Intelligence": Mail,
  "Trust Verification": Shield,
  "Document Understanding": Brain,
  "OCR Extraction": ScanLine,
  "Business Rules": ScrollText,
  "Invoice Generation": FileCheck,
  "ERP Integration": Plug,
  "Analytics": BarChart3,
};

function logLevelClass(lvl: string) {
  if (lvl === "ok") return "text-success";
  if (lvl === "warn") return "text-warning";
  if (lvl === "err") return "text-destructive";
  return "text-[color:var(--ai)]";
}

function Agents() {
  const { data, isLoading } = useAgentsStatus();
  const agents = data?.agents ?? [];
  const liveLogs = data?.live_logs ?? [];

  return (
    <AppLayout>
      <PageHeader title="AI Agents" subtitle="Real-time orchestration across the touchless invoice pipeline."
        actions={<Badge tone="ai"><Activity className="h-3 w-3" /> {data?.pipeline_running ? "Pipeline running" : "Pipeline idle"}</Badge>}
      />

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground text-sm mb-4">Loading agents…</div>
      )}

      <Card className="mb-6 relative overflow-hidden">
        <h3 className="font-semibold mb-6">Processing Pipeline</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 relative">
          {agents.map((a, i) => {
            const Icon = AGENT_ICONS[a.name] ?? Bot;
            return (
              <div key={a.name} className="relative">
                {i < agents.length - 1 && (i + 1) % 4 !== 0 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 z-10 text-muted-foreground">
                    <svg width="24" height="2" className="animate-flow">
                      <line x1="0" y1="1" x2="24" y2="1" stroke="var(--primary)" strokeWidth="1.5" strokeDasharray="4 4" />
                    </svg>
                  </div>
                )}
                <div className={`glass rounded-2xl p-4 hover-glow ${a.status === "thinking" ? "border-[color:var(--ai)]/40" : ""}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`h-9 w-9 rounded-lg grid place-items-center ${
                      a.status === "active" ? "bg-success/15 text-success" :
                      a.status === "thinking" ? "bg-[color:var(--ai)]/15 text-[color:var(--ai)]" :
                      "bg-muted text-muted-foreground"}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    {a.status === "thinking" ? <ThinkingDots /> :
                     a.status === "active" ? <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-75 animate-ping" /><span className="relative inline-flex h-2 w-2 rounded-full bg-success" /></span> :
                     <span className="h-2 w-2 rounded-full bg-muted-foreground/40" />}
                  </div>
                  <div className="text-sm font-semibold">{a.name}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5 truncate">{a.task}</div>
                  <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>⏱ {a.time}</span>
                    <span className="font-semibold text-foreground">{a.conf}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold mb-3">Agent Performance (24h)</h3>
          <div className="space-y-3">
            {agents.slice(0, 6).map((a) => {
              const Icon = AGENT_ICONS[a.name] ?? Bot;
              return (
                <div key={a.name}>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <div className="flex items-center gap-2"><Icon className="h-3.5 w-3.5" /> {a.name}</div>
                    <span className="text-muted-foreground">{a.conf}%</span>
                  </div>
                  <ConfidenceBar value={a.conf} />
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold mb-3">Live Logs</h3>
          <div className="font-mono text-[11px] space-y-1.5 max-h-72 overflow-y-auto">
            {liveLogs.length === 0 && (
              <div className="text-muted-foreground py-4 text-center">No agent logs yet.</div>
            )}
            {liveLogs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-muted-foreground">{log.time}</span>
                <span className={logLevelClass(log.level)}>[{log.level.toUpperCase()}]</span>
                <span className="text-foreground/80">{log.message}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
