"""RBAC 權限矩陣說明，供展示／測試階段前端完整檢視。"""

from app.models import UserRole

# 各角色可執行的能力鍵值（與前端 permissions 頁對齊）
PERMISSION_MATRIX: dict[str, dict[str, bool]] = {
    UserRole.ADMIN.value: {
        "view_all_assets": True,
        "create_reservation": True,
        "approve_any_reservation": True,
        "approve_custodian_assets": True,
        "return_checkout": True,
        "manage_maintenance": True,
        "view_damage_logs": True,
        "view_all_reservations": True,
        "cancel_own_reservation": True,
    },
    UserRole.CUSTODIAN.value: {
        "view_all_assets": True,
        "create_reservation": True,
        "approve_any_reservation": False,
        "approve_custodian_assets": True,
        "return_checkout": True,
        "manage_maintenance": True,
        "view_damage_logs": True,
        "view_all_reservations": False,
        "cancel_own_reservation": True,
    },
    UserRole.EMPLOYEE.value: {
        "view_all_assets": True,
        "create_reservation": True,
        "approve_any_reservation": False,
        "approve_custodian_assets": False,
        "return_checkout": False,
        "manage_maintenance": False,
        "view_damage_logs": False,
        "view_all_reservations": False,
        "cancel_own_reservation": True,
    },
}


def get_permissions_for_role(role: UserRole) -> dict[str, bool]:
    return PERMISSION_MATRIX.get(role.value, {})
