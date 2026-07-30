export const PERMISSION_LABELS: Record<string, string> = {
  view_all_assets: "檢視全部資產",
  create_reservation: "建立借用／預約",
  approve_any_reservation: "審核任意預約（Admin）",
  approve_custodian_assets: "審核保管資產",
  return_checkout: "驗收歸還",
  manage_maintenance: "維護紀錄管理",
  view_damage_logs: "檢視損壞紀錄",
  view_all_reservations: "檢視全部預約",
  cancel_own_reservation: "取消自己的預約",
};

export const TEST_ACCOUNTS = [
  { label: "Admin 管理員", email: "admin@casms.local", password: "password123", role: "Admin" },
  {
    label: "Custodian 保管人",
    email: "custodian@casms.local",
    password: "password123",
    role: "Custodian",
  },
  {
    label: "Employee 員工",
    email: "employee@casms.local",
    password: "password123",
    role: "Employee",
  },
] as const;
