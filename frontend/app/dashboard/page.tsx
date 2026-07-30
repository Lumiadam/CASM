"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Calendar, CalendarPlus } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { PermissionGate } from "@/components/PermissionGate";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch, Asset, CalendarReservation } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type Tab = "DEVICE" | "SPACE" | "FACILITY";

const TAB_LABEL: Record<Tab, string> = {
  DEVICE: "器材",
  SPACE: "空間",
  FACILITY: "設施",
};

export default function DashboardPage() {
  const { session } = useAuth();
  const [tab, setTab] = useState<Tab>("DEVICE");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [purpose, setPurpose] = useState("內部會議使用");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [calendar, setCalendar] = useState<CalendarReservation[]>([]);
  const [loadingCalendar, setLoadingCalendar] = useState(false);

  useEffect(() => {
    if (!session) return;
    apiFetch<Asset[]>(`/assets?type=${tab}`, {}, session.access_token)
      .then(setAssets)
      .catch((e) => setError(e.message));
  }, [session, tab]);

  useEffect(() => {
    if (!session || !selectedId) {
      setCalendar([]);
      return;
    }
    setLoadingCalendar(true);
    apiFetch<CalendarReservation[]>(`/assets/${selectedId}/calendar`, {}, session.access_token)
      .then(setCalendar)
      .catch(() => setCalendar([]))
      .finally(() => setLoadingCalendar(false));
  }, [session, selectedId]);

  const filtered = useMemo(() => assets.filter((a) => a.type === tab), [assets, tab]);

  const selectedAsset = useMemo(() => assets.find(a => a.id === selectedId), [assets, selectedId]);

  async function submitReservation() {
    if (!session || !selectedId || !start || !end) return;
    setMessage(null);
    try {
      await apiFetch(
        "/reservations",
        {
          method: "POST",
          body: JSON.stringify({
            asset_id: selectedId,
            start_time: new Date(start).toISOString(),
            end_time: new Date(end).toISOString(),
            purpose,
          }),
        },
        session.access_token
      );
      setMessage("預約申請已送出，等待保管人審核。");
      // 重新載入行事曆
      apiFetch<CalendarReservation[]>(`/assets/${selectedId}/calendar`, {}, session.access_token)
        .then(setCalendar)
        .catch(() => {});
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "申請失敗");
    }
  }

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">資產總覽與預約</h2>
            <p className="text-sm text-[rgb(var(--muted))]">
              切換器材／空間／設施卡片；設施支援借用並顯示壽命預警。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(TAB_LABEL) as Tab[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setTab(key);
                  setSelectedId(null);
                }}
                className={`px-4 py-2 rounded-lg text-sm border transition ${
                  tab === key
                    ? "border-sky-500 bg-sky-500/10 text-sky-500 font-medium"
                    : "border-[rgb(var(--border))] hover:bg-slate-500/5 text-[rgb(var(--muted))]"
                }`}
              >
                {TAB_LABEL[key]}
              </button>
            ))}
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((asset) => (
              <button
                key={asset.id}
                type="button"
                onClick={() => setSelectedId(asset.id)}
                className={`card-panel p-4 text-left transition duration-200 ring-2 ${
                  selectedId === asset.id ? "ring-sky-500/60" : "ring-transparent hover:ring-[rgb(var(--border))]"
                }`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <p className="text-xs text-[rgb(var(--muted))]">{asset.asset_code}</p>
                    <h3 className="font-medium">{asset.name}</h3>
                  </div>
                  <StatusBadge status={asset.status} />
                </div>
                {asset.lifecycle_warning && (
                  <div className="mt-2 text-xs space-y-0.5 text-amber-600 dark:text-amber-400">
                    <p className="flex items-center gap-1 font-medium text-[11px]">
                      <AlertTriangle size={13} /> 即將到期／建議更換
                    </p>
                    {asset.remaining_years !== undefined && asset.expiration_date && (
                      <p className="pl-4 text-[10px] opacity-80">
                        剩餘 {asset.remaining_years} 年 (到期日: {asset.expiration_date})
                      </p>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>

          {selectedId && (
            <div className="grid md:grid-cols-2 gap-6">
              {/* 預約行事曆面板 */}
              <div className="card-panel p-5 space-y-4">
                <div>
                  <h3 className="font-medium flex items-center gap-2 text-sky-500">
                    <Calendar size={18} /> 預約時間軸 / 行事曆
                  </h3>
                  <p className="text-xs text-[rgb(var(--muted))] mt-0.5">
                    已選資產：{selectedAsset?.name} ({selectedAsset?.asset_code})
                  </p>
                </div>
                {loadingCalendar ? (
                  <p className="text-xs text-[rgb(var(--muted))] animate-pulse">載入時間軸中...</p>
                ) : calendar.length === 0 ? (
                  <p className="text-xs text-[rgb(var(--muted))] py-8 text-center border border-dashed border-[rgb(var(--border))] rounded-lg">
                    目前此時段尚無預約，可自由安排借用！
                  </p>
                ) : (
                  <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                    {calendar.map((item) => (
                      <div 
                        key={item.id} 
                        className="p-3 rounded-lg bg-slate-500/5 border border-[rgb(var(--border))]/40 text-xs space-y-2 hover:border-sky-500/30 transition duration-150"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            {item.borrower_name} ({item.borrower_email || "Email 未提供"})
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                            item.approval_status === "APPROVED" 
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" 
                              : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                          }`}>
                            {item.approval_status === "APPROVED" ? "已核准" : "待審核"}
                          </span>
                        </div>
                        <div className="text-[rgb(var(--muted))]">
                          {new Date(item.start_time).toLocaleString()} — {new Date(item.end_time).toLocaleString()}
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 italic bg-black/5 dark:bg-black/20 p-1.5 rounded">
                          事由：{item.purpose}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 建立預約面板 */}
              <PermissionGate permission="create_reservation">
                <div className="card-panel p-5 space-y-4">
                  <h3 className="font-medium flex items-center gap-2 text-sky-500">
                    <CalendarPlus size={18} /> 建立借用／預約申請
                  </h3>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <label className="text-sm space-y-1 block">
                      <span className="font-medium text-slate-700 dark:text-slate-300">開始時間</span>
                      <input
                        type="datetime-local"
                        className="w-full rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                        value={start}
                        onChange={(e) => setStart(e.target.value)}
                      />
                    </label>
                    <label className="text-sm space-y-1 block">
                      <span className="font-medium text-slate-700 dark:text-slate-300">結束時間</span>
                      <input
                        type="datetime-local"
                        className="w-full rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                        value={end}
                        onChange={(e) => setEnd(e.target.value)}
                      />
                    </label>
                  </div>
                  <label className="text-sm space-y-1 block">
                    <span className="font-medium text-slate-700 dark:text-slate-300">預約用途說明</span>
                    <input
                      className="w-full rounded-lg border border-[rgb(var(--border))] bg-transparent px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                      value={purpose}
                      onChange={(e) => setPurpose(e.target.value)}
                      placeholder="請填寫具體用途"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={submitReservation}
                    className="w-full py-2.5 rounded-lg bg-sky-500 text-white text-sm font-semibold hover:bg-sky-600 transition shadow-sm"
                  >
                    送出借用申請
                  </button>
                  {message && <p className="text-sm text-center font-medium text-[rgb(var(--muted))]">{message}</p>}
                </div>
              </PermissionGate>
            </div>
          )}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
