"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogIn } from "lucide-react";

import { TEST_ACCOUNTS } from "@/lib/constants";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login, session } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@casms.local");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (session) router.replace("/dashboard");
  }, [session, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登入失敗");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-slate-900 via-slate-800 to-sky-950 dark:from-slate-950 dark:via-slate-900 dark:to-sky-950">
      <div className="w-full max-w-md card-panel p-8 space-y-6">
        <div className="text-center space-y-1">
          <p className="text-xs tracking-widest uppercase text-[rgb(var(--muted))]">CASMS MVP</p>
          <h1 className="text-2xl font-bold">控制艙登入</h1>
          <p className="text-sm text-[rgb(var(--muted))]">企業資產 · 空間 · 設施借用管理</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm space-y-1">
            Email
            <input
              className="w-full rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </label>
          <label className="block text-sm space-y-1">
            密碼
            <input
              className="w-full rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </label>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white py-2.5 font-medium disabled:opacity-60"
          >
            <LogIn size={18} /> {submitting ? "登入中…" : "登入"}
          </button>
        </form>
        <div className="space-y-2">
          <p className="text-xs text-[rgb(var(--muted))] uppercase tracking-wide">快捷測試帳號</p>
          <div className="flex flex-col gap-2">
            {TEST_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                className="text-left text-sm px-3 py-2 rounded-lg border border-[rgb(var(--border))] hover:border-sky-500/40 hover:bg-sky-500/5"
                onClick={() => {
                  setEmail(acc.email);
                  setPassword(acc.password);
                }}
              >
                <span className="font-medium">{acc.label}</span>
                <span className="block text-xs text-[rgb(var(--muted))]">{acc.email}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
