import { Bot, CheckCircle2, Clock, FileText, Shield, ShieldAlert, TrendingUp, Zap } from "lucide-react";
import type { ReactNode } from "react";

export function StatCard({
  label, value, delta, icon: Icon, tone = "primary",
}: { label: string; value: string; delta?: string; icon: any; tone?: "primary" | "success" | "warning" | "ai" | "destructive" }) {
  const toneMap: Record<string, string> = {
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    ai: "text-[color:var(--ai)]",
    destructive: "text-destructive",
  };
  return (
    <div className="glass rounded-2xl p-5 hover-glow relative overflow-hidden">
      <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-20 blur-2xl" style={{ background: `var(--color-${tone === "ai" ? "ai" : tone})` }} />
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
        <Icon className={`h-4 w-4 ${toneMap[tone]}`} />
      </div>
      <div className="mt-3 text-3xl font-bold tracking-tight">{value}</div>
      {delta && <div className={`mt-1 text-xs font-medium ${toneMap[tone]}`}>{delta}</div>}
    </div>
  );
}

export function TrustRing({ score, size = 120 }: { score: number; size?: number }) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const dash = (score / 100) * c;
  const color = score >= 80 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--destructive)";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--border)" strokeWidth="8" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="8" fill="none"
          strokeDasharray={`${dash} ${c}`} strokeLinecap="round" style={{ transition: "stroke-dasharray 1s ease" }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="text-2xl font-bold">{score}</div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Trust</div>
        </div>
      </div>
    </div>
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "success" | "warning" | "destructive" | "ai" | "primary" }) {
  const map: Record<string, string> = {
    default: "bg-muted text-muted-foreground border-border",
    success: "bg-success/15 text-success border-success/20",
    warning: "bg-warning/15 text-warning border-warning/20",
    destructive: "bg-destructive/15 text-destructive border-destructive/20",
    ai: "bg-[color:var(--ai)]/15 text-[color:var(--ai)] border-[color:var(--ai)]/20",
    primary: "bg-primary/15 text-primary border-primary/20",
  };
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${map[tone]}`}>{children}</span>;
}

export function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 90 ? "var(--success)" : value >= 70 ? "var(--primary)" : "var(--warning)";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold tabular-nums" style={{ color }}>{value}%</span>
    </div>
  );
}

export function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-1.5 w-1.5 rounded-full bg-[color:var(--ai)] animate-ai-think" style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </span>
  );
}

export const HeroIcons = { Bot, CheckCircle2, Clock, FileText, Shield, ShieldAlert, TrendingUp, Zap };
