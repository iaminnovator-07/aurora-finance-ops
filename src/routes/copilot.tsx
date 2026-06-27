import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, Card, PageHeader } from "@/components/app-layout";
import { Badge, ThinkingDots } from "@/components/ui-bits";
import { useState } from "react";
import { Send, Sparkles, Paperclip, Mic, FileText, Download, BarChart3 } from "lucide-react";
import { useCopilotChat } from "@/lib/api/hooks";

export const Route = createFileRoute("/copilot")({ component: Copilot });

const prompts = [
  "Show pending invoices over $10k",
  "Why was invoice INV-2378 rejected?",
  "Generate monthly fraud report",
  "Find duplicate invoices this week",
  "Which vendor has the highest fraud risk?",
];

type Message = { role: "user" | "ai"; content: string; data?: Record<string, unknown> };

function Copilot() {
  const chat = useCopilotChat();
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([
    { role: "ai", content: "Hi Anya — I'm Aurora Copilot. Ask me anything about invoices, vendors, fraud, or run a report." },
  ]);
  const [input, setInput] = useState("");

  const ask = (q: string) => {
    if (!q.trim() || chat.isPending) return;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    chat.mutate(
      { message: q, conversation_id: conversationId },
      {
        onSuccess: (res) => {
          setConversationId(res.conversation_id);
          setMessages((m) => [...m, { role: "ai", content: res.reply, data: res.data }]);
        },
        onError: () => {
          setMessages((m) => [...m, { role: "ai", content: "Sorry, I couldn't reach Aurora right now. Please try again." }]);
        },
      },
    );
  };

  return (
    <AppLayout>
      <PageHeader title="AI Copilot" subtitle="Ask Aurora in natural language." actions={<Badge tone="ai"><Sparkles className="h-3 w-3" /> Aurora v2.3</Badge>} />
      <div className="grid lg:grid-cols-[1fr_300px] gap-4">
        <Card className="!p-0 flex flex-col h-[calc(100vh-14rem)]">
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "ai" && <div className="h-8 w-8 rounded-lg grid place-items-center shrink-0" style={{ background: "var(--gradient-aurora)" }}><Sparkles className="h-4 w-4 text-white" /></div>}
                <div className={`max-w-[75%] ${m.role === "user" ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5" : "text-sm"}`}>
                  <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                  {m.data && Object.keys(m.data).length > 0 && (
                    <div className="mt-3 rounded-xl border border-border overflow-hidden">
                      <pre className="text-xs p-3 overflow-x-auto bg-muted/30">{JSON.stringify(m.data, null, 2)}</pre>
                      <div className="flex gap-2 p-2 border-t border-border">
                        <button className="text-xs px-3 py-1.5 rounded-lg bg-primary text-primary-foreground inline-flex items-center gap-1"><BarChart3 className="h-3 w-3"/> Visualize</button>
                        <button className="text-xs px-3 py-1.5 rounded-lg border border-border inline-flex items-center gap-1"><Download className="h-3 w-3"/> Export CSV</button>
                        <button className="text-xs px-3 py-1.5 rounded-lg border border-border">Open queue</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chat.isPending && (
              <div className="flex gap-3">
                <div className="h-8 w-8 rounded-lg grid place-items-center shrink-0" style={{ background: "var(--gradient-aurora)" }}><Sparkles className="h-4 w-4 text-white" /></div>
                <div className="text-sm text-muted-foreground inline-flex items-center gap-2">Aurora is thinking <ThinkingDots /></div>
              </div>
            )}
          </div>
          <div className="border-t border-border p-4">
            <div className="flex items-end gap-2 rounded-2xl border border-border bg-background/60 p-2 focus-within:ring-2 focus-within:ring-ring">
              <button className="h-9 w-9 grid place-items-center rounded-lg hover:bg-accent"><Paperclip className="h-4 w-4" /></button>
              <textarea
                rows={1} value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(input); } }}
                placeholder="Ask Aurora… e.g. show pending invoices > $10k"
                className="flex-1 bg-transparent text-sm focus:outline-none resize-none py-2 px-1"
                disabled={chat.isPending}
              />
              <button className="h-9 w-9 grid place-items-center rounded-lg hover:bg-accent"><Mic className="h-4 w-4" /></button>
              <button onClick={() => ask(input)} disabled={chat.isPending} className="h-9 w-9 grid place-items-center rounded-lg bg-primary text-primary-foreground disabled:opacity-50"><Send className="h-4 w-4" /></button>
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <h3 className="font-semibold text-sm mb-3">Suggested prompts</h3>
            <div className="space-y-2">
              {prompts.map((p) => (
                <button key={p} onClick={() => ask(p)} disabled={chat.isPending} className="w-full text-left text-xs p-2.5 rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition disabled:opacity-50">
                  {p}
                </button>
              ))}
            </div>
          </Card>
          <Card>
            <h3 className="font-semibold text-sm mb-3">Recent</h3>
            <div className="space-y-2 text-xs">
              {messages.filter((m) => m.role === "user").slice(-3).reverse().map((r, i) => (
                <button key={i} onClick={() => ask(r.content)} disabled={chat.isPending} className="w-full text-left p-2 rounded-lg hover:bg-accent flex items-center gap-2 text-muted-foreground hover:text-foreground disabled:opacity-50">
                  <FileText className="h-3.5 w-3.5" /> {r.content}
                </button>
              ))}
              {messages.filter((m) => m.role === "user").length === 0 && (
                <div className="text-muted-foreground p-2">No recent queries yet.</div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
