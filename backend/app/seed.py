"""Idempotent demo-data bootstrap.  Fixed codes make additions safe on deployed databases."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import ApprovalStatus, Asset, AssetStatus, AssetType, DamageSeverity, Department, MaintenancePart, MaintenanceRecord, MaintenanceWorkOrder, MaintenanceWorkOrderStatus, Reservation, User, UserRole


ASSET_COLUMNS = {
    "is_movable": "BOOLEAN NOT NULL DEFAULT TRUE",
    "quantity_total": "INTEGER NOT NULL DEFAULT 1",
    "reservation_locked": "BOOLEAN NOT NULL DEFAULT FALSE",
    "location": "VARCHAR(200)",
    "space_id": "INTEGER",
    "warranty_start_at": "TIMESTAMP",
    "warranty_end_at": "TIMESTAMP",
    "replacement_due_at": "TIMESTAMP",
    "next_maintenance_at": "TIMESTAMP",
}
RESERVATION_COLUMNS = {"reservation_quantity": "INTEGER NOT NULL DEFAULT 1"}


def migrate_schema() -> None:
    """Add only missing columns; never drops/rebuilds deployed data."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    for table, columns in (("assets", ASSET_COLUMNS), ("reservations", RESERVATION_COLUMNS)):
        existing = {item["name"] for item in inspector.get_columns(table)}
        for name, sql_type in columns.items():
            if name not in existing:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


def _department(db: Session, code: str, name: str) -> Department:
    item = db.query(Department).filter(Department.code == code).first()
    if not item:
        item = Department(code=code, name=name); db.add(item); db.flush()
    return item


def _user(db: Session, email: str, name: str, role: UserRole, department: Department) -> User:
    item = db.query(User).filter(User.email == email).first()
    if not item:
        item = User(name=name, email=email, password_hash=hash_password("password123"), role=role, department_id=department.id)
        db.add(item); db.flush()
    return item


def _asset(db: Session, code: str, name: str, asset_type: AssetType, department: Department, custodian: User, **values) -> Asset:
    item = db.query(Asset).filter(Asset.asset_code == code).first()
    if not item:
        item = Asset(asset_code=code, name=name, type=asset_type, department_id=department.id, custodian_id=custodian.id, **values)
        db.add(item); db.flush()
    return item


def _reservation(db: Session, asset: Asset, borrower: User, start: datetime, end: datetime, purpose: str, quantity: int = 1, approval: ApprovalStatus = ApprovalStatus.APPROVED, approver: User | None = None) -> None:
    if not db.query(Reservation).filter(Reservation.asset_id == asset.id, Reservation.start_time == start, Reservation.borrower_id == borrower.id).first():
        db.add(Reservation(asset_id=asset.id, borrower_id=borrower.id, start_time=start, end_time=end, purpose=purpose, reservation_quantity=quantity, approval_status=approval, approved_by=approver.id if approver else None))


