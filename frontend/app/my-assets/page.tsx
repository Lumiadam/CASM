"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch, Asset } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function MyAssetsPage() {
  const { session, role } = useAuth();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selected, setSelected] = useState<Asset | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (!session) return;
    const all = await apiFetch<Asset[]>("/assets?include_archived=true", {}, session.access_token);
    setAssets(role === "Admin" ? all : all.filter((asset) => asset.custodian_id === session.user_id));
  }, [role, session]);
  useEffect(() => { load().catch((error) => setMessage(error.message)); }, [load]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !selected) return;
    const form = new FormData(event.currentTarget);
    try {
      await apiFetch(`/assets/${selected.id}`, { method: "PUT", body: JSON.stringify({ name: form.get("name"), location: form.get("location") || null, reservation_locked: form.get("reservation_locked") === "on", next_maintenance_at: form.get("next_maintenance_at") || null }) }, session.access_token);
      setMessage("資產設定已更新。"); setSelected(null); await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "更新失敗"); }
  }
  return <RequireAuth><AppShell><div className="space-y-5"><div><h2 className="text-xl font-semibold">我的保管資產</h2><p className="text-sm text-[rgb(var(--muted))]">Custodian 僅能管理自己保管的資產；Admin 可查看全部資產。</p></div>{message && <p className="text-sm">{message}</p>}<div className="grid gap-4 md:grid-cols-2">{assets.map((asset) => <button key={asset.id} type="button" className="card-panel p-4 text-left" onClick={() => setSelected(asset)}><div className="flex justify-between"><strong>{asset.name}</strong><StatusBadge status={asset.status} /></div><p className="text-xs text-[rgb(var(--muted))]">{asset.asset_code} · {asset.location || "未設定位置"}</p><p className="mt-2 text-xs">{asset.reservation_locked ? "🔒 預約已鎖定" : "可接受預約"}</p></button>)}</div>{selected && <form onSubmit={save} className="card-panel p-5 space-y-3"><h3 className="font-semibold">調整：{selected.name}</h3><label className="block text-sm">名稱<input name="name" defaultValue={selected.name} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">位置<input name="location" defaultValue={selected.location || ""} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">下次保養日<input name="next_maintenance_at" type="datetime-local" defaultValue={selected.next_maintenance_at?.slice(0, 16) || ""} className="mt-1 w-full rounded border p-2" /></label><label className="flex gap-2 text-sm"><input name="reservation_locked" type="checkbox" defaultChecked={selected.reservation_locked} />鎖定預約</label><div className="flex gap-2"><button className="rounded bg-sky-600 px-4 py-2 text-sm text-white">儲存</button><button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => setSelected(null)}>取消</button></div></form>}</div></AppShell></RequireAuth>;
}
