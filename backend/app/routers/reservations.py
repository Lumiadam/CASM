"""
預約、保管人核定、歸還驗收與損壞鎖定。
Admin 可審核全部；Custodian 僅能審核 custodian_id 為自己的資產。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import (
    ApprovalStatus,
    Asset,
    AssetStatus,
    DamageLog,
    Reservation,
    User,
    UserRole,
)
from app.schemas.common import (
    ApprovalAction,
    DamageLogOut,
    ReservationCreate,
    ReservationOut,
    ReturnCheckoutRequest,
)
from app.services.reservation_overlap import find_overlapping_reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _reservation_out(r: Reservation) -> ReservationOut:
    return ReservationOut(
        id=r.id,
        asset_id=r.asset_id,
        borrower_id=r.borrower_id,
        start_time=r.start_time,
        end_time=r.end_time,
        purpose=r.purpose,
        approval_status=r.approval_status,
        approved_by=r.approved_by,
        asset_name=r.asset.name if r.asset else None,
        borrower_name=r.borrower.name if r.borrower else None,
    )


def _ensure_can_approve(user: User, asset: Asset) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.CUSTODIAN and asset.custodian_id == user.id:
        return
    raise HTTPException(status_code=403, detail="無權審核此資產的預約")


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    mine: bool = Query(False, description="僅個人借用"),
    pending_for_custodian: bool = Query(False, description="保管人待審清單"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Reservation)
    if mine:
        q = q.filter(Reservation.borrower_id == user.id)
    elif pending_for_custodian:
        if user.role not in (UserRole.CUSTODIAN, UserRole.ADMIN):
            raise HTTPException(status_code=403, detail="僅保管人或管理員可檢視待審清單")
        q = q.filter(Reservation.approval_status == ApprovalStatus.PENDING)
        if user.role == UserRole.CUSTODIAN:
            q = q.join(Asset).filter(Asset.custodian_id == user.id)
    elif user.role == UserRole.EMPLOYEE:
        q = q.filter(Reservation.borrower_id == user.id)
    q = q.order_by(Reservation.start_time.desc())
    return [_reservation_out(r) for r in q.all()]


@router.get("/damage-logs", response_model=list[DamageLogOut])
def list_damage_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN)),
):
    logs = db.query(DamageLog).order_by(DamageLog.created_at.desc()).all()
    if user.role == UserRole.CUSTODIAN:
        custodian_asset_ids = [
            a.id for a in db.query(Asset).filter(Asset.custodian_id == user.id).all()
        ]
        logs = [log for log in logs if log.asset_id in custodian_asset_ids]
    return logs


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(
    body: ReservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail="結束時間必須晚於開始時間")
    # 悲觀排他鎖，防範 Race Condition
    asset = db.query(Asset).filter(Asset.id == body.asset_id).with_for_update().first()
    if not asset:
        raise HTTPException(status_code=404, detail="資產不存在")
        
    # 安全性防線：Employee 只能預約同科室資產或公開資產
    if user.role == UserRole.EMPLOYEE:
        if asset.department_id is not None and asset.department_id != user.department_id:
            raise HTTPException(status_code=403, detail="您無權預約其他科室的資產")

    if asset.status in (AssetStatus.MAINTENANCE, AssetStatus.RETIRED):
        raise HTTPException(status_code=400, detail=f"資產目前狀態為 {asset.status.value}，無法預約")
    overlap = find_overlapping_reservation(db, body.asset_id, body.start_time, body.end_time)
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=f"預約時間與既有申請 #{overlap.id} 重疊（{overlap.approval_status.value}）",
        )
    reservation = Reservation(
        asset_id=body.asset_id,
        borrower_id=user.id,
        start_time=body.start_time,
        end_time=body.end_time,
        purpose=body.purpose,
        approval_status=ApprovalStatus.PENDING,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return _reservation_out(reservation)


@router.post("/{reservation_id}/approve", response_model=ReservationOut)
def approve_reservation(
    reservation_id: int,
    body: ApprovalAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN)),
):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="預約不存在")
    if reservation.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="僅待審狀態可核定")
    asset = reservation.asset
    _ensure_can_approve(user, asset)
    action = body.action.lower()
    if action == "approve":
        overlap = find_overlapping_reservation(
            db,
            reservation.asset_id,
            reservation.start_time,
            reservation.end_time,
            exclude_reservation_id=reservation.id,
        )
        if overlap:
            raise HTTPException(status_code=409, detail="核准將造成時間重疊")
        reservation.approval_status = ApprovalStatus.APPROVED
        reservation.approved_by = user.id
    elif action == "reject":
        reservation.approval_status = ApprovalStatus.REJECTED
        reservation.approved_by = user.id
    else:
        raise HTTPException(status_code=400, detail="action 須為 approve 或 reject")
    db.commit()
    db.refresh(reservation)
    return _reservation_out(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="預約不存在")
    if user.role == UserRole.EMPLOYEE and reservation.borrower_id != user.id:
        raise HTTPException(status_code=403, detail="僅能取消自己的預約")
    if reservation.approval_status not in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED):
        raise HTTPException(status_code=400, detail="目前狀態無法取消")
    reservation.approval_status = ApprovalStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return _reservation_out(reservation)


@router.post("/{reservation_id}/return", response_model=ReservationOut)
def return_checkout(
    reservation_id: int,
    body: ReturnCheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN)),
):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="預約不存在")
    if reservation.approval_status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="僅已核准且借用中的預約可辦理歸還")
    asset = reservation.asset
    _ensure_can_approve(user, asset)
    if body.register_damage:
        if not body.damage_description or not body.severity:
            raise HTTPException(status_code=400, detail="登記損壞須提供描述與嚴重度")
        log = DamageLog(
            asset_id=asset.id,
            reservation_id=reservation.id,
            reported_by=user.id,
            damage_description=body.damage_description,
            severity=body.severity,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        asset.status = AssetStatus.MAINTENANCE
        
        # 器材損壞連動取消未來所有已核准或待審核的預約
        now_naive = datetime.utcnow()
        future_reservations = db.query(Reservation).filter(
            Reservation.asset_id == asset.id,
            Reservation.approval_status.in_([ApprovalStatus.PENDING, ApprovalStatus.APPROVED]),
            Reservation.start_time >= now_naive
        ).all()
        for r_fut in future_reservations:
            r_fut.approval_status = ApprovalStatus.CANCELLED
    reservation.approval_status = ApprovalStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return _reservation_out(reservation)
