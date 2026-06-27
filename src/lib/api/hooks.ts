import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

// ── Auth ──────────────────────────────────────────────────────────────────────

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api.post<{ user: { id: string; email: string; full_name: string; role: string }; tokens: { access_token: string; refresh_token: string } }>(
        "/auth/login",
        body,
      ),
    onSuccess: () => qc.invalidateQueries(),
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/analytics/dashboard"),
    refetchInterval: 30_000,
  });
}

export function useAgentsStatus() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: () => api.get<{ agents: AgentStatus[]; pipeline_running: boolean; live_logs: LiveLog[] }>("/agents/status"),
    refetchInterval: 5_000,
  });
}

// ── Inbox ─────────────────────────────────────────────────────────────────────

export function useEmails(unreadOnly = false) {
  return useQuery({
    queryKey: ["emails", unreadOnly],
    queryFn: () =>
      api.get<{ items: EmailItem[]; total: number }>(
        `/emails?limit=50${unreadOnly ? "&unread_only=true" : ""}`,
      ),
    refetchInterval: 15_000,
  });
}

export function useEmail(id: string | undefined) {
  return useQuery({
    queryKey: ["email", id],
    queryFn: () => api.get<EmailDetail>(`/emails/${id}`),
    enabled: !!id,
  });
}

export function useSyncEmails() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ synced_count: number; new_count: number; message: string }>("/emails/sync"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["emails"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useProcessEmails() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (emailIds?: string[]) =>
      api.post("/emails/process", emailIds?.length ? { email_ids: emailIds } : { process_all: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["emails"] });
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

// ── Trust ─────────────────────────────────────────────────────────────────────

export function useTrustCheck(emailId: string | undefined) {
  return useQuery({
    queryKey: ["trust", emailId],
    queryFn: () => api.post<TrustData>("/trust/check", { email_id: emailId }),
    enabled: !!emailId,
  });
}

// ── Invoices ──────────────────────────────────────────────────────────────────

export function useInvoices(status?: string, search?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  const qs = params.toString();
  return useQuery({
    queryKey: ["invoices", status, search],
    queryFn: () => api.get<{ items: InvoiceItem[]; total: number }>(`/invoice${qs ? `?${qs}` : ""}`),
    refetchInterval: 20_000,
  });
}

export function useInvoice(id: string | undefined) {
  return useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api.get<InvoiceDetail>(`/invoice/${id}`),
    enabled: !!id,
  });
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export function useApprovals() {
  return useQuery({
    queryKey: ["approvals"],
    queryFn: () => api.get<{ items: ApprovalItem[]; total: number }>("/approvals"),
    refetchInterval: 15_000,
  });
}

export function useApprovalAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, notes }: { id: string; action: "approve" | "reject" | "request-review"; notes?: string }) =>
      api.post(`/approvals/${id}/${action}`, { notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["exceptions"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function useAnalyticsMonthly() {
  return useQuery({
    queryKey: ["analytics", "monthly"],
    queryFn: () => api.get<MonthlyAnalytics>("/analytics/monthly"),
  });
}

export function useAnalyticsRoi() {
  return useQuery({
    queryKey: ["analytics", "roi"],
    queryFn: () => api.get<RoiAnalytics>("/analytics/roi"),
  });
}

// ── Copilot ───────────────────────────────────────────────────────────────────

export function useCopilotChat() {
  return useMutation({
    mutationFn: (body: { message: string; conversation_id?: string }) =>
      api.post<{ conversation_id: string; reply: string; data?: Record<string, unknown>; confidence: number; sources?: { type: string; id: string }[] }>(
        "/copilot/chat",
        body,
      ),
  });
}

// ── Clients ───────────────────────────────────────────────────────────────────

export function useClients() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: () => api.get<{ items: ClientItem[]; total: number }>("/clients"),
  });
}

// ── Exceptions ────────────────────────────────────────────────────────────────

export function useExceptions() {
  return useQuery({
    queryKey: ["exceptions"],
    queryFn: () => api.get<{ columns: Record<string, ExceptionItem[]> }>("/exceptions"),
    refetchInterval: 15_000,
  });
}

