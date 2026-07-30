"""資產 CRUD、壽命預警、與預約行事曆。"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Asset, AssetType, User, UserRole, Reservation, ApprovalStatus
from app.schemas.common import AssetCreate, AssetOut, CalendarReservationOut
from app.services.lifecycle import (
    compute_lifecycle_warning,
    compute_expiration_date,
    compute_remaining_years,
)

router = APIRouter(prefix="/assets", tags=["assets"])


def _to_asset_out(asset: Asset) -> AssetOut:
    meta = asset.metadata_json or {}
    installed_at_str = meta.get("installed_at")
    lifespan_years = meta.get("lifespan_years")
    
    installed_at = None
    if installed_at_str:
        try:
            installed_at = datetime.fromisoformat(installed_at_str)
        except Exception:
            pass
            
    expiration_date = None
    remaining_years = None
    lifecycle_warning = False
    
    if installed_at and lifespan_years is not None:
        exp = compute_expiration_date(installed_at, lifespan_years)
        if exp:
            expiration_date = exp.date().isoformat()
            remaining_years = compute_remaining_years(exp)
            lifecycle_warning = compute_lifecycle_warning(installed_at, lifespan_years)

    return AssetOut(
        id=asset.id,
        asset_code=asset.asset_code,
        name=asset.name,
        type=asset.type,
        department_id=asset.department_id,
        custodian_id=asset.custodian_id,
        status=asset.get_dynamic_status(),
        metadata_json=asset.metadata_json,
        lifecycle_warning=lifecycle_warning,
        expiration_date=expiration_date,
        remaining_years=remaining_years,
    )


@router.get("", response_model=list[AssetOut])
def list_assets(
    asset_type: AssetType | None = Query(None, alias="type"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Asset)
    
    # 任務一的安全防線：一般同仁 (Employee) 只能查詢與預約同科室資產或公開資產 (department_id IS NULL)
    if user.role == UserRole.EMPLOYEE:
        q = q.filter((Asset.department_id == None) | (Asset.department_id == user.department_id))
        
    if asset_type:
        q = q.filter(Asset.type == asset_type)
    return [_to_asset_out(a) for a in q.order_by(Asset.id).all()]


@router.post("", response_model=AssetOut)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if db.query(Asset).filter(Asset.asset_code == body.asset_code).first():
        raise HTTPException(status_code=400, detail="資產編號已存在")
    asset = Asset(**body.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_asset_out(asset)


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: int, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="資產不存在")
        
    # 安全隔離檢查
    if user.role == UserRole.EMPLOYEE:
        if asset.department_id is not None and asset.department_id != user.department_id:
            raise HTTPException(status_code=403, detail="您無權讀取其他科室的資產")
            
    return _to_asset_out(asset)


@router.get("/{asset_id}/calendar", response_model=list[CalendarReservationOut])
def get_asset_calendar(
    asset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="資產不存在")
        
    # 一般員工只能檢視同科室或公開資產的預約時間軸
    if user.role == UserRole.EMPLOYEE:
        if asset.department_id is not None and asset.department_id != user.department_id:
            raise HTTPException(status_code=403, detail="您無權檢視其他科室資產的預約行事曆")
            
    # 撈取 PENDING 與 APPROVED 的預約
    reservations = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.approval_status.in_([ApprovalStatus.PENDING, ApprovalStatus.APPROVED])
    ).order_by(Reservation.start_time.asc()).all()
    
    out = []
    for r in reservations:
        # 隱私過濾：借用人本人、管理員、或保管人可以檢視 purpose
        is_borrower = r.borrower_id == user.id
        is_admin = user.role == UserRole.ADMIN
        is_custodian = user.role == UserRole.CUSTODIAN and asset.custodian_id == user.id
        
        purpose = r.purpose
        if not (is_borrower or is_admin or is_custodian):
            purpose = "已預約 (內容隱蔽)"
            
        out.append(CalendarReservationOut(
            id=r.id,
            start_time=r.start_time,
            end_time=r.end_time,
            borrower_name=r.borrower.name if r.borrower else "未知員工",
            borrower_email=r.borrower.email if r.borrower else None,
            approval_status=r.approval_status,
            purpose=purpose
        ))
    return out
