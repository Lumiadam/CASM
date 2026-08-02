"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PermissionGate } from "@/components/PermissionGate";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch, Reservation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function ApprovalsPage() {
  const { session, hasPermission } = useAuth();
  const [pending, setPending] = useState<Reservation[]>([]);
  const [approved, setApproved] = useState<Reservation[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [damageDesc, setDamageDesc] = useState("");
  const [availability, setAvailability] = useState("PARTIALLY_USABLE");
  const [returnId, setReturnId] = useState<number | null>(null);
  const [registerDamage, setRegisterDamage] = useState(false);

  const load = useCallback(async () => {
    if (!session) return;
    const token = session.access_token;
    const pendingList = await apiFetch<Reservation[]>(
      "/reservations?pending_for_custodian=true",
      {},
      token
    ).catch(() => [] as Reservation[]);
    const all = await apiFetch<Reservation[]>("/reservations", {}, token);
    setPending(pendingList);
    setApproved(all.filter((r) => r.approval_status === "APPROVED"));
  }, [session]);

  useEffect(() => {
    load().catch((e) => setMsg(e.message));
  }, [load]);

  async function approve(id: number, action: "approve" | "reject") {
    if (!session) return;
    setMsg(null);
    try {
      await apiFetch(
        `/reservations/${id}/approve`,
        { method: "POST", body: JSON.stringify({ action }) },
        session.access_token
      );
      setMsg(action === "approve" ? "已核准" : "已拒絕");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "操作失敗");
    }
  }

  async function doReturn(id: number) {
    if (!session) return;
    setMsg(null);
    try {
      await apiFetch(
        `/reservations/${id}/return`,
        {
          method: "POST",
          body: JSON.stringify({
            register_damage: registerDamage,
            damage_description: registerDamage ? damageDesc : null,
            availability: registerDamage ? availability : null,
          }),
        },
        session.access_token
      );
      setMsg(registerDamage ? "已歸還並登記損壞，資產鎖定維護中" : "已驗收歸還");
      setReturnId(null);
      setRegisterDamage(false);
      setDamageDesc("");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "歸還失敗");
    }
  }

  const canAct =
    hasPermission("approve_custodian_assets") || hasPermission("approve_any_reservation");

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">保管人審核控制艙</h2>
            <p className="text-sm text-[rgb(var(--muted))]">
              Custodian 僅能審核自己保管的資產；Admin 可審核全部。Employee 可進入本頁檢視 RBAC
              差異（操作按鈕依權限停用）。
            </p>
          </div>
          {!canAct && (
            <div className="card-panel p-4 text-sm text-amber-700 dark:text-amber-200 border-amber-500/30">
              您目前為 Employee：可檢視待審／借用中列表，但無法執行核准或歸還（請切換保管人或 Admin
              帳號操作）。
            </div>
          )}
          {msg && <p className="text-sm text-[rgb(var(--muted))]">{msg}</p>}
          <section className="space-y-3">
            <h3 className="font-medium">待審核申請</h3>
            {pending.length === 0 && (
              <p className="text-sm text-[rgb(var(--muted))]">目前無待審項目</p>
            )}
            {pending.map((r) => (
              <div key={r.id} className="card-panel p-4 flex flex-wrap gap-3 justify-between">
                <div>
                  <p className="font-medium">
                    #{r.id} {r.asset_name}
                  </p>
                  <p className="text-xs text-[rgb(var(--muted))]">
                    {r.borrower_name} · {new Date(r.start_time).toLocaleString()} —{" "}
                    {new Date(r.end_time).toLocaleString()}
                  </p>
                  <p className="text-sm mt-1">{r.purpose}</p>
                  <StatusBadge status={r.approval_status} />
                </div>
                <PermissionGate permission="approve_custodian_assets">
                  <div className="flex gap-2 items-start">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-sm"
                      onClick={() => approve(r.id, "approve")}
                    >
                      <Check size={16} /> 核准
                    </button>
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-600/90 text-white text-sm"
                      onClick={() => approve(r.id, "reject")}
                    >
                      <X size={16} /> 拒絕
                    </button>
                  </div>
                </PermissionGate>
              </div>
            ))}
          </section>
          <section className="space-y-3">
            <h3 className="font-medium">借用中 · 驗收歸還</h3>
            {approved.map((r) => (
              <div key={r.id} className="card-panel p-4 space-y-3">
                <div className="flex justify-between flex-wrap gap-2">
                  <div>
                    <p className="font-medium">
                      #{r.id} {r.asset_name} — {r.borrower_name}
                    </p>
                    <StatusBadge status={r.approval_status} />
                  </div>
                  <PermissionGate permission="return_checkout">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border border-[rgb(var(--border))]"
                      onClick={() => setReturnId(returnId === r.id ? null : r.id)}
                    >
                      <RotateCcw size={16} /> 辦理歸還
                    </button>
                  </PermissionGate>
                </div>
                {returnId === r.id && (
                  <PermissionGate permission="return_checkout">
                    <div className="border-t border-[rgb(var(--border))] pt-3 space-y-2 text-sm">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={registerDamage}
                          onChange={(e) => setRegisterDamage(e.target.checked)}
                        />
                        登記損壞／缺件（將資產鎖定 MAINTENANCE）
                      </label>
                      {registerDamage && (
                        <>
                          <textarea
                            className="w-full rounded border border-[rgb(var(--border))] bg-transparent p-2"
                            placeholder="損壞描述"
                            value={damageDesc}
                            onChange={(e) => setDamageDesc(e.target.value)}
                          />
                          <label className="text-sm">可用性<select
                            className="rounded border border-[rgb(var(--border))] bg-transparent px-2 py-1"
                            value={availability}
                            onChange={(e) => setAvailability(e.target.value)}
                          >
                            <option value="USABLE">可使用</option>
                            <option value="PARTIALLY_USABLE">部分可使用</option>
                            <option value="UNUSABLE">不可使用</option>
                          </select></label>
                        </>
                      )}
                      <button
                        type="button"
                        onClick={() => doReturn(r.id)}
                        className="px-3 py-1.5 rounded-lg bg-sky-600 text-white"
                      >
                        確認歸還
                      </button>
                    </div>
                  </PermissionGate>
                )}
              </div>
            ))}
          </section>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
