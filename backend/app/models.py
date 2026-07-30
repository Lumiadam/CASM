"""
CASMS 核心 ORM 模型。
對應企業資產、空間借用、維護與損壞追溯等領域實體。
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    CUSTODIAN = "Custodian"
    EMPLOYEE = "Employee"


class AssetType(str, enum.Enum):
    DEVICE = "DEVICE"
    SPACE = "SPACE"
    FACILITY = "FACILITY"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class DamageSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="department")
    assets: Mapped[list["Asset"]] = relationship(back_populates="department")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    department: Mapped["Department | None"] = relationship(back_populates="users")
    custodian_assets: Mapped[list["Asset"]] = relationship(
        back_populates="custodian", foreign_keys="Asset.custodian_id"
    )
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="borrower", foreign_keys="Reservation.borrower_id"
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    custodian_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus), default=AssetStatus.AVAILABLE, nullable=False
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    department: Mapped["Department | None"] = relationship(back_populates="assets")
    custodian: Mapped["User | None"] = relationship(
        back_populates="custodian_assets", foreign_keys=[custodian_id]
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="asset")
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(back_populates="asset")
    damage_logs: Mapped[list["DamageLog"]] = relationship(back_populates="asset")

    def get_dynamic_status(self) -> AssetStatus:
        if self.status in (AssetStatus.MAINTENANCE, AssetStatus.RETIRED):
            return self.status

        # 檢查當前時間是否落在任何 APPROVED 預約的區間內
        now = datetime.now(timezone.utc)
        for r in self.reservations:
            if r.approval_status == ApprovalStatus.APPROVED:
                start = r.start_time
                end = r.end_time
                
                # 為了避免 naive datetime 和 aware datetime 比較時出錯
                if start.tzinfo is not None:
                    now_compare = now
                else:
                    now_compare = now.astimezone(timezone.utc).replace(tzinfo=None)
                
                if start <= now_compare <= end:
                    return AssetStatus.IN_USE
        return AssetStatus.AVAILABLE


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    asset: Mapped["Asset"] = relationship(back_populates="reservations")
    borrower: Mapped["User"] = relationship(back_populates="reservations", foreign_keys=[borrower_id])
    approver: Mapped["User | None"] = relationship(foreign_keys=[approved_by])
    damage_logs: Mapped[list["DamageLog"]] = relationship(back_populates="reservation")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(120), nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    performed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    asset: Mapped["Asset"] = relationship(back_populates="maintenance_records")


class DamageLog(Base):
    __tablename__ = "damage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    damage_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[DamageSeverity] = mapped_column(Enum(DamageSeverity), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asset: Mapped["Asset"] = relationship(back_populates="damage_logs")
    reservation: Mapped["Reservation | None"] = relationship(back_populates="damage_logs")
    reporter: Mapped["User"] = relationship(foreign_keys=[reported_by])
