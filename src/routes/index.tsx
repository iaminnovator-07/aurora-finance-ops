import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { ArrowRight, Bot, Shield, Zap, CheckCircle2, ChevronRight, BarChart3, ScanLine } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

function LandingPage() {
  const { auth } = useAuth();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col relative overflow-hidden">
      {/* Dynamic Background Effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[color:var(--primary)]/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-[color:var(--ai)]/20 blur-[120px] pointer-events-none" />

      {/* Navbar */}
      <header className="px-6 py-4 flex items-center justify-between relative z-10 border-b border-border/50 glass">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: "var(--gradient-aurora)" }}>
            <span className="text-white text-xl font-bold">A</span>
          </div>
          <span className="text-xl font-bold tracking-tight">Aurora TIA</span>
        </div>
        <div className="flex items-center gap-4">
          {auth ? (
            <Link
              to="/dashboard"
              className="px-5 py-2 rounded-full bg-primary text-primary-foreground font-medium text-sm transition hover-glow flex items-center gap-2"
            >
              Go to Dashboard <ArrowRight className="h-4 w-4" />
            </Link>
          ) : (
            <Link
              to="/login"
              className="px-5 py-2 rounded-full bg-primary text-primary-foreground font-medium text-sm transition hover-glow"
            >
              Log In
            </Link>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20 relative z-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[color:var(--ai)]/30 bg-[color:var(--ai)]/5 text-[color:var(--ai)] text-sm font-medium mb-8">
          <Bot className="h-4 w-4" /> Meet your AI-powered Touchless Invoice Agent
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight max-w-4xl leading-tight mb-6">
          The Future of <span className="text-gradient">Finance Operations</span> is Autonomous
        </h1>
        
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed">
          Aurora TIA ingests, verifies, and processes invoices with zero human touch. 
          Powered by state-of-the-art AI, we automate data extraction, rule checking, and ERP sync.
        </p>

        <div className="flex items-center gap-4 flex-wrap justify-center">
          <Link
            to={auth ? "/dashboard" : "/login"}
            className="h-14 px-8 rounded-full bg-primary text-primary-foreground font-semibold text-lg transition hover-glow flex items-center gap-2"
          >
            Get Started <ArrowRight className="h-5 w-5" />
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full mt-24">
          <div className="glass p-6 rounded-2xl text-left border border-border/50">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4">
              <ScanLine className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Omnichannel Ingestion</h3>
            <p className="text-sm text-muted-foreground">Automatically fetch emails, extract attachments, and read PDFs, Excel files, and even handwritten documents.</p>
          </div>

          <div className="glass p-6 rounded-2xl text-left border border-border/50">
            <div className="h-12 w-12 rounded-xl bg-[color:var(--ai)]/10 text-[color:var(--ai)] flex items-center justify-center mb-4">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Trust & Validation</h3>
            <p className="text-sm text-muted-foreground">Run intense validation on vendors, detect duplicates, and evaluate custom business rules for auto-approval.</p>
          </div>

          <div className="glass p-6 rounded-2xl text-left border border-border/50">
            <div className="h-12 w-12 rounded-xl bg-success/10 text-success flex items-center justify-center mb-4">
              <BarChart3 className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Instant ERP Sync</h3>
            <p className="text-sm text-muted-foreground">Successfully processed invoices are instantly normalized and synchronized to your ERP system without manual data entry.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
