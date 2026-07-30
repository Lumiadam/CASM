"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";

/** 展示階段：未登入導向登入；已登入則允許進入各頁（含權限展示頁） */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, session, router]);

  if (loading || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center text-[rgb(var(--muted))]">
        驗證工作階段…
      </div>
    );
  }

  return <>{children}</>;
}
