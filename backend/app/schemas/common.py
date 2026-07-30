from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ApprovalStatus,
    AssetStatus,
    AssetType,
    DamageSeverity,
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


class AssetCreate(BaseModel):
    asset_code: str
    name: str
    type: AssetType
    department_id: int | None = None
    custodian_id: int | None = None
    status: AssetStatus = AssetStatus.AVAILABLE
    metadata_json: dict | None = None


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


class ReservationCreate(BaseModel):
    asset_id: int
    start_time: datetime
    end_time: datetime
    purpose: str = Field(min_length=1)


class ApprovalAction(BaseModel):
    action: str = Field(description="approve 或 reject")
    note: str | None = None


class ReturnCheckoutRequest(BaseModel):
    register_damage: bool = False
    damage_description: str | None = None
    severity: DamageSeverity | None = None


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
