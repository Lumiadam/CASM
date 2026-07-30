"""資料庫種子：部門、測試帳號、範例資產與預約。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database import SessionLocal, engine, Base
from app.models import (
    ApprovalStatus,
    Asset,
    AssetStatus,
    AssetType,
    Department,
    Reservation,
    User,
    UserRole,
)


def run_seed(db: Session) -> None:
    if db.query(User).filter(User.email == "admin@casms.local").first():
        return

    dept_it = Department(name="資訊部", code="IT")
    dept_admin = Department(name="行政部", code="ADM")
    dept_ops = Department(name="營運部", code="OPS")
    db.add_all([dept_it, dept_admin, dept_ops])
    db.flush()

    pwd = hash_password("password123")
    admin = User(
        name="系統管理員",
        email="admin@casms.local",
        password_hash=pwd,
        role=UserRole.ADMIN,
        department_id=dept_it.id,
    )
    custodian = User(
        name="資產保管人",
        email="custodian@casms.local",
        password_hash=pwd,
        role=UserRole.CUSTODIAN,
        department_id=dept_it.id,
    )
    employee = User(
        name="一般員工",
        email="employee@casms.local",
        password_hash=pwd,
        role=UserRole.EMPLOYEE,
        department_id=dept_admin.id,
    )
    db.add_all([admin, custodian, employee])
    db.flush()

    now = datetime.now(timezone.utc)
    assets = [
        Asset(
            asset_code="DEV-001",
            name="4K 投影機",
            type=AssetType.DEVICE,
            department_id=dept_it.id,
            custodian_id=custodian.id,
            status=AssetStatus.AVAILABLE,
            metadata_json={
                "model": "Sony UBP-X700",
                "serial_number": "SN-PROJ-4K-889"
            }
        ),
        Asset(
            asset_code="SPC-101",
            name="會議室 A",
            type=AssetType.SPACE,
            department_id=dept_admin.id,
            custodian_id=custodian.id,
            status=AssetStatus.AVAILABLE,
            metadata_json={
                "capacity": 20,
                "amenities": ["白板", "視訊設備"]
            }
        ),
        Asset(
            asset_code="FAC-HVAC-01",
            name="中央空調主機",
            type=AssetType.FACILITY,
            department_id=dept_ops.id,
            custodian_id=custodian.id,
            status=AssetStatus.AVAILABLE,
            metadata_json={
                "installed_at": (now - timedelta(days=int(365.25 * 9.2))).isoformat(),
                "lifespan_years": 10.0
            }
        ),
        Asset(
            asset_code="DEV-002",
            name="無線麥克風組",
            type=AssetType.DEVICE,
            department_id=dept_it.id,
            custodian_id=custodian.id,
            status=AssetStatus.IN_USE,
        ),
    ]
    db.add_all(assets)
    db.flush()

    db.add(
        Reservation(
            asset_id=assets[3].id,
            borrower_id=employee.id,
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=2),
            purpose="季度簡報",
            approval_status=ApprovalStatus.APPROVED,
            approved_by=custodian.id,
        )
    )
    db.add(
        Reservation(
            asset_id=assets[1].id,
            borrower_id=employee.id,
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=2),
            purpose="客戶會議",
            approval_status=ApprovalStatus.PENDING,
        )
    )
    db.commit()


def init_db_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