// ── Notifications ─────────────────────────────────────────────────────────────

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<{ items: NotificationItem[]; total: number }>("/notifications"),
    refetchInterval: 30_000,
  });
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type DashboardData = {
  processed_today: number;
  auto_approved: number;
  pending_review: number;
  fraud_alerts: number;
  trust_avg: number;
  ai_accuracy: number;
  touchless_percentage: number;
  hours_saved_today: number;
  recent_invoices: { id: string; vendor: string; amount: string; trust: number; status: string }[];
  throughput_trend: { day: string; processed: number; auto: number }[];
  vendor_breakdown: { name: string; value: number }[];
  approval_breakdown: { name: string; value: number; color?: string }[];
  agent_status: AgentStatus[];
};

export type AgentStatus = {
  name: string;
  status: string;
  task: string;
  time: string;
  conf: number;
};

export type LiveLog = { time: string; level: string; message: string };

export type EmailItem = {
  id: string;
  from_email: string;
  from_name: string | null;
  subject: string;
  received_at: string;
  status: string;
  priority: string;
  intent: string | null;
  ai_summary: string | null;
  is_read: boolean;
  is_flagged: boolean;
  is_spam: boolean;
  is_duplicate: boolean;
  trust_score: number | null;
  attachment_count: number;
  pipeline_stage: string | null;
};

export type EmailDetail = EmailItem & {
  body_text: string | null;
  attachments: { id: string; filename: string; content_type: string; size_bytes: number; is_processed: boolean }[];
  trust_details: Record<string, unknown> | null;
  rule_checks: Record<string, unknown>[] | null;
  suggested_action: string | null;
};

export type TrustData = {
  trust_score: number;
  identity_score: number;
  content_score: number;
  domain_trust_score: number;
  vendor_reputation_score: number;
  duplicate_score: number;
  overall_score: number;
  risk_level: string;
  reason: string;
  checks: Record<string, unknown>;
  reasoning_timeline: { step?: string; score?: number; detail?: string; w?: string; d?: string; tone?: string }[];
  confidence: number;
};

export type InvoiceItem = {
  id: string;
  invoice_number: string;
  status: string;
  vendor_name: string | null;
  issue_date: string | null;
  total_amount: string | null;
  trust_score: number | null;
  confidence_score: number | null;
  created_at: string;
};

export type InvoiceDetail = InvoiceItem & {
  due_date: string | null;
  po_reference: string | null;
  currency: string;
  subtotal: string | null;
  tax_amount: string | null;
  line_items: Record<string, unknown>[] | null;
  extracted_fields: Record<string, unknown> | null;
  field_confidences: Record<string, number> | null;
  processing_history: Record<string, unknown>[];
  rules_passed: boolean | null;
};

export type ApprovalItem = {
  id: string;
  invoice_id: string;
  invoice_number: string | null;
  status: string;
  approval_status: string;
  reason: string;
  risk_level: string;
  ai_recommendation: string | null;
  ai_suggestion: string | null;
  confidence_score: number | null;
  trust_score: number | null;
  failed_rules: Record<string, unknown>[] | null;
  created_at: string;
};

export type MonthlyAnalytics = {
  months: string[];
  invoices: number[];
  savings_usd: number[];
  hours_saved: number[];
  fraud_prevented: number[];
  by_department: { name: string; value: number }[];
  fraud_heatmap: { x: number; y: number; v: number }[];
};

export type RoiAnalytics = {
  hours_saved_month: number;
  dollars_saved_month: number;
  fraud_prevented_ytd: number;
  roi_multiplier: number;
  touchless_rate: number;
  avg_processing_time_seconds: number;
  pending_reviews: number;
};

export type ClientItem = {
  id: string;
  name: string;
  domain: string | null;
  email: string | null;
  phone: string | null;
  city: string | null;
  country: string | null;
  trust_score: number | null;
  invoice_count: number;
  spend_ytd: number;
  risk_level: string;
};

export type ExceptionItem = {
  id: string;
  invoice_id: string;
  invoice_number: string | null;
  status: string;
  reason: string;
  risk_level: string;
  ai_suggestion: string | null;
};

export type NotificationItem = {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};
