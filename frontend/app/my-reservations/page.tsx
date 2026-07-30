"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch, Reservation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function MyReservationsPage() {
  const { session } = useAuth();
  const [items, setItems] = useState<Reservation[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<Reservation[]>("/reservations?mine=true", {}, session.access_token)
      .then(setItems)
      .catch((e) => setMsg(e.message));
  }, [session]);

  async function cancel(id: number) {
    if (!session) return;
    try {
      await apiFetch(`/reservations/${id}/cancel`, { method: "POST" }, session.access_token);
      setMsg("已取消申請");
      const next = await apiFetch<Reservation[]>(
        "/reservations?mine=true",
        {},
        session.access_token
      );
      setItems(next);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "取消失敗");
    }
  }

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold">個人借用歷程</h2>
            <p className="text-sm text-[rgb(var(--muted))]">檢視申請進度與借用中項目</p>
          </div>
          {msg && <p className="text-sm text-[rgb(var(--muted))]">{msg}</p>}
          <div className="space-y-3">
            {items.map((r) => (
              <div key={r.id} className="card-panel p-4 flex flex-wrap justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {r.asset_name} (#{r.id})
                  </p>
                  <p className="text-xs text-[rgb(var(--muted))]">
                    {new Date(r.start_time).toLocaleString()} → {new Date(r.end_time).toLocaleString()}
                  </p>
                  <p className="text-sm mt-1">{r.purpose}</p>
                  <div className="mt-2">
                    <StatusBadge status={r.approval_status} />
                  </div>
                </div>
                {["PENDING", "APPROVED"].includes(r.approval_status) && (
                  <button
                    type="button"
                    onClick={() => cancel(r.id)}
                    className="text-sm px-3 py-1.5 rounded-lg border border-[rgb(var(--border))] hover:bg-red-500/10 text-red-600"
                  >
                    取消
                  </button>
                )}
              </div>
            ))}
            {items.length === 0 && (
              <p className="text-sm text-[rgb(var(--muted))]">尚無借用紀錄</p>
            )}
          </div>
        </div>
      </AppShell>
    </RequireAuth>
  );
}
