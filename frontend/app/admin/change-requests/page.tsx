"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch, ChangeRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const STATUS_LABELS: Record<ChangeRequest["status"], string> = {
  PENDING_REVIEW: "待審核",
  APPROVED: "已核准",
  REJECTED: "已駁回",
  WITHDRAWN: "已撤回",
};

export default function AdminChangeRequestsPage() {
  const { session, role } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<ChangeRequest[]>([]);
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session || role !== "Admin") return;
    setItems(await apiFetch<ChangeRequest[]>("/change-requests?pending_only=true", {}, session.access_token));
  }, [role, session]);

  useEffect(() => { load().catch((error) => setMessage(error.message)); }, [load]);
  useEffect(() => { if (role && role !== "Admin") router.replace("/dashboard"); }, [role, router]);

  async function review(event: FormEvent, id: number, approved: boolean) {
    event.preventDefault();
    if (!session) return;
    const reason = reasons[id]?.trim();
    if (!reason) { setMessage("請填寫審核說明。"); return; }
    try {
      await apiFetch(`/change-requests/${id}/review`, { method: "POST", body: JSON.stringify({ approved, reason }) }, session.access_token);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "審核申請失敗。"); }
  }

  if (role && role !== "Admin") return null;

  return (
    <RequireAuth>
      <AppShell>
        <section className="space-y-4">
          <div><h2 className="text-xl font-semibold">管理員審核中心</h2><p className="text-sm text-[rgb(var(--muted))]">此頁僅限管理員使用；核准或駁回時必須留下審核說明。</p></div>
          {message && <p className="text-sm">{message}</p>}
          {items.map((item) => (
            <form className="card-panel space-y-3 p-4" key={item.id}>
              <div className="flex flex-wrap justify-between gap-2"><strong>#{item.id} {item.target_type} {item.action}</strong><span>{STATUS_LABELS[item.status]}</span></div>
              <p className="text-sm">申請人：{item.requester_id}{item.target_id ? `・目標 ID：${item.target_id}` : ""}</p>
              <pre className="overflow-auto rounded bg-slate-500/10 p-3 text-xs">{JSON.stringify(item.payload_json, null, 2)}</pre>
              <textarea className="w-full rounded border p-2 text-sm" placeholder="請填寫審核說明（必填）" value={reasons[item.id] ?? ""} onChange={(e) => setReasons({ ...reasons, [item.id]: e.target.value })} />
              <div className="flex gap-2"><button className="rounded bg-emerald-600 px-3 py-2 text-sm text-white" onClick={(e) => review(e, item.id, true)}>核准</button><button className="rounded bg-red-600 px-3 py-2 text-sm text-white" onClick={(e) => review(e, item.id, false)}>駁回</button></div>
            </form>
          ))}
          {items.length === 0 && <p className="text-sm text-[rgb(var(--muted))]">目前沒有待審資產申請。</p>}
        </section>
      </AppShell>
    </RequireAuth>
  );
}
