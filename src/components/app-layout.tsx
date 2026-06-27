import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard, Inbox, FileText, AlertTriangle, CheckCircle2,
  BarChart3, Users, ScrollText, Sparkles, Settings, Search, Upload, Bell,
  Activity, Shield, Menu, X,
} from "lucide-react";

import { useState, type ReactNode } from "react";
import { useEmails, useExceptions } from "@/lib/api/hooks";

const navBase = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/inbox", icon: Inbox, label: "Inbox", badgeKey: "inbox" as const },
  { to: "/invoices", icon: FileText, label: "Invoices" },
  { to: "/exceptions", icon: AlertTriangle, label: "Exceptions", badgeKey: "exceptions" as const },
  { to: "/approvals", icon: CheckCircle2, label: "Approvals" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/clients", icon: Users, label: "Clients" },
  { to: "/rules", icon: ScrollText, label: "Business Rules" },
  { to: "/copilot", icon: Sparkles, label: "AI Copilot" },
  { to: "/trust", icon: Shield, label: "Trust Engine" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [open, setOpen] = useState(false);
  const { data: emails } = useEmails();
  const { data: exceptions } = useExceptions();

  const unreadCount = emails?.items?.filter((e) => !e.is_read).length ?? 0;
  const exceptionCount = Object.values(exceptions?.columns ?? {}).reduce((n, col) => n + col.length, 0);

  const nav = navBase.map((item) => ({
    ...item,
    badge: item.badgeKey === "inbox" ? unreadCount : item.badgeKey === "exceptions" ? exceptionCount : undefined,
  }));

  return (
    <div className="min-h-screen flex w-full">
      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 z-40 h-screen w-64 shrink-0 border-r border-sidebar-border bg-sidebar/80 backdrop-blur-xl transition-transform ${open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex h-16 items-center gap-3 px-5 border-b border-sidebar-border">
          <div className="relative h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gradient-aurora)" }}>
            <Sparkles className="h-5 w-5 text-white" />
            <span className="absolute inset-0 rounded-xl animate-aurora-pulse" style={{ background: "var(--gradient-aurora)", filter: "blur(12px)", opacity: 0.6, zIndex: -1 }} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold tracking-tight">Aurora TIA</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Touchless Invoice Agent</div>
          </div>
        </div>
        <nav className="p-3 space-y-0.5 overflow-y-auto h-[calc(100vh-4rem)]">
          {nav.map((item) => {
            const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_0_0_0_1px_var(--color-border)]"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                }`}
              >
                {active && <span className="absolute left-0 h-6 w-0.5 rounded-r bg-primary" />}
                <item.icon className={`h-4 w-4 shrink-0 ${active ? "text-primary" : ""}`} />
                <span className="flex-1 truncate">{item.label}</span>
                {item.badge != null && item.badge > 0 && (
                  <span className={`text-[10px] font-semibold rounded-full px-1.5 py-0.5 ${active ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
          <div className="mt-6 mx-2 p-3 rounded-xl glass">
            <div className="flex items-center gap-2 text-xs font-semibold">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              AI Engine Online
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">All 8 agents healthy</div>
          </div>
        </nav>
      </aside>

      {open && <div className="lg:hidden fixed inset-0 z-30 bg-black/50" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar onMenu={() => setOpen((v) => !v)} open={open} />
        <main className="flex-1 p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

function TopBar({ onMenu, open }: { onMenu: () => void; open: boolean }) {
  return (
    <header className="sticky top-0 z-20 h-16 border-b border-border bg-background/60 backdrop-blur-xl">
      <div className="h-full px-4 lg:px-8 flex items-center gap-3">
        <button onClick={onMenu} className="lg:hidden p-2 rounded-lg hover:bg-accent">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>

        <div className="relative flex-1 max-w-xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Search invoices, vendors, agents…  (⌘K)"
            className="w-full h-10 pl-10 pr-4 rounded-xl bg-muted/40 border border-border text-sm placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button className="hidden md:inline-flex items-center gap-2 h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover-glow">
            <Upload className="h-4 w-4" /> Upload Invoice
          </button>
          <button className="h-10 w-10 grid place-items-center rounded-xl border border-border hover:bg-accent">
            <Activity className="h-4 w-4 text-success" />
          </button>
          <button className="relative h-10 w-10 grid place-items-center rounded-xl border border-border hover:bg-accent">
            <Bell className="h-4 w-4" />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-destructive" />
          </button>
          <div className="h-10 pl-1 pr-3 flex items-center gap-2 rounded-xl border border-border">
            <div className="h-8 w-8 rounded-lg grid place-items-center text-xs font-bold" style={{ background: "var(--gradient-aurora)" }}>AK</div>
            <div className="hidden md:block leading-tight">
              <div className="text-xs font-semibold">Anya Kapoor</div>
              <div className="text-[10px] text-muted-foreground">Finance Lead</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4 mb-6">
      <div className="min-w-0">
        <h1 className="text-2xl lg:text-3xl font-bold tracking-tight truncate">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`glass rounded-2xl p-5 ${className}`}>{children}</div>;
}
