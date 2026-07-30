"use client";

import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { apiFetch, PermissionMatrixResponse } from "@/lib/api";
import { PERMISSION_LABELS } from "@/lib/constants";
import { useAuth } from "@/lib/auth-context";

export default function PermissionsPage() {
  const { session } = useAuth();
  const [data, setData] = useState<PermissionMatrixResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<PermissionMatrixResponse>("/permissions/matrix", {}, session.access_token)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [session]);

  const keys = Object.keys(PERMISSION_LABELS);

  return (
    <RequireAuth>
      <AppShell>
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold">RBAC 權限矩陣（展示）</h2>
            <p className="text-sm text-[rgb(var(--muted))]">
              測試／展示階段完整列出 Admin、Custodian、Employee 能力差異；目前登入角色：
              <strong className="ml-1">{data?.current_role ?? session?.role}</strong>
            </p>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {data && (
            <div className="overflow-x-auto card-panel">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[rgb(var(--border))] text-left">
                    <th className="p-3">能力</th>
                    {Object.keys(data.matrix).map((role) => (
                      <th key={role} className="p-3">
                        {role}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key} className="border-b border-[rgb(var(--border))]/60">
                      <td className="p-3">{PERMISSION_LABELS[key] ?? key}</td>
                      {Object.entries(data.matrix).map(([role, perms]) => (
                        <td key={role} className="p-3">
                          {perms[key] ? (
                            <Check className="text-emerald-500" size={18} />
                          ) : (
                            <X className="text-red-400" size={18} />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data && (
            <div className="card-panel p-4">
              <h3 className="font-medium mb-2">目前工作階段有效權限</h3>
              <ul className="grid sm:grid-cols-2 gap-2 text-sm">
                {keys.map((k) => (
                  <li key={k} className="flex items-center gap-2">
                    {data.current_permissions[k] ? (
                      <Check size={14} className="text-emerald-500" />
                    ) : (
                      <X size={14} className="text-red-400" />
                    )}
                    {PERMISSION_LABELS[k]}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </AppShell>
    </RequireAuth>
  );
}
