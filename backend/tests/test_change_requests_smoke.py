import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite:///./casms_smoke_test.db"
os.environ["SEED_ON_STARTUP"] = "true"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


class ChangeRequestSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        Base.metadata.drop_all(bind=engine)

    def login(self, email: str) -> str:
        response = self.client.post(
            "/auth/login",
            json={"email": email, "password": "password123"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    @staticmethod
    def headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_change_request_lifecycle_and_permissions(self):
        employee = self.login("employee@casms.local")
        custodian = self.login("custodian@casms.local")
        custodian = self.login("custodian@casms.local")
        admin = self.login("admin@casms.local")

        employee_request = self.client.post(
            "/change-requests",
            headers=self.headers(employee),
            json={
                "target_type": "ASSET",
                "action": "CREATE",
                "payload_json": {"asset_code": "SMOKE-001", "name": "Smoke asset", "type": "DEVICE"},
            },
        )
        self.assertEqual(employee_request.status_code, 201, employee_request.text)
        employee_request_id = employee_request.json()["id"]

        employee_maintenance = self.client.post(
            "/change-requests",
            headers=self.headers(employee),
            json={"target_type": "MAINTENANCE", "action": "CREATE", "payload_json": {"asset_id": 1}},
        )
        self.assertEqual(employee_maintenance.status_code, 403, employee_maintenance.text)

        custodian_request = self.client.post(
            "/change-requests",
            headers=self.headers(custodian),
            json={
                "target_type": "ASSET",
                "action": "UPDATE",
                "target_id": 1,
                "payload_json": {"name": "Updated by request"},
            },
        )
        self.assertEqual(custodian_request.status_code, 201, custodian_request.text)
        custodian_request_id = custodian_request.json()["id"]

        pending = self.client.get("/change-requests?pending_only=true", headers=self.headers(admin))
        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertEqual({item["id"] for item in pending.json()}, {employee_request_id, custodian_request_id})

        employee_review = self.client.post(
            f"/change-requests/{employee_request_id}/review",
            headers=self.headers(employee),
            json={"approved": True, "reason": "Not allowed"},
        )
        self.assertEqual(employee_review.status_code, 403, employee_review.text)

        approved = self.client.post(
            f"/change-requests/{employee_request_id}/review",
            headers=self.headers(admin),
            json={"approved": True, "reason": "Approved for smoke test"},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        self.assertEqual(approved.json()["review_reason"], "Approved for smoke test")
        approved_asset = self.client.get(f"/assets/{approved.json()['target_id']}", headers=self.headers(admin))
        self.assertEqual(approved_asset.status_code, 200, approved_asset.text)
        self.assertEqual(approved_asset.json()["asset_code"], "SMOKE-001")
        self.assertEqual(approved_asset.json()["custodian_id"], 3)

        withdrawn = self.client.post(
            f"/change-requests/{custodian_request_id}/withdraw",
            headers=self.headers(custodian),
        )
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        self.assertEqual(withdrawn.json()["status"], "WITHDRAWN")

    def test_admin_asset_and_supplemental_reservation_crud(self):
        admin = self.login("admin@casms.local")
        headers = self.headers(admin)

        created_asset = self.client.post(
            "/assets",
            headers=headers,
            json={
                "asset_code": "ADMIN-CRUD-001",
                "name": "管理員測試資產",
                "type": "DEVICE",
                "category": "測試分類",
                "custodian_id": 2,
            },
        )
        self.assertEqual(created_asset.status_code, 200, created_asset.text)
        asset_id = created_asset.json()["id"]
        self.assertEqual(created_asset.json()["category"], "測試分類")

        updated_asset = self.client.put(
            f"/assets/{asset_id}",
            headers=headers,
            json={"name": "已更新測試資產", "category": "更新分類", "custodian_id": 1},
        )
        self.assertEqual(updated_asset.status_code, 200, updated_asset.text)
        self.assertEqual(updated_asset.json()["category"], "更新分類")

        now = datetime.now(timezone.utc)
        created_reservation = self.client.post(
            "/reservations",
            headers=headers,
            json={
                "asset_id": asset_id,
                "borrower_id": 3,
                "start_time": (now - timedelta(days=3)).isoformat(),
                "end_time": (now - timedelta(days=3, hours=-2)).isoformat(),
                "purpose": "補件測試",
            },
        )
        self.assertEqual(created_reservation.status_code, 201, created_reservation.text)
        reservation_id = created_reservation.json()["id"]
        self.assertTrue(created_reservation.json()["is_supplemental"])

        updated_reservation = self.client.put(
            f"/reservations/{reservation_id}",
            headers=headers,
            json={"purpose": "補件測試已更新", "approval_status": "APPROVED"},
        )
        self.assertEqual(updated_reservation.status_code, 200, updated_reservation.text)
        self.assertEqual(updated_reservation.json()["purpose"], "補件測試已更新")

        archived_asset = self.client.post(f"/assets/{asset_id}/archive", headers=headers)
        self.assertEqual(archived_asset.status_code, 200, archived_asset.text)
        self.assertEqual(archived_asset.json()["status"], "RETIRED")

    def test_bulk_reservation_capacity_and_work_order(self):
        admin = self.login("admin@casms.local")
        employee = self.login("employee@casms.local")
        custodian = self.login("custodian@casms.local")
        admin_headers = self.headers(admin)
        employee_headers = self.headers(employee)
        custodian_headers = self.headers(custodian)
        assets = self.client.get("/assets", headers=admin_headers).json()
        vests = next(item for item in assets if item["asset_code"] == "VEST-STOCK-001")
        meeting = next(item for item in assets if item["asset_code"] == "SPC-101")
        now = datetime.now(timezone.utc) + timedelta(days=30)
        first = self.client.post("/reservations", headers=admin_headers, json={
            "asset_id": vests["id"], "borrower_id": 3, "reservation_quantity": 20,
            "start_time": now.isoformat(), "end_time": (now + timedelta(hours=2)).isoformat(), "purpose": "Capacity test",
        })
        self.assertEqual(first.status_code, 201, first.text)
        overflow = self.client.post("/reservations", headers=admin_headers, json={
            "asset_id": vests["id"], "borrower_id": 3, "reservation_quantity": 11,
            "start_time": now.isoformat(), "end_time": (now + timedelta(hours=2)).isoformat(), "purpose": "Overflow test",
        })
        self.assertEqual(overflow.status_code, 409, overflow.text)
        report = self.client.post("/maintenance/work-orders", headers=custodian_headers, json={
            "asset_id": meeting["id"], "issue_type": "Display issue", "description": "Screen input is intermittent", "severity": "MEDIUM",
        })
        self.assertEqual(report.status_code, 201, report.text)
        work_order_id = report.json()["id"]
        updated = self.client.put(f"/maintenance/work-orders/{work_order_id}", headers=admin_headers, json={"status": "IN_REPAIR", "vendor_name": "Demo vendor"})
        self.assertEqual(updated.status_code, 200, updated.text)
        part = self.client.post(f"/maintenance/work-orders/{work_order_id}/parts", headers=admin_headers, json={"name": "HDMI cable", "quantity": 1, "cost": 200})
        self.assertEqual(part.status_code, 201, part.text)
        self.assertEqual(part.json()["name"], "HDMI cable")


if __name__ == "__main__":
    unittest.main()
