import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, ConfidenceBar } from "@/components/ui-bits";
import { Download, Filter, Search, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useInvoices } from "@/lib/api/hooks";

export const Route = createFileRoute("/invoices")({ component: Invoices });

const STATUS_FILTERS = ["All", "auto_approved", "in_review", "flagged", "dispatched"];

function statusLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusTone(s: string): "success" | "warning" | "destructive" | "default" {
  if (s === "auto_approved" || s === "approved" || s === "dispatched") return "success";
  if (s === "in_review" || s === "draft") return "warning";
  if (s === "rejected" || s === "flagged") return "destructive";
  return "default";
}

function Invoices() {
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const status = filter === "All" ? undefined : filter;
  const { data, isLoading, refetch } = useInvoices(status, search || undefined);
  const rows = data?.items ?? [];

  return (
    <AppLayout>
      <PageHeader title="Invoices" subtitle="All invoices captured by Aurora across channels."
        actions={
          <>
            <button onClick={() => refetch()} className="h-10 px-3 rounded-xl border border-border text-sm inline-flex items-center gap-2"><RefreshCw className="h-4 w-4" /> Refresh</button>
          </>
        }
      />

      <Card className="!p-0 overflow-hidden">
        <div className="p-4 border-b border-border flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-10 pl-10 pr-3 rounded-lg bg-muted/40 border border-border text-sm"
              placeholder="Search invoices…"
            />
          </div>
          <div className="flex gap-1 text-xs">
            {STATUS_FILTERS.map((t) => (
              <button key={t} onClick={() => setFilter(t)} className={`px-3 py-1.5 rounded-md capitalize ${filter === t ? "bg-primary/15 text-primary" : "hover:bg-accent text-muted-foreground"}`}>
                {t === "All" ? t : statusLabel(t)}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 text-center text-sm text-muted-foreground">Loading invoices…</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wider text-muted-foreground bg-muted/30">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">Invoice</th>
                  <th className="text-left px-5 py-3 font-medium">Vendor</th>
                  <th className="text-left px-5 py-3 font-medium">Date</th>
                  <th className="text-right px-5 py-3 font-medium">Amount</th>
                  <th className="text-left px-5 py-3 font-medium w-44">Trust</th>
                  <th className="text-left px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={6} className="px-5 py-8 text-center text-muted-foreground">No invoices found. Process emails from the Inbox.</td></tr>
                )}
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-border hover:bg-accent/30 transition">
                    <td className="px-5 py-3 font-medium"><Link to="/approvals" className="hover:text-primary">{r.invoice_number}</Link></td>
                    <td className="px-5 py-3">{r.vendor_name ?? "—"}</td>
                    <td className="px-5 py-3 text-muted-foreground">{r.issue_date ?? new Date(r.created_at).toLocaleDateString()}</td>
                    <td className="px-5 py-3 text-right tabular-nums font-semibold">
                      {r.total_amount ? `$${Number(r.total_amount).toLocaleString()}` : "—"}
                    </td>
                    <td className="px-5 py-3"><ConfidenceBar value={r.trust_score ?? 0} /></td>
                    <td className="px-5 py-3"><Badge tone={statusTone(r.status)}>{statusLabel(r.status)}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </AppLayout>
  );
}
