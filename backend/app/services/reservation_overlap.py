"""
防重疊預約引擎：對同一資產，若存在 PENDING 或 APPROVED 預約且時間區間重疊則拒絕。
重疊條件：(T_start < Exist_end) AND (T_end > Exist_start)
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ApprovalStatus, Reservation


ACTIVE_STATUSES = (ApprovalStatus.PENDING, ApprovalStatus.APPROVED)


def find_overlapping_reservation(
    db: Session,
    asset_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_reservation_id: int | None = None,
) -> Reservation | None:
    query = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.approval_status.in_(ACTIVE_STATUSES),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if exclude_reservation_id is not None:
        query = query.filter(Reservation.id != exclude_reservation_id)
    return query.first()
