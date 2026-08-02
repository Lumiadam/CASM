from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import ApprovalStatus, Asset, AssetStatus, AssetType, Reservation, User, UserRole
from app.schemas.common import AssetCreate, AssetOut, AssetUpdate, CalendarReservationOut
from app.services.lifecycle import (
    compute_expiration_date,
    compute_lifecycle_warning,
    compute_remaining_years,
)

router = APIRouter(prefix="/assets", tags=["assets"])


def _to_asset_out(asset: Asset) -> AssetOut:
    metadata = asset.metadata_json or {}
    installed_at = None
    try:
        if metadata.get("installed_at"):
            installed_at = datetime.fromisoformat(metadata["installed_at"])
    except ValueError:
        pass

    expiration_date = None
    remaining_years = None
    lifecycle_warning = False
    lifespan_years = metadata.get("lifespan_years")
    if installed_at and lifespan_years is not None:
        expiration = compute_expiration_date(installed_at, lifespan_years)
        if expiration:
            expiration_date = expiration.date().isoformat()
            remaining_years = compute_remaining_years(expiration)
            lifecycle_warning = compute_lifecycle_warning(installed_at, lifespan_years)

    warnings = []
    if asset.type == AssetType.SPACE:
        warnings = [
            f"{child.name}（{child.asset_code}）目前維修中"
            for child in asset.fixed_assets
            if child.status == AssetStatus.MAINTENANCE
        ]
    return AssetOut(
        id=asset.id,
        asset_code=asset.asset_code,
        name=asset.name,
        type=asset.type,
        department_id=asset.department_id,
        custodian_id=asset.custodian_id,
        status=asset.get_dynamic_status(),
        metadata_json=metadata,
        lifecycle_warning=lifecycle_warning,
        expiration_date=expiration_date,
        remaining_years=remaining_years,
        category=metadata.get("category"),
        is_movable=asset.is_movable,
        quantity_total=asset.quantity_total,
        reservation_locked=asset.reservation_locked,
        location=asset.location,
        space_id=asset.space_id,
        warranty_start_at=asset.warranty_start_at,
        warranty_end_at=asset.warranty_end_at,
        replacement_due_at=asset.replacement_due_at,
        next_maintenance_at=asset.next_maintenance_at,
        fixed_asset_warnings=warnings,
    )


def _ensure_asset_visible(asset: Asset, user: User) -> None:
    if user.role == UserRole.EMPLOYEE and asset.department_id is not None and asset.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="您無權查看此資產。")


@router.get("", response_model=list[AssetOut])
def list_assets(
    asset_type: AssetType | None = Query(None, alias="type"),
    keyword: str | None = Query(None, min_length=1),
    status: AssetStatus | None = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Asset)
    if user.role == UserRole.EMPLOYEE:
        query = query.filter(or_(Asset.department_id.is_(None), Asset.department_id == user.department_id))
    if asset_type:
        query = query.filter(Asset.type == asset_type)
    if status:
        query = query.filter(Asset.status == status)
    if keyword:
        term = f"%{keyword.strip()}%"
        query = query.filter(or_(Asset.name.ilike(term), Asset.asset_code.ilike(term)))
    return [_to_asset_out(asset) for asset in query.order_by(Asset.id).all()]


@router.post("", response_model=AssetOut)
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if db.query(Asset).filter(Asset.asset_code == body.asset_code).first():
        raise HTTPException(status_code=400, detail="資產編號已存在。")
    values = body.model_dump(exclude={"category"})
    metadata = values.get("metadata_json") or {}
    if body.category:
        metadata["category"] = body.category
    values["metadata_json"] = metadata
    if values.get("space_id"):
        space = db.query(Asset).filter(Asset.id == values["space_id"], Asset.type == AssetType.SPACE).first()
        if not space:
            raise HTTPException(status_code=400, detail="space_id 必須指定既有空間資產")
    asset = Asset(**values)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_asset_out(asset)


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到資產。")
    _ensure_asset_visible(asset, user)
    return _to_asset_out(asset)


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: int,
    body: AssetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN)),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到資產。")
    if user.role == UserRole.CUSTODIAN and asset.custodian_id != user.id:
        raise HTTPException(status_code=403, detail="只能調整自己保管的資產")
    values = body.model_dump(exclude_unset=True, exclude={"category"})
    if user.role == UserRole.CUSTODIAN:
        forbidden = {"asset_code", "type", "department_id", "custodian_id", "space_id"}
        values = {key: value for key, value in values.items() if key not in forbidden}
    if values.get("asset_code") and values["asset_code"] != asset.asset_code:
        if db.query(Asset).filter(Asset.asset_code == values["asset_code"]).first():
            raise HTTPException(status_code=400, detail="資產編號已存在。")
    if "space_id" in values and values["space_id"]:
        space = db.query(Asset).filter(Asset.id == values["space_id"], Asset.type == AssetType.SPACE).first()
        if not space:
            raise HTTPException(status_code=400, detail="space_id 必須指定既有空間資產")
        if values["space_id"] == asset.id:
            raise HTTPException(status_code=400, detail="資產不可綁定自己為空間")
    for key, value in values.items():
        setattr(asset, key, value)
    if "category" in body.model_fields_set:
        metadata = dict(asset.metadata_json or {})
        if body.category:
            metadata["category"] = body.category
        else:
            metadata.pop("category", None)
        asset.metadata_json = metadata
    db.commit()
    db.refresh(asset)
    return _to_asset_out(asset)


@router.post("/{asset_id}/archive", response_model=AssetOut)
def archive_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到資產。")
    asset.status = AssetStatus.RETIRED
    for reservation in asset.reservations:
        if reservation.approval_status in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED):
            reservation.approval_status = ApprovalStatus.CANCELLED
    db.commit()
    db.refresh(asset)
    return _to_asset_out(asset)


@router.get("/{asset_id}/calendar", response_model=list[CalendarReservationOut])
def get_asset_calendar(
    asset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到資產。")
    _ensure_asset_visible(asset, user)
    reservations = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.approval_status.in_([ApprovalStatus.PENDING, ApprovalStatus.APPROVED]),
    ).order_by(Reservation.start_time.asc()).all()
    output: list[CalendarReservationOut] = []
    for reservation in reservations:
        can_see_purpose = (
            reservation.borrower_id == user.id
            or user.role == UserRole.ADMIN
            or (user.role == UserRole.CUSTODIAN and asset.custodian_id == user.id)
        )
        output.append(CalendarReservationOut(
            id=reservation.id,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            borrower_name=reservation.borrower.name if reservation.borrower else None,
            borrower_email=reservation.borrower.email if reservation.borrower else None,
            approval_status=reservation.approval_status,
            purpose=reservation.purpose if can_see_purpose else "已隱藏",
        ))
    return output
