from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import ApprovalStatus, Asset, AssetStatus, DamageLog, DamageSeverity, Reservation, User, UserRole
from app.schemas.common import ApprovalAction, DamageLogOut, ReservationCreate, ReservationOut, ReservationUpdate, ReturnCheckoutRequest
from app.services.reservation_overlap import reserved_quantity_for_period

router = APIRouter(prefix="/reservations", tags=["reservations"])
ACTIVE = (ApprovalStatus.PENDING, ApprovalStatus.APPROVED)


def _out(r: Reservation) -> ReservationOut:
    return ReservationOut(
        id=r.id, asset_id=r.asset_id, borrower_id=r.borrower_id,
        start_time=r.start_time, end_time=r.end_time, purpose=r.purpose,
        approval_status=r.approval_status, approved_by=r.approved_by,
        asset_name=r.asset.name if r.asset else None,
        borrower_name=r.borrower.name if r.borrower else None,
        is_supplemental=r.start_time.date() < datetime.now(timezone.utc).date(),
        reservation_quantity=r.reservation_quantity,
        quantity_total=r.asset.quantity_total if r.asset else 1,
    )


def _can_approve(user: User, asset: Asset) -> None:
    if user.role == UserRole.ADMIN or (user.role == UserRole.CUSTODIAN and asset.custodian_id == user.id):
        return
    raise HTTPException(status_code=403, detail="沒有審核此資產的權限")


def _asset_for_reservation(db: Session, asset_id: int) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id).with_for_update().first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到資產")
    if asset.status in (AssetStatus.MAINTENANCE, AssetStatus.RETIRED):
        raise HTTPException(status_code=400, detail=f"資產目前為 {asset.status.value}，無法預約")
    if asset.reservation_locked:
        raise HTTPException(status_code=400, detail="此資產已鎖定預約，請洽保管人或管理員")
    if asset.type == asset.type.FACILITY and not asset.is_movable and asset.space_id and asset.name.startswith(("冷氣", "互動式電子白板")):
        raise HTTPException(status_code=400, detail="此固定設施請改以所屬空間預約")
    return asset


def _ensure_capacity(db: Session, asset: Asset, start: datetime, end: datetime, quantity: int, exclude_id: int | None = None) -> None:
    occupied = reserved_quantity_for_period(db, asset.id, start, end, exclude_reservation_id=exclude_id)
    if occupied + quantity > asset.quantity_total:
        raise HTTPException(status_code=409, detail=f"庫存不足：此時段已占用 {occupied}，可借總數為 {asset.quantity_total}")


@router.get("", response_model=list[ReservationOut])
def list_reservations(mine: bool = Query(False), pending_for_custodian: bool = Query(False), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Reservation)
    if mine or user.role == UserRole.EMPLOYEE:
        query = query.filter(Reservation.borrower_id == user.id)
    elif pending_for_custodian:
        if user.role not in (UserRole.ADMIN, UserRole.CUSTODIAN):
            raise HTTPException(status_code=403, detail="沒有審核權限")
        query = query.filter(Reservation.approval_status == ApprovalStatus.PENDING)
        if user.role == UserRole.CUSTODIAN:
            query = query.join(Asset).filter(Asset.custodian_id == user.id)
    return [_out(item) for item in query.order_by(Reservation.start_time.desc()).all()]


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(body: ReservationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail="結束時間必須晚於開始時間")
    asset = _asset_for_reservation(db, body.asset_id)
    if user.role == UserRole.EMPLOYEE and asset.department_id and asset.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="您無權預約其他部門的資產")
    borrower_id = body.borrower_id if user.role == UserRole.ADMIN and body.borrower_id else user.id
    if body.borrower_id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="僅 Admin 可替他人建立預約")
    if not db.query(User).filter(User.id == borrower_id).first():
        raise HTTPException(status_code=404, detail="找不到借用人")
    _ensure_capacity(db, asset, body.start_time, body.end_time, body.reservation_quantity)
    reservation = Reservation(asset_id=asset.id, borrower_id=borrower_id, start_time=body.start_time, end_time=body.end_time, purpose=body.purpose, reservation_quantity=body.reservation_quantity)
    db.add(reservation); db.commit(); db.refresh(reservation)
    return _out(reservation)


