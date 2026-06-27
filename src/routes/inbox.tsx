import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, ConfidenceBar, TrustRing } from "@/components/ui-bits";
import { useState } from "react";
import { Mail, Paperclip, Shield, RefreshCw, Zap } from "lucide-react";
import { useEmails, useEmail, useSyncEmails, useProcessEmails } from "@/lib/api/hooks";
import { formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/inbox")({ component: Inbox });

function Inbox() {
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const { data, isLoading, refetch } = useEmails(filter === "unread");
  const emails = data?.items ?? [];
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const activeId = selectedId ?? emails[0]?.id;
  const { data: selected } = useEmail(activeId);
  const sync = useSyncEmails();
  const process = useProcessEmails();

  const trust = selected?.trust_score ?? 0;

  return (
    <AppLayout>
      <PageHeader
        title="Inbox"
        subtitle="Aurora monitors your AP mailbox in real time."
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
              className="h-10 px-3 rounded-xl border border-border text-sm inline-flex items-center gap-2 hover:bg-accent"
            >
              <RefreshCw className={`h-4 w-4 ${sync.isPending ? "animate-spin" : ""}`} /> Sync
            </button>
            <button
              onClick={() => activeId && process.mutate([activeId])}
              disabled={process.isPending || !activeId}
              className="h-10 px-4 rounded-xl bg-primary text-primary-foreground text-sm font-medium inline-flex items-center gap-2"
            >
              <Zap className="h-4 w-4" /> Process Now
            </button>
          </div>
        }
      />
      <div className="grid lg:grid-cols-[380px_1fr] gap-4 h-[calc(100vh-12rem)]">
        <Card className="!p-0 overflow-hidden flex flex-col">
          <div className="p-3 border-b border-border flex items-center gap-2 text-xs">
            <button onClick={() => setFilter("all")} className={`px-2.5 py-1 rounded-md ${filter === "all" ? "bg-primary/15 text-primary font-medium" : "hover:bg-accent text-muted-foreground"}`}>
              All · {data?.total ?? 0}
            </button>
            <button onClick={() => setFilter("unread")} className={`px-2.5 py-1 rounded-md ${filter === "unread" ? "bg-primary/15 text-primary font-medium" : "hover:bg-accent text-muted-foreground"}`}>
              Unread
            </button>
            <button onClick={() => refetch()} className="ml-auto p-1 hover:bg-accent rounded"><RefreshCw className="h-3.5 w-3.5" /></button>
          </div>
          <div className="overflow-y-auto flex-1">
            {isLoading && <div className="p-4 text-sm text-muted-foreground">Loading emails…</div>}
            {emails.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelectedId(e.id)}
                className={`w-full text-left px-4 py-3 border-b border-border/60 hover:bg-accent/40 transition ${activeId === e.id ? "bg-accent/60" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {!e.is_read && <span className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                    <span className={`text-sm truncate ${!e.is_read ? "font-semibold" : ""}`}>{e.from_name ?? e.from_email}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground shrink-0">
                    {formatDistanceToNow(new Date(e.received_at), { addSuffix: false })}
                  </span>
                </div>
                <div className="mt-0.5 text-xs truncate text-muted-foreground">{e.subject}</div>
                <div className="mt-2 flex items-center gap-1.5">
                  <Badge tone={(e.trust_score ?? 0) >= 80 ? "success" : (e.trust_score ?? 0) >= 60 ? "warning" : "destructive"}>
                    <Shield className="h-2.5 w-2.5" /> {e.trust_score ?? "—"}
                  </Badge>
                  {e.attachment_count > 0 && <Badge><Paperclip className="h-2.5 w-2.5" /> {e.attachment_count}</Badge>}
                  {e.priority === "high" && <Badge tone="destructive">High</Badge>}
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card className="!p-0 overflow-hidden flex flex-col">
          {!selected ? (
            <div className="flex-1 grid place-items-center text-muted-foreground text-sm">Select an email</div>
          ) : (
            <>
              <div className="p-4 border-b border-border">
                <h3 className="font-semibold truncate">{selected.subject}</h3>
                <div className="text-xs text-muted-foreground mt-0.5 truncate">From {selected.from_email}</div>
              </div>
              <div className="grid lg:grid-cols-2 divide-x divide-border overflow-y-auto flex-1">
                <div className="p-5 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl grid place-items-center text-sm font-bold" style={{ background: "var(--gradient-aurora)" }}>
                      {(selected.from_name ?? selected.from_email)[0]?.toUpperCase()}
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{selected.from_name ?? selected.from_email}</div>
                      <div className="text-xs text-muted-foreground">to ap@yourcompany.com</div>
                    </div>
                  </div>
                  <div className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
                    {selected.body_text ?? selected.ai_summary ?? "No body content"}
                  </div>
                  {selected.attachments.length > 0 && (
                    <div className="rounded-xl border border-border p-3 bg-background/40">
                      <div className="text-xs font-semibold mb-2 flex items-center gap-2"><Paperclip className="h-3.5 w-3.5" /> Attachments</div>
                      <div className="flex gap-2 flex-wrap">
                        {selected.attachments.map((a) => (
                          <div key={a.id} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-background/60">
                            <div className="h-8 w-8 grid place-items-center rounded bg-primary/15 text-primary text-[10px] font-bold">DOC</div>
                            <div className="text-xs">
                              <div className="font-medium">{a.filename}</div>
                              <div className="text-muted-foreground">{Math.round(a.size_bytes / 1024)} KB</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-5 space-y-4 bg-background/20">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold uppercase tracking-wider text-[color:var(--ai)]">Aurora Analysis</div>
                    <Badge tone="ai">AI</Badge>
                  </div>
                  <div className="flex items-center gap-4">
                    <TrustRing score={trust} size={90} />
                    <div className="flex-1 space-y-2">
                      <div className="text-xs"><span className="text-muted-foreground">Detected intent:</span> <b>{selected.intent?.replace(/_/g, " ") ?? "Analyzing…"}</b></div>
                      <div className="text-xs"><span className="text-muted-foreground">Priority:</span> <b>{selected.priority}</b></div>
                      <div className="text-xs"><span className="text-muted-foreground">Stage:</span> <b>{selected.pipeline_stage ?? "received"}</b></div>
                    </div>
                  </div>
                  {selected.ai_summary && (
                    <div className="rounded-xl border border-border p-3 text-xs text-muted-foreground">{selected.ai_summary}</div>
                  )}
                  <div className="rounded-xl p-3 border border-[color:var(--ai)]/30 bg-[color:var(--ai)]/5">
                    <div className="text-xs font-semibold text-[color:var(--ai)] mb-1">Suggested action</div>
                    <div className="text-sm">{selected.suggested_action ?? "Run Process Now to analyze."}</div>
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <button
                        onClick={() => activeId && process.mutate([activeId])}
                        disabled={process.isPending}
                        className="h-9 rounded-lg bg-success text-success-foreground text-xs font-semibold inline-flex items-center justify-center gap-1"
                      >
                        <Zap className="h-3.5 w-3.5" /> Process
                      </button>
                      <button
                        onClick={() => sync.mutate()}
                        className="h-9 rounded-lg border border-border text-xs font-semibold inline-flex items-center justify-center gap-1"
                      >
                        <RefreshCw className="h-3.5 w-3.5" /> Re-sync
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
