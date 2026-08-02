from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_roles
from app.database import get_db
from app.models import Asset, AssetStatus, MaintenancePart, MaintenanceRecord, MaintenanceWorkOrder, MaintenanceWorkOrderStatus, User, UserRole
from app.schemas.common import MaintenanceCreate, MaintenanceOut, MaintenancePartCreate, MaintenancePartOut, WorkOrderCreate, WorkOrderOut, WorkOrderUpdate

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _can_manage(user: User, asset: Asset) -> bool:
    return user.role == UserRole.ADMIN or (user.role == UserRole.CUSTODIAN and asset.custodian_id == user.id)


def _work_order_out(item: MaintenanceWorkOrder) -> WorkOrderOut:
    return WorkOrderOut(
        id=item.id, asset_id=item.asset_id, reporter_id=item.reporter_id, assigned_to_id=item.assigned_to_id,
        status=item.status, severity=item.severity, issue_type=item.issue_type, description=item.description,
        photo_url=item.photo_url, vendor_name=item.vendor_name, estimated_cost=item.estimated_cost,
        actual_cost=item.actual_cost, due_at=item.due_at, resolved_at=item.resolved_at,
        verified_by_id=item.verified_by_id, created_at=item.created_at, updated_at=item.updated_at,
        asset_name=item.asset.name if item.asset else None,
        reporter_name=item.reporter.name if item.reporter else None,
        assignee_name=item.assignee.name if item.assignee else None,
        parts=[MaintenancePartOut.model_validate(part) for part in item.parts],
    )


@router.get("", response_model=list[MaintenanceOut])
def list_maintenance(asset_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(MaintenanceRecord)
    if asset_id: query = query.filter(MaintenanceRecord.asset_id == asset_id)
    if user.role == UserRole.CUSTODIAN: query = query.join(Asset).filter(Asset.custodian_id == user.id)
    elif user.role == UserRole.EMPLOYEE: raise HTTPException(status_code=403, detail="沒有檢視維護紀錄的權限")
    return query.order_by(MaintenanceRecord.performed_at.desc()).all()


@router.post("", response_model=MaintenanceOut)
def create_maintenance(body: MaintenanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    asset = db.query(Asset).filter(Asset.id == body.asset_id).first()
    if not asset: raise HTTPException(status_code=404, detail="找不到資產")
    if not _can_manage(user, asset): raise HTTPException(status_code=403, detail="沒有此資產的維護權限")
    record = MaintenanceRecord(**body.model_dump()); db.add(record)
    if asset.status == AssetStatus.MAINTENANCE: asset.status = AssetStatus.AVAILABLE
    db.commit(); db.refresh(record)
    return record


@router.get("/work-orders", response_model=list[WorkOrderOut])
def list_work_orders(mine: bool = False, asset_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(MaintenanceWorkOrder)
    if mine or user.role == UserRole.EMPLOYEE: query = query.filter(MaintenanceWorkOrder.reporter_id == user.id)
    elif user.role == UserRole.CUSTODIAN: query = query.join(Asset).filter(Asset.custodian_id == user.id)
    if asset_id: query = query.filter(MaintenanceWorkOrder.asset_id == asset_id)
    return [_work_order_out(item) for item in query.order_by(MaintenanceWorkOrder.updated_at.desc()).all()]


@router.post("/work-orders", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(body: WorkOrderCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    asset = db.query(Asset).filter(Asset.id == body.asset_id).first()
    if not asset: raise HTTPException(status_code=404, detail="找不到資產")
    if user.role == UserRole.EMPLOYEE and asset.department_id and asset.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="無法申報其他部門的資產")
    if not _can_manage(user, asset): raise HTTPException(status_code=403, detail="只能針對自己保管的資產報修")
    item = MaintenanceWorkOrder(**body.model_dump(), reporter_id=user.id, status=MaintenanceWorkOrderStatus.REPORTED)
    db.add(item); db.commit(); db.refresh(item)
    return _work_order_out(item)


@router.put("/work-orders/{work_order_id}", response_model=WorkOrderOut)
def update_work_order(work_order_id: int, body: WorkOrderUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    item = db.query(MaintenanceWorkOrder).filter(MaintenanceWorkOrder.id == work_order_id).first()
    if not item: raise HTTPException(status_code=404, detail="找不到工單")
    if not _can_manage(user, item.asset): raise HTTPException(status_code=403, detail="沒有此工單的處理權限")
    values = body.model_dump(exclude_unset=True)
    if "assigned_to_id" in values and values["assigned_to_id"] and not db.query(User).filter(User.id == values["assigned_to_id"]).first():
        raise HTTPException(status_code=404, detail="找不到受指派人")
    for key, value in values.items(): setattr(item, key, value)
    if item.status in (MaintenanceWorkOrderStatus.CLOSED, MaintenanceWorkOrderStatus.CANCELLED):
        item.resolved_at = datetime.now(timezone.utc)
        item.verified_by_id = user.id
    db.commit(); db.refresh(item)
    return _work_order_out(item)


@router.post("/work-orders/{work_order_id}/parts", response_model=MaintenancePartOut, status_code=status.HTTP_201_CREATED)
def add_work_order_part(work_order_id: int, body: MaintenancePartCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.ADMIN, UserRole.CUSTODIAN))):
    item = db.query(MaintenanceWorkOrder).filter(MaintenanceWorkOrder.id == work_order_id).first()
    if not item: raise HTTPException(status_code=404, detail="找不到工單")
    if not _can_manage(user, item.asset): raise HTTPException(status_code=403, detail="沒有此工單的處理權限")
    values = body.model_dump(); values["replaced_at"] = values["replaced_at"] or datetime.now(timezone.utc)
    part = MaintenancePart(work_order_id=item.id, **values); db.add(part)
    if item.status == MaintenanceWorkOrderStatus.IN_REPAIR: item.status = MaintenanceWorkOrderStatus.VERIFICATION
    db.commit(); db.refresh(part)
    return MaintenancePartOut.model_validate(part)
