"""維護紀錄 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Asset, AssetStatus, MaintenanceRecord, User, UserRole
from app.schemas.common import MaintenanceCreate, MaintenanceOut

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("", response_model=list[MaintenanceOut])
def list_maintenance(
    asset_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MaintenanceRecord)
    if asset_id:
        q = q.filter(MaintenanceRecord.asset_id == asset_id)
    if user.role == UserRole.CUSTODIAN:
        ids = [a.id for a in db.query(Asset).filter(Asset.custodian_id == user.id).all()]
        q = q.filter(MaintenanceRecord.asset_id.in_(ids)) if ids else q.filter(False)
    elif user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="員工無權檢視維護紀錄")
    return q.order_by(MaintenanceRecord.performed_at.desc()).all()


@router.post("", response_model=MaintenanceOut)
def create_maintenance(
    body: MaintenanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN)),
):
    asset = db.query(Asset).filter(Asset.id == body.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="資產不存在")
    if user.role == UserRole.CUSTODIAN and asset.custodian_id != user.id:
        raise HTTPException(status_code=403, detail="僅能為自己保管的資產建立維護紀錄")
    record = MaintenanceRecord(**body.model_dump())
    db.add(record)
    if asset.status == AssetStatus.MAINTENANCE:
        asset.status = AssetStatus.AVAILABLE
    db.commit()
    db.refresh(record)
    return record
