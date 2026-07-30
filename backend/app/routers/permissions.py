"""RBAC 權限矩陣 API，供展示階段完整檢視各角色能力。"""

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.models import User
from app.schemas.common import PermissionsMatrixOut
from app.services.permissions import PERMISSION_MATRIX, get_permissions_for_role

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/matrix", response_model=PermissionsMatrixOut)
def permission_matrix(user: User = Depends(get_current_user)):
    return PermissionsMatrixOut(
        matrix=PERMISSION_MATRIX,
        current_role=user.role,
        current_permissions=get_permissions_for_role(user.role),
    )
