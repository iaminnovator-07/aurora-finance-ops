import { type ReactNode } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useRouter, useLocation } from "@tanstack/react-router";
import { useEffect } from "react";
import { ThinkingDots } from "@/components/ui-bits";

export function AuthGate({ children }: { children: ReactNode }) {
  const { auth, isLoading } = useAuth();
  const router = useRouter();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && !auth) {
      const publicRoutes = ["/", "/login"];
      if (!publicRoutes.includes(location.pathname)) {
        router.navigate({ to: "/login", replace: true });
      }
    }
  }, [isLoading, auth, location.pathname, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="text-center space-y-3">
          <div className="h-12 w-12 mx-auto rounded-xl grid place-items-center" style={{ background: "var(--gradient-aurora)" }}>
            <span className="text-white text-lg font-bold">A</span>
          </div>
          <p className="text-sm text-muted-foreground inline-flex items-center gap-2">
            Connecting to Aurora <ThinkingDots />
          </p>
        </div>
      </div>
    );
  }

  // If not loading, and not authenticated, and trying to access protected route, render nothing while redirecting
  if (!auth) {
    const publicRoutes = ["/", "/login"];
    if (!publicRoutes.includes(location.pathname)) {
       return null;
    }
  }

  return <>{children}</>;
}
