"""維運：健康檢查與資料庫連線狀態。"""

from fastapi import APIRouter

from app.database import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
