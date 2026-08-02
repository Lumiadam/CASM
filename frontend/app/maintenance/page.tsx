"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch, Asset, WorkOrder } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const initialForm = { asset_id: "", issue_type: "", description: "", severity: "MEDIUM", photo_url: "" };

export default function MaintenancePage() {
  const { session, role } = useAuth();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [form, setForm] = useState(initialForm);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) return;
    const [assetList, orderList] = await Promise.all([
      apiFetch<Asset[]>("/assets", {}, session.access_token),
      apiFetch<WorkOrder[]>(role === "Employee" ? "/maintenance/work-orders?mine=true" : "/maintenance/work-orders", {}, session.access_token),
    ]);
    setAssets(assetList); setOrders(orderList);
  }, [role, session]);
  useEffect(() => { load().catch((error) => setMessage(error.message)); }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!session) return;
    try {
      await apiFetch("/maintenance/work-orders", { method: "POST", body: JSON.stringify({ ...form, asset_id: Number(form.asset_id), photo_url: form.photo_url || null }) }, session.access_token);
      setForm(initialForm); setMessage("報修已送出，可在此頁追蹤處理進度。"); await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "送出失敗"); }
  }

  async function setStatus(id: number, status: string) {
    if (!session) return;
    try {
      await apiFetch(`/maintenance/work-orders/${id}`, { method: "PUT", body: JSON.stringify({ status }) }, session.access_token);
      setMessage("工單狀態已更新。"); await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "更新失敗"); }
  }

  return <RequireAuth><AppShell><div className="space-y-6">
    <div><h2 className="text-xl font-semibold">報修與維護</h2><p className="text-sm text-[rgb(var(--muted))]">申報問題後依序進入審核、保固／維修、等待零件、驗證與結案；一般使用者僅能查看自己的工單。</p></div>
    {message && <p className="text-sm">{message}</p>}
    {role !== "Employee" && <form className="card-panel p-5 space-y-3" onSubmit={submit}>
      <h3 className="font-semibold">新增報修</h3>
      <div className="grid gap-3 md:grid-cols-2"><label className="text-sm">資產<select required className="mt-1 w-full rounded border p-2" value={form.asset_id} onChange={(e) => setForm({ ...form, asset_id: e.target.value })}><option value="">請選擇</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.name}（{asset.asset_code}）</option>)}</select></label><label className="text-sm">問題類型<input required className="mt-1 w-full rounded border p-2" value={form.issue_type} onChange={(e) => setForm({ ...form, issue_type: e.target.value })} placeholder="例如：無法開機、異音" /></label></div>
      <div className="grid gap-3 md:grid-cols-2"><label className="text-sm">嚴重度<select className="mt-1 w-full rounded border p-2" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}><option value="LOW">低</option><option value="MEDIUM">中</option><option value="HIGH">高</option></select></label><label className="text-sm">照片或說明連結（選填）<input className="mt-1 w-full rounded border p-2" value={form.photo_url} onChange={(e) => setForm({ ...form, photo_url: e.target.value })} /></label></div>
      <label className="block text-sm">問題說明<textarea required className="mt-1 w-full rounded border p-2" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      <button className="rounded bg-sky-600 px-4 py-2 text-sm text-white">送出報修</button>
    </form>}
    <section className="space-y-3"><h3 className="font-semibold">工單追蹤</h3>{orders.length === 0 ? <p className="text-sm text-[rgb(var(--muted))]">尚無工單。</p> : orders.map((order) => <article key={order.id} className="card-panel p-4"><div className="flex flex-wrap justify-between gap-2"><div><p className="font-medium">#{order.id} {order.asset_name}</p><p className="text-sm">{order.issue_type} · {order.severity}</p></div><StatusBadge status={order.status} /></div><p className="mt-2 text-sm">{order.description}</p><p className="mt-2 text-xs text-[rgb(var(--muted))]">申報人：{order.reporter_name || "-"}　零件：{order.parts.map((part) => `${part.name} × ${part.quantity}`).join("、") || "尚無"}</p>{role !== "Employee" && <div className="mt-3 flex flex-wrap gap-2"><button type="button" className="rounded border px-2 py-1 text-xs" onClick={() => setStatus(order.id, "IN_REPAIR")}>開始維修</button><button type="button" className="rounded border px-2 py-1 text-xs" onClick={() => setStatus(order.id, "WAITING_PARTS")}>等待零件</button><button type="button" className="rounded border px-2 py-1 text-xs" onClick={() => setStatus(order.id, "VERIFICATION")}>驗證</button><button type="button" className="rounded border px-2 py-1 text-xs" onClick={() => setStatus(order.id, "CLOSED")}>結案</button></div>}</article>)}</section>
  </div></AppShell></RequireAuth>;
}
