"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ClipboardCheck,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Moon,
  Shield,
  Sun,
} from "lucide-react";
import { useTheme } from "next-themes";

import { useAuth } from "@/lib/auth-context";

const nav = [
  { href: "/dashboard", label: "資產總覽", icon: LayoutDashboard },
  { href: "/approvals", label: "保管人審核", icon: ClipboardCheck },
  { href: "/my-reservations", label: "個人借用", icon: ListChecks },
  { href: "/permissions", label: "權限矩陣", icon: Shield },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { session, logout, role, hasPermission } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[rgb(var(--border))] bg-[rgb(var(--card))]/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center gap-4 justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[rgb(var(--muted))]">CASMS</p>
            <h1 className="font-semibold text-lg">企業資產與空間管理控制艙</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {session && (
              <span className="px-2 py-1 rounded-md bg-sky-500/10 text-sky-600 dark:text-sky-300 border border-sky-500/30">
                {session.name} · {role}
              </span>
            )}
            <button
              type="button"
              aria-label="切換主題"
              className="p-2 rounded-lg border border-[rgb(var(--border))] hover:bg-slate-500/10"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-[rgb(var(--border))] hover:bg-red-500/10 text-red-600 dark:text-red-300"
            >
              <LogOut size={16} /> 登出
            </button>
          </div>
        </div>
        <nav className="max-w-6xl mx-auto px-4 pb-2 flex flex-wrap gap-2">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            const restricted =
              href === "/approvals" &&
              !hasPermission("approve_custodian_assets") &&
              !hasPermission("approve_any_reservation");
            return (
              <Link
                key={href}
                href={href}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition ${
                  active
                    ? "border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-200"
                    : "border-transparent hover:border-[rgb(var(--border))] hover:bg-slate-500/5"
                } ${restricted ? "opacity-80" : ""}`}
                title={restricted ? "可進入檢視，部分操作依 RBAC 停用" : undefined}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">{children}</main>
    </div>
  );
}