def run_seed(db: Session) -> None:
    now = datetime.now(timezone.utc)
    it, admin_dept, ops = _department(db, "IT", "資訊技術"), _department(db, "ADM", "行政管理"), _department(db, "OPS", "營運管理")
    admin = _user(db, "admin@casms.local", "系統管理員", UserRole.ADMIN, it)
    custodian = _user(db, "custodian@casms.local", "資訊保管員", UserRole.CUSTODIAN, it)
    employee = _user(db, "employee@casms.local", "一般員工", UserRole.EMPLOYEE, admin_dept)
    assistant_admin = _user(db, "assistant.admin@casms.local", "協助管理員", UserRole.ADMIN, admin_dept)
    space_custodian = _user(db, "space.custodian@casms.local", "空間設施保管員", UserRole.CUSTODIAN, ops)
    staff = [_user(db, f"employee{index}@casms.local", f"展示員工 {index}", UserRole.EMPLOYEE, admin_dept if index < 4 else ops) for index in range(1, 6)]

    # Keep original seed scenarios for compatibility, then extend by stable demo codes.
    projector = _asset(db, "DEV-001", "4K 投影設備", AssetType.DEVICE, it, custodian, metadata_json={"category": "既有展示"})
    meeting_a = _asset(db, "SPC-101", "會議室 A", AssetType.SPACE, admin_dept, custodian, is_movable=False, location="行政大樓 1F")
    _asset(db, "FAC-HVAC-01", "既有空調主機", AssetType.FACILITY, ops, custodian, is_movable=False, warranty_start_at=now - timedelta(days=3650), warranty_end_at=now - timedelta(days=20))
    wireless_old = _asset(db, "DEV-002", "無線麥克風（既有資料）", AssetType.DEVICE, it, custodian, quantity_total=1)
    _reservation(db, wireless_old, employee, now - timedelta(days=1), now + timedelta(days=2), "既有展示借用", approver=custodian)
    _reservation(db, meeting_a, employee, now + timedelta(days=3), now + timedelta(days=3, hours=2), "既有展示會議", approval=ApprovalStatus.PENDING)

    recorders = [_asset(db, f"REC-{n:03}", f"微型密錄器 {n:02}", AssetType.DEVICE, it, custodian, metadata_json={"category": "偵蒐器材", "serial_number": f"REC-SN-{n:04}"}, warranty_start_at=now-timedelta(days=90), warranty_end_at=now+timedelta(days=635), next_maintenance_at=now+timedelta(days=90)) for n in range(1, 11)]
    detectors = [_asset(db, f"DET-{n:03}", f"三合一金屬探測器 {n}", AssetType.DEVICE, ops, space_custodian, metadata_json={"category": "安檢器材", "serial_number": f"DET-SN-{n:04}"}, warranty_end_at=now+timedelta(days=450)) for n in range(1, 3)]
    vests = _asset(db, "VEST-STOCK-001", "螢光背心", AssetType.DEVICE, ops, space_custodian, quantity_total=30, metadata_json={"category": "安全防護", "inventory_mode": "bulk"}, next_maintenance_at=now+timedelta(days=180))
    microphones = _asset(db, "MIC-STOCK-001", "無線麥克風", AssetType.DEVICE, it, custodian, quantity_total=3, metadata_json={"category": "影音器材", "inventory_mode": "bulk", "merged_from": "DEV-002"})

    gym = _asset(db, "SPC-GYM-01", "健身房", AssetType.SPACE, ops, space_custodian, is_movable=False, location="活動中心 B1", metadata_json={"category": "空間", "capacity": 40})
    meeting_rooms = [_asset(db, f"SPC-MTG-{n:02}", f"會議室 {n}", AssetType.SPACE, admin_dept, space_custodian, is_movable=False, location=f"行政大樓 {n}F", metadata_json={"category": "空間", "capacity": 12}) for n in range(1, 4)]
    receptions = [_asset(db, f"SPC-REC-{n:02}", f"接待室 {n}", AssetType.SPACE, admin_dept, space_custodian, is_movable=False, location=f"行政大樓 1F 接待區 {n}", metadata_json={"category": "空間", "capacity": 6}) for n in range(1, 3)]
    workshop = _asset(db, "SPC-WORK-01", "開放式工作區", AssetType.SPACE, ops, space_custodian, is_movable=False, location="後勤大樓 1F", metadata_json={"category": "空間"})
    space_map = [gym, *meeting_rooms, *receptions, workshop]
    for index, space in enumerate(space_map, 1):
        _asset(db, f"HVAC-{index:03}", f"冷氣主機 {index}", AssetType.FACILITY, ops, space_custodian, is_movable=False, space_id=space.id, warranty_start_at=now-timedelta(days=1600), warranty_end_at=now+timedelta(days=200), replacement_due_at=now+timedelta(days=900), next_maintenance_at=now+timedelta(days=45), metadata_json={"category": "空調", "reserve_via_space": True})
    for index, space in enumerate([gym, *meeting_rooms], 1):
        _asset(db, f"IWB-{index:03}", f"互動式電子白板 {index}", AssetType.FACILITY, it, custodian, is_movable=False, space_id=space.id, warranty_end_at=now+timedelta(days=300), replacement_due_at=now+timedelta(days=1200), metadata_json={"category": "會議設備", "reserve_via_space": True})
    boards = [_asset(db, f"MWB-{n:03}", f"移動式白板 {n}", AssetType.FACILITY, admin_dept, space_custodian, metadata_json={"category": "會議設備"}, warranty_end_at=now+timedelta(days=500)) for n in range(1, 3)]
    grinder = _asset(db, "GRD-001", "工業砂輪機", AssetType.FACILITY, ops, space_custodian, is_movable=False, space_id=workshop.id, metadata_json={"category": "工業設備", "direct_reservation": True}, warranty_end_at=now+timedelta(days=120))

    _reservation(db, vests, staff[0], now+timedelta(days=1), now+timedelta(days=1, hours=4), "活動安全勤務", 12, approver=space_custodian)
    _reservation(db, microphones, staff[1], now+timedelta(days=2), now+timedelta(days=2, hours=2), "簡報活動", 2, ApprovalStatus.PENDING)
    _reservation(db, recorders[0], staff[2], now-timedelta(days=7), now-timedelta(days=7, hours=-3), "後期添加補件", approver=custodian)
    _reservation(db, grinder, staff[4], now+timedelta(days=4), now+timedelta(days=4, hours=2), "設備訓練", approval=ApprovalStatus.PENDING)
    if not db.query(MaintenanceRecord).filter(MaintenanceRecord.asset_id == recorders[0].id).first():
        db.add(MaintenanceRecord(asset_id=recorders[0].id, maintenance_type="例行保養", cost=1200, description="鏡頭與電池檢測", performed_at=now-timedelta(days=30)))
    if not db.query(MaintenanceWorkOrder).filter(MaintenanceWorkOrder.asset_id == detectors[0].id).first():
        order = MaintenanceWorkOrder(asset_id=detectors[0].id, reporter_id=space_custodian.id, assigned_to_id=custodian.id, status=MaintenanceWorkOrderStatus.WAITING_PARTS, severity=DamageSeverity.MEDIUM, issue_type="感測異常", description="感測模組讀值不穩定", vendor_name="展示維修商", estimated_cost=2800, due_at=now+timedelta(days=7))
        db.add(order); db.flush(); db.add(MaintenancePart(work_order_id=order.id, name="感測模組", part_number="SEN-3IN1", quantity=1, supplier="展示供應商", cost=1600, replaced_at=now-timedelta(days=2)))
    db.commit()


def init_db_and_seed() -> None:
    migrate_schema()
    db = SessionLocal()
    try: run_seed(db)
    finally: db.close()
