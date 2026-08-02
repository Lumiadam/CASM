"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardCheck, LayoutDashboard, ListChecks, LogOut, Moon, Shield, Sun, Wrench } from "lucide-react";
import { useTheme } from "next-themes";

import { useAuth } from "@/lib/auth-context";

const nav = [
  { href: "/dashboard", label: "資產與預約", icon: LayoutDashboard },
  { href: "/my-reservations", label: "我的預約", icon: ListChecks },
  { href: "/my-assets", label: "我的保管資產", icon: ClipboardCheck },
  { href: "/maintenance", label: "報修與維護", icon: Wrench },
  { href: "/change-requests", label: "我的資產申請", icon: ClipboardCheck },
  { href: "/approvals", label: "預約審核", icon: ClipboardCheck },
  { href: "/admin/management", label: "資產與預約管理", icon: ClipboardCheck },
  { href: "/admin/change-requests", label: "Admin 審核中心", icon: Shield },
  { href: "/permissions", label: "權限說明", icon: Shield },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { session, logout, role, hasPermission } = useAuth();
  const { theme, setTheme } = useTheme();
  const visible = nav.filter((item) => {
    if (item.href === "/admin/change-requests" || item.href === "/admin/management") return role === "Admin";
    if (item.href === "/change-requests") return role !== "Admin";
    if (item.href === "/my-assets") return role !== "Employee";
    if (item.href === "/approvals") return hasPermission("approve_custodian_assets") || hasPermission("approve_any_reservation");
    return true;
  });
  return <div className="min-h-screen flex flex-col">
    <header className="border-b border-[rgb(var(--border))] bg-[rgb(var(--card))]/80 backdrop-blur sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center gap-4 justify-between">
        <div><p className="text-xs uppercase tracking-widest text-[rgb(var(--muted))]">CASMS</p><h1 className="font-semibold text-lg">資產、空間與設施管理系統</h1></div>
        <div className="flex items-center gap-3 text-sm">
          {session && <span className="px-2 py-1 rounded-md bg-sky-500/10 text-sky-600 border border-sky-500/30">{session.name} · {role}</span>}
          <button type="button" aria-label="切換主題" className="p-2 rounded-lg border border-[rgb(var(--border))]" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button type="button" onClick={logout} className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-[rgb(var(--border))] text-red-600"><LogOut size={16} />登出</button>
        </div>
      </div>
      <nav className="max-w-6xl mx-auto px-4 pb-2 flex flex-wrap gap-2">{visible.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition ${pathname === href ? "border-sky-500/50 bg-sky-500/10 text-sky-700" : "border-transparent hover:border-[rgb(var(--border))]"}`}><Icon size={16} />{label}</Link>)}</nav>
    </header>
    <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">{children}</main>
  </div>;
}
