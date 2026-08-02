from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ApprovalStatus,
    AssetStatus,
    AssetType,
    DamageSeverity,
    AssetAvailability,
    MaintenanceWorkOrderStatus,
    UserRole,
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    name: str
    permissions: dict[str, bool]


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    department_id: int | None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    type: AssetType
    department_id: int | None
    custodian_id: int | None
    status: AssetStatus
    metadata_json: dict | None = None
    lifecycle_warning: bool = False
    expiration_date: str | None = None
    remaining_years: float | None = None
    category: str | None = None
    is_movable: bool = True
    quantity_total: int = 1
    reservation_locked: bool = False
    location: str | None = None
    space_id: int | None = None
    warranty_start_at: datetime | None = None
    warranty_end_at: datetime | None = None
    replacement_due_at: datetime | None = None
    next_maintenance_at: datetime | None = None
    fixed_asset_warnings: list[str] = []


class AssetCreate(BaseModel):
    asset_code: str
    name: str
    type: AssetType
    department_id: int | None = None
    custodian_id: int | None = None
    status: AssetStatus = AssetStatus.AVAILABLE
    metadata_json: dict | None = None
    category: str | None = Field(default=None, max_length=80)
    is_movable: bool = True
    quantity_total: int = Field(default=1, ge=1)
    reservation_locked: bool = False
    location: str | None = Field(default=None, max_length=200)
    space_id: int | None = None
    warranty_start_at: datetime | None = None
    warranty_end_at: datetime | None = None
    replacement_due_at: datetime | None = None
    next_maintenance_at: datetime | None = None


class AssetUpdate(BaseModel):
    asset_code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: AssetType | None = None
    department_id: int | None = None
    custodian_id: int | None = None
    status: AssetStatus | None = None
    metadata_json: dict | None = None
    category: str | None = Field(default=None, max_length=80)
    is_movable: bool | None = None
    quantity_total: int | None = Field(default=None, ge=1)
    reservation_locked: bool | None = None
    location: str | None = Field(default=None, max_length=200)
    space_id: int | None = None
    warranty_start_at: datetime | None = None
    warranty_end_at: datetime | None = None
    replacement_due_at: datetime | None = None
    next_maintenance_at: datetime | None = None


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    borrower_id: int
    start_time: datetime
    end_time: datetime
    purpose: str
    approval_status: ApprovalStatus
    approved_by: int | None
    asset_name: str | None = None
    borrower_name: str | None = None
    is_supplemental: bool = False
    reservation_quantity: int = 1
    quantity_total: int = 1


class ReservationCreate(BaseModel):
    asset_id: int
    start_time: datetime
    end_time: datetime
    purpose: str = Field(min_length=1)
    borrower_id: int | None = None
    reservation_quantity: int = Field(default=1, ge=1)


class ReservationUpdate(BaseModel):
    asset_id: int | None = None
    borrower_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    purpose: str | None = Field(default=None, min_length=1)
    approval_status: ApprovalStatus | None = None
    reservation_quantity: int | None = Field(default=None, ge=1)


class ApprovalAction(BaseModel):
    action: str = Field(description="approve 或 reject")
    note: str | None = None


class ReturnCheckoutRequest(BaseModel):
    register_damage: bool = False
    damage_description: str | None = None
    severity: DamageSeverity | None = None
    availability: AssetAvailability | None = None


class MaintenanceCreate(BaseModel):
    asset_id: int
    maintenance_type: str
    cost: float = 0.0
    description: str = ""
    performed_at: datetime


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    maintenance_type: str
    cost: float
    description: str
    performed_at: datetime


class MaintenancePartCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    part_number: str | None = Field(default=None, max_length=120)
    quantity: int = Field(default=1, ge=1)
    supplier: str | None = Field(default=None, max_length=160)
    cost: float = Field(default=0.0, ge=0)
    replaced_at: datetime | None = None


class MaintenancePartOut(MaintenancePartCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    work_order_id: int
    replaced_at: datetime


class WorkOrderCreate(BaseModel):
    asset_id: int
    issue_type: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    severity: DamageSeverity = DamageSeverity.MEDIUM
    photo_url: str | None = Field(default=None, max_length=500)
    due_at: datetime | None = None


class WorkOrderUpdate(BaseModel):
    status: MaintenanceWorkOrderStatus | None = None
    assigned_to_id: int | None = None
    vendor_name: str | None = Field(default=None, max_length=160)
    estimated_cost: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    due_at: datetime | None = None
    description: str | None = Field(default=None, min_length=1)


class WorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    reporter_id: int
    assigned_to_id: int | None
    status: MaintenanceWorkOrderStatus
    severity: DamageSeverity
    issue_type: str
    description: str
    photo_url: str | None
    vendor_name: str | None
    estimated_cost: float
    actual_cost: float
    due_at: datetime | None
    resolved_at: datetime | None
    verified_by_id: int | None
    created_at: datetime
    updated_at: datetime
    asset_name: str | None = None
    reporter_name: str | None = None
    assignee_name: str | None = None
    parts: list[MaintenancePartOut] = []


class DamageLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    reservation_id: int | None
    reported_by: int
    damage_description: str
    severity: DamageSeverity
    created_at: datetime


class PermissionsMatrixOut(BaseModel):
    matrix: dict[str, dict[str, bool]]
    current_role: UserRole
    current_permissions: dict[str, bool]


class CalendarReservationOut(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    borrower_name: str | None
    borrower_email: str | None
    approval_status: ApprovalStatus
    purpose: str
