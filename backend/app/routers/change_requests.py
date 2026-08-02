from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import (
    ApprovalStatus,
    Asset,
    AssetStatus,
    AssetType,
    ChangeAction,
    ChangeRequest,
    ChangeRequestStatus,
    ChangeTarget,
    MaintenanceRecord,
    User,
    UserRole,
)
from app.schemas.change_requests import ChangeRequestCreate, ChangeRequestOut, ChangeRequestReview

router = APIRouter(prefix="/change-requests", tags=["change-requests"])


def _apply_asset_change(request: ChangeRequest, db: Session) -> None:
    payload = request.payload_json or {}
    if request.action == ChangeAction.CREATE:
        asset_code = payload.get("asset_code")
        name = payload.get("name")
        asset_type = payload.get("type")
        if not all(isinstance(value, str) and value.strip() for value in (asset_code, name, asset_type)):
            raise HTTPException(status_code=400, detail="資產申請缺少名稱、編號或類型。")
        if db.query(Asset).filter(Asset.asset_code == asset_code.strip()).first():
            raise HTTPException(status_code=400, detail="資產編號已存在。")
        try:
            parsed_type = AssetType(asset_type)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="資產類型無效。") from error
        metadata = payload.get("metadata_json") if isinstance(payload.get("metadata_json"), dict) else {}
        metadata = dict(metadata)
        if isinstance(payload.get("category"), str) and payload["category"].strip():
            metadata["category"] = payload["category"].strip()
        requester = db.query(User).filter(User.id == request.requester_id).first()
        asset = Asset(
            asset_code=asset_code.strip(),
            name=name.strip(),
            type=parsed_type,
            department_id=requester.department_id if requester else None,
            custodian_id=request.requester_id,
            metadata_json=metadata,
        )
        db.add(asset)
        db.flush()
        request.target_id = asset.id
        return

    asset = db.query(Asset).filter(Asset.id == request.target_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="找不到申請目標資產。")
    if request.action == ChangeAction.UPDATE:
        for field in ("asset_code", "name", "department_id", "custodian_id", "status"):
            if field in payload:
                setattr(asset, field, payload[field])
        if "type" in payload:
            asset.type = AssetType(payload["type"])
        if "category" in payload:
            metadata = dict(asset.metadata_json or {})
            if payload["category"]:
                metadata["category"] = payload["category"]
            else:
                metadata.pop("category", None)
            asset.metadata_json = metadata
    elif request.action == ChangeAction.ARCHIVE:
        asset.status = AssetStatus.RETIRED
        for reservation in asset.reservations:
            if reservation.approval_status.value in ("PENDING", "APPROVED"):
                reservation.approval_status = ApprovalStatus.CANCELLED


def _require_request_scope(body: ChangeRequestCreate, user: User, db: Session) -> None:
    if user.role == UserRole.EMPLOYEE:
        if body.target_type != ChangeTarget.ASSET or body.action != ChangeAction.CREATE:
            raise HTTPException(status_code=403, detail="員工僅能提出新增資產申請。")
        if body.target_id is not None:
            raise HTTPException(status_code=400, detail="新增資產申請不可指定目標 ID。")
        return

    if user.role != UserRole.CUSTODIAN:
        raise HTTPException(status_code=403, detail="僅員工與保管人可提出異動申請。")

    asset_id: int | None = None
    if body.target_type == ChangeTarget.ASSET:
        if body.action == ChangeAction.CREATE:
            if body.target_id is not None:
                raise HTTPException(status_code=400, detail="新增資產申請不可指定目標 ID。")
            return
        asset_id = body.target_id
    elif body.target_type == ChangeTarget.MAINTENANCE:
        if body.action == ChangeAction.CREATE:
            asset_id = body.payload_json.get("asset_id")
        else:
            if body.target_id is None:
                raise HTTPException(status_code=400, detail="維護紀錄異動必須指定目標 ID。")
            record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == body.target_id).first()
            asset_id = record.asset_id if record else None

    if not isinstance(asset_id, int):
        raise HTTPException(status_code=400, detail="此申請必須指定由您保管的資產。")
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset or asset.custodian_id != user.id:
        raise HTTPException(status_code=403, detail="您僅能申請異動自己保管的資產。")


@router.post("", response_model=ChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_change_request(
    body: ChangeRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_request_scope(body, user, db)
    request = ChangeRequest(
        target_type=body.target_type,
        action=body.action,
        target_id=body.target_id,
        payload_json=body.payload_json,
        requester_id=user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("", response_model=list[ChangeRequestOut])
def list_change_requests(
    pending_only: bool = Query(False),
    mine: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(ChangeRequest)
    if mine or user.role != UserRole.ADMIN:
        query = query.filter(ChangeRequest.requester_id == user.id)
    if pending_only:
        query = query.filter(ChangeRequest.status == ChangeRequestStatus.PENDING_REVIEW)
    return query.order_by(ChangeRequest.created_at.desc()).all()


@router.post("/{request_id}/withdraw", response_model=ChangeRequestOut)
def withdraw_change_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="找不到資產申請。")
    if request.requester_id != user.id:
        raise HTTPException(status_code=403, detail="僅申請人可撤回此申請。")
    if request.status != ChangeRequestStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="僅待審申請可撤回。")
    request.status = ChangeRequestStatus.WITHDRAWN
    db.commit()
    db.refresh(request)
    return request


@router.post("/{request_id}/review", response_model=ChangeRequestOut)
def review_change_request(
    request_id: int,
    body: ChangeRequestReview,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    request = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="找不到資產申請。")
    if request.status != ChangeRequestStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="僅待審申請可進行審核。")
    if body.approved and request.target_type == ChangeTarget.ASSET:
        _apply_asset_change(request, db)
    request.status = ChangeRequestStatus.APPROVED if body.approved else ChangeRequestStatus.REJECTED
    request.reviewer_id = user.id
    request.review_reason = body.reason
    request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request