@router.put("/{reservation_id}", response_model=ReservationOut)
def update_reservation(reservation_id: int, body: ReservationUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="找不到預約")
    values = body.model_dump(exclude_unset=True)
    asset_id = values.get("asset_id", reservation.asset_id)
    asset = _asset_for_reservation(db, asset_id)
    start, end = values.get("start_time", reservation.start_time), values.get("end_time", reservation.end_time)
    if end <= start:
        raise HTTPException(status_code=400, detail="結束時間必須晚於開始時間")
    if "borrower_id" in values and not db.query(User).filter(User.id == values["borrower_id"]).first():
        raise HTTPException(status_code=404, detail="找不到借用人")
    if values.get("approval_status", reservation.approval_status) in ACTIVE:
        _ensure_capacity(db, asset, start, end, values.get("reservation_quantity", reservation.reservation_quantity), reservation.id)
    for key, value in values.items(): setattr(reservation, key, value)
    db.commit(); db.refresh(reservation)
    return _out(reservation)


@router.post("/{reservation_id}/approve", response_model=ReservationOut)
def approve_reservation(reservation_id: int, body: ApprovalAction, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation or reservation.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="找不到可審核的預約")
    _can_approve(user, reservation.asset)
    if body.action.lower() == "approve":
        _ensure_capacity(db, reservation.asset, reservation.start_time, reservation.end_time, reservation.reservation_quantity, reservation.id)
        reservation.approval_status = ApprovalStatus.APPROVED
    elif body.action.lower() == "reject": reservation.approval_status = ApprovalStatus.REJECTED
    else: raise HTTPException(status_code=400, detail="action 必須是 approve 或 reject")
    reservation.approved_by = user.id; db.commit(); db.refresh(reservation)
    return _out(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation: raise HTTPException(status_code=404, detail="找不到預約")
    if user.role == UserRole.EMPLOYEE and reservation.borrower_id != user.id: raise HTTPException(status_code=403, detail="只能取消自己的預約")
    if reservation.approval_status not in ACTIVE: raise HTTPException(status_code=400, detail="目前狀態不可取消")
    reservation.approval_status = ApprovalStatus.CANCELLED; db.commit(); db.refresh(reservation)
    return _out(reservation)


@router.get("/damage-logs", response_model=list[DamageLogOut])
def list_damage_logs(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    query = db.query(DamageLog)
    if user.role == UserRole.CUSTODIAN: query = query.join(Asset).filter(Asset.custodian_id == user.id)
    return query.order_by(DamageLog.created_at.desc()).all()


@router.post("/{reservation_id}/return", response_model=ReservationOut)
def return_checkout(reservation_id: int, body: ReturnCheckoutRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation or reservation.approval_status != ApprovalStatus.APPROVED: raise HTTPException(status_code=400, detail="找不到可歸還的預約")
    _can_approve(user, reservation.asset)
    if body.register_damage:
        if not body.damage_description or not (body.severity or body.availability): raise HTTPException(status_code=400, detail="請填寫缺失說明與可用性")
        availability_to_severity = {"USABLE": "LOW", "PARTIALLY_USABLE": "MEDIUM", "UNUSABLE": "HIGH"}
        severity = body.severity or DamageSeverity(availability_to_severity[body.availability.value])
        db.add(DamageLog(asset_id=reservation.asset_id, reservation_id=reservation.id, reported_by=user.id, damage_description=body.damage_description, severity=severity))
        reservation.asset.reservation_locked = True
    reservation.approval_status = ApprovalStatus.CANCELLED; db.commit(); db.refresh(reservation)
    return _out(reservation)
