export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    AVAILABLE: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    IN_USE: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
    MAINTENANCE: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
    RETIRED: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
    PENDING: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    APPROVED: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    REJECTED: "bg-red-500/15 text-red-700 dark:text-red-300",
    CANCELLED: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
  };
  const labels: Record<string, string> = {
    AVAILABLE: "可使用", IN_USE: "使用中", MAINTENANCE: "維護中", RETIRED: "已封存",
    PENDING: "待審核", APPROVED: "已核准", REJECTED: "已拒絕", CANCELLED: "已取消",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${map[status] || map.AVAILABLE}`}>
      {labels[status] || status}
    </span>
  );
}
