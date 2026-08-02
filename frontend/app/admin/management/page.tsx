"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch, Asset, Reservation, UserSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const emptyAsset = { asset_code: "", name: "", type: "DEVICE", category: "", custodian_id: "", status: "AVAILABLE" };
const emptyReservation = { asset_id: "", borrower_id: "", start_time: "", end_time: "", purpose: "", approval_status: "PENDING" };

export default function AdminManagementPage() {
  const { session, role } = useAuth();
  const router = useRouter();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [assetForm, setAssetForm] = useState(emptyAsset);
  const [reservationForm, setReservationForm] = useState(emptyReservation);
  const [editingAsset, setEditingAsset] = useState<number | null>(null);
  const [editingReservation, setEditingReservation] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session || role !== "Admin") return;
    const [assetList, reservationList, userList] = await Promise.all([
      apiFetch<Asset[]>("/assets?include_archived=true", {}, session.access_token),
      apiFetch<Reservation[]>("/reservations", {}, session.access_token),
      apiFetch<UserSummary[]>("/users", {}, session.access_token),
    ]);
    setAssets(assetList); setReservations(reservationList); setUsers(userList);
  }, [role, session]);

  useEffect(() => { load().catch((error) => setMessage(error.message)); }, [load]);
  useEffect(() => { if (role && role !== "Admin") router.replace("/dashboard"); }, [role, router]);

  function selectAsset(asset: Asset) {
    setEditingAsset(asset.id);
    setAssetForm({ asset_code: asset.asset_code, name: asset.name, type: asset.type, category: asset.category || "", custodian_id: asset.custodian_id?.toString() || "", status: asset.status });
  }

  function selectReservation(item: Reservation) {
    setEditingReservation(item.id);
    setReservationForm({ asset_id: item.asset_id.toString(), borrower_id: item.borrower_id.toString(), start_time: item.start_time.slice(0, 16), end_time: item.end_time.slice(0, 16), purpose: item.purpose, approval_status: item.approval_status });
  }

  async function saveAsset(event: FormEvent) {
    event.preventDefault(); if (!session) return;
    const body = { ...assetForm, custodian_id: assetForm.custodian_id ? Number(assetForm.custodian_id) : null };
    try {
      await apiFetch(editingAsset ? `/assets/${editingAsset}` : "/assets", { method: editingAsset ? "PUT" : "POST", body: JSON.stringify(body) }, session.access_token);
      setMessage(editingAsset ? "資產已更新。" : "資產已新增。"); setEditingAsset(null); setAssetForm(emptyAsset); await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "儲存資產失敗。"); }
  }

  async function archiveAsset(id: number) {
    if (!session || !confirm("封存後將取消該資產的待審與已核准預約，是否繼續？")) return;
    try { await apiFetch(`/assets/${id}/archive`, { method: "POST" }, session.access_token); setMessage("資產已封存。"); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "封存資產失敗。"); }
  }

  async function saveReservation(event: FormEvent) {
    event.preventDefault(); if (!session) return;
    const body = { ...reservationForm, asset_id: Number(reservationForm.asset_id), borrower_id: Number(reservationForm.borrower_id), start_time: new Date(reservationForm.start_time).toISOString(), end_time: new Date(reservationForm.end_time).toISOString() };
    try {
      await apiFetch(editingReservation ? `/reservations/${editingReservation}` : "/reservations", { method: editingReservation ? "PUT" : "POST", body: JSON.stringify(body) }, session.access_token);
      setMessage(editingReservation ? "預約已更新。" : "預約已新增。"); setEditingReservation(null); setReservationForm(emptyReservation); await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "儲存預約失敗。"); }
  }

  if (role && role !== "Admin") return null;
  return <RequireAuth><AppShell><div className="space-y-8">
    <div><h2 className="text-xl font-semibold">資產與預約管理</h2><p className="text-sm text-[rgb(var(--muted))]">僅限管理員直接新增、調整、封存資產及編輯預約；開始日期早於今日的預約會標示為後期添加補件。</p></div>
    {message && <p className="text-sm">{message}</p>}
    <section className="grid gap-5 lg:grid-cols-2"><form className="card-panel space-y-3 p-5" onSubmit={saveAsset}>
      <h3 className="font-semibold">{editingAsset ? "編輯資產" : "新增資產"}</h3>
      <label className="block text-sm">名稱<input required className="mt-1 w-full rounded border p-2" value={assetForm.name} onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })} /></label>
      <label className="block text-sm">編號<input required className="mt-1 w-full rounded border p-2" value={assetForm.asset_code} onChange={(e) => setAssetForm({ ...assetForm, asset_code: e.target.value })} /></label>
      <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">類型<select className="mt-1 w-full rounded border p-2" value={assetForm.type} onChange={(e) => setAssetForm({ ...assetForm, type: e.target.value })}><option value="DEVICE">設備</option><option value="SPACE">空間</option><option value="FACILITY">設施</option></select></label><label className="text-sm">分類<input className="mt-1 w-full rounded border p-2" value={assetForm.category} onChange={(e) => setAssetForm({ ...assetForm, category: e.target.value })} /></label></div>
      <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">保管人<select className="mt-1 w-full rounded border p-2" value={assetForm.custodian_id} onChange={(e) => setAssetForm({ ...assetForm, custodian_id: e.target.value })}><option value="">未指派</option>{users.map((user) => <option key={user.id} value={user.id}>{user.name}（{user.role}）</option>)}</select></label><label className="text-sm">狀態<select className="mt-1 w-full rounded border p-2" value={assetForm.status} onChange={(e) => setAssetForm({ ...assetForm, status: e.target.value })}><option value="AVAILABLE">可用</option><option value="MAINTENANCE">維護中</option><option value="RETIRED">已封存</option></select></label></div>
      <div className="flex gap-2"><button className="rounded bg-sky-600 px-4 py-2 text-sm text-white">儲存資產</button>{editingAsset && <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => { setEditingAsset(null); setAssetForm(emptyAsset); }}>取消編輯</button>}</div>
    </form><div className="card-panel p-5"><h3 className="font-semibold">資產清單</h3><div className="mt-3 max-h-[520px] space-y-2 overflow-auto">{assets.map((asset) => <div className="rounded border p-3 text-sm" key={asset.id}><div className="flex justify-between gap-3"><strong>{asset.name}</strong><span>{asset.status}</span></div><p className="text-xs text-[rgb(var(--muted))]">{asset.asset_code}・{asset.category || "未分類"}</p><div className="mt-2 flex gap-2"><button className="rounded border px-2 py-1 text-xs" onClick={() => selectAsset(asset)}>編輯</button>{asset.status !== "RETIRED" && <button className="rounded border border-red-300 px-2 py-1 text-xs text-red-600" onClick={() => archiveAsset(asset.id)}>封存</button>}</div></div>)}</div></div></section>
    <section className="grid gap-5 lg:grid-cols-2"><form className="card-panel space-y-3 p-5" onSubmit={saveReservation}>
      <h3 className="font-semibold">{editingReservation ? "編輯預約" : "新增預約"}</h3>
      <label className="block text-sm">資產<select required className="mt-1 w-full rounded border p-2" value={reservationForm.asset_id} onChange={(e) => setReservationForm({ ...reservationForm, asset_id: e.target.value })}><option value="">請選擇資產</option>{assets.filter((asset) => asset.status !== "RETIRED").map((asset) => <option key={asset.id} value={asset.id}>{asset.name}（{asset.asset_code}）</option>)}</select></label>
      <label className="block text-sm">借用人<select required className="mt-1 w-full rounded border p-2" value={reservationForm.borrower_id} onChange={(e) => setReservationForm({ ...reservationForm, borrower_id: e.target.value })}><option value="">請選擇借用人</option>{users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}</select></label>
      <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">開始時間<input required type="datetime-local" className="mt-1 w-full rounded border p-2" value={reservationForm.start_time} onChange={(e) => setReservationForm({ ...reservationForm, start_time: e.target.value })} /></label><label className="text-sm">結束時間<input required type="datetime-local" className="mt-1 w-full rounded border p-2" value={reservationForm.end_time} onChange={(e) => setReservationForm({ ...reservationForm, end_time: e.target.value })} /></label></div>
      <label className="block text-sm">用途<input required className="mt-1 w-full rounded border p-2" value={reservationForm.purpose} onChange={(e) => setReservationForm({ ...reservationForm, purpose: e.target.value })} /></label>
      {editingReservation && <label className="block text-sm">狀態<select className="mt-1 w-full rounded border p-2" value={reservationForm.approval_status} onChange={(e) => setReservationForm({ ...reservationForm, approval_status: e.target.value })}><option value="PENDING">待審</option><option value="APPROVED">已核准</option><option value="REJECTED">已駁回</option><option value="CANCELLED">已取消</option></select></label>}
      <div className="flex gap-2"><button className="rounded bg-sky-600 px-4 py-2 text-sm text-white">儲存預約</button>{editingReservation && <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => { setEditingReservation(null); setReservationForm(emptyReservation); }}>取消編輯</button>}</div>
    </form><div className="card-panel p-5"><h3 className="font-semibold">預約清單</h3><div className="mt-3 max-h-[520px] space-y-2 overflow-auto">{reservations.map((item) => <div className="rounded border p-3 text-sm" key={item.id}><div className="flex justify-between gap-3"><strong>{item.asset_name}</strong><span>{item.approval_status}</span></div><p className="text-xs text-[rgb(var(--muted))]">{item.borrower_name}・{new Date(item.start_time).toLocaleString()}</p>{item.is_supplemental && <p className="mt-1 text-xs text-amber-600">後期添加補件申請</p>}<button className="mt-2 rounded border px-2 py-1 text-xs" onClick={() => selectReservation(item)}>編輯</button></div>)}</div></div></section>
  </div></AppShell></RequireAuth>;
}
