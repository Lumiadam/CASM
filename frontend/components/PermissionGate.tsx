"use client";

import { useAuth } from "@/lib/auth-context";

export function PermissionGate({
  permission,
  children,
  fallback,
}: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission } = useAuth();
  if (!hasPermission(permission)) {
    return (
      fallback ?? (
        <div className="text-sm text-amber-600 dark:text-amber-300 border border-amber-500/30 rounded-lg px-3 py-2 bg-amber-500/5">
          目前角色無「{permission}」權限（展示模式仍可檢視頁面，此操作已停用）
        </div>
      )
    );
  }
  return <>{children}</>;
}
