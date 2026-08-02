"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch, ChangeRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const STATUS_LABELS: Record<ChangeRequest["status"], string> = {
  PENDING_REVIEW: "待管理員審核",
  APPROVED: "已核准",
  REJECTED: "已駁回",
  WITHDRAWN: "已撤回",
};

export default function ChangeRequestsPage() {
  const { session, role } = useAuth();
  const [items, setItems] = useState<ChangeRequest[]>([]);
  const [assetCode, setAssetCode] = useState("");
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("DEVICE");
  const [category, setCategory] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) return;
    setItems(await apiFetch<ChangeRequest[]>("/change-requests?mine=true", {}, session.access_token));
  }, [session]);

  useEffect(() => { load().catch((error) => setMessage(error.message)); }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    try {
      await apiFetch<ChangeRequest>(
        "/change-requests",
        {
          method: "POST",
          body: JSON.stringify({
            target_type: "ASSET",
            action: "CREATE",
            payload_json: { asset_code: assetCode, name, type: assetType, category: category || null },
          }),
        },
        session.access_token
      );
      setMessage("資產申請已送出，請等待管理員審核。");
      setAssetCode(""); setName(""); setCategory("");
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "申請送出失敗。"); }
  }

  async function withdraw(id: number) {
    if (!session) return;
    try {
      await apiFetch(`/change-requests/${id}/withdraw`, { method: "POST" }, session.access_token);
      setMessage("申請已撤回。");
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "撤回申請失敗。"); }
  }

  return (
    <RequireAuth><AppShell><div className="grid gap-6 lg:grid-cols-2">
      <section className="card-panel p-5">
        <h2 className="text-xl font-semibold">我的資產申請</h2>
        {role === "Admin" ? (
          <p className="mt-3 text-sm text-[rgb(var(--muted))]">管理員可直接管理資產與預約。<Link className="ml-1 text-sky-600 underline" href="/admin/management">前往資產與預約管理</Link></p>
        ) : <form className="mt-5 space-y-3" onSubmit={submit}>
          <label className="block text-sm">資產名稱<input required className="mt-1 w-full rounded border p-2" value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label className="block text-sm">資產編號<input required className="mt-1 w-full rounded border p-2" value={assetCode} onChange={(e) => setAssetCode(e.target.value)} /></label>
          <label className="block text-sm">資產類型<select className="mt-1 w-full rounded border p-2" value={assetType} onChange={(e) => setAssetType(e.target.value)}><option value="DEVICE">設備</option><option value="SPACE">空間</option><option value="FACILITY">設施</option></select></label>
          <label className="block text-sm">分類<input className="mt-1 w-full rounded border p-2" placeholder="例如：會議設備、教室、空調" value={category} onChange={(e) => setCategory(e.target.value)} /></label>
          <button className="rounded bg-sky-600 px-4 py-2 text-sm text-white" type="submit">送出資產申請</button>
        </form>}
        {message && <p className="mt-3 text-sm">{message}</p>}
      </section>
      <section className="card-panel p-5"><h2 className="text-xl font-semibold">申請狀態</h2><p className="mt-1 text-sm text-[rgb(var(--muted))]">僅顯示您本人提出的資產申請。</p><div className="mt-4 space-y-3">
        {items.map((item) => <div className="rounded border border-[rgb(var(--border))] p-3 text-sm" key={item.id}><div className="flex justify-between gap-3"><span>{item.payload_json.name as string || "資產申請"}</span><span>{STATUS_LABELS[item.status]}</span></div><p className="mt-1 text-xs text-[rgb(var(--muted))]">申請編號 #{item.id}・{item.payload_json.asset_code as string || "未填寫編號"}</p>{item.review_reason && <p className="mt-2">審核說明：{item.review_reason}</p>}{role !== "Admin" && item.status === "PENDING_REVIEW" && <button className="mt-3 rounded border px-3 py-1 text-xs" type="button" onClick={() => withdraw(item.id)}>撤回申請</button>}</div>)}
        {items.length === 0 && <p className="text-sm text-[rgb(var(--muted))]">目前沒有您提出的資產申請。</p>}
      </div></section>
    </div></AppShell></RequireAuth>
  );
}
