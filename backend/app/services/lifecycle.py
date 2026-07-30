"""設施壽命精確計算與到期日預警。"""

import calendar
from datetime import datetime, timezone


def compute_expiration_date(installed_at: datetime | None, lifespan_years: float | None) -> datetime | None:
    if not installed_at or lifespan_years is None or lifespan_years <= 0:
        return None
    # 將浮點數年份轉為月數
    total_months = int(lifespan_years * 12)
    year_offset = total_months // 12
    month_offset = total_months % 12
    
    new_year = installed_at.year + year_offset
    new_month = installed_at.month + month_offset
    if new_month > 12:
        new_year += 1
        new_month -= 12
        
    # 處理特殊日期（例如在非閏年將 2/29 移至 2/28，或 31 日在 30 日月份縮短）
    _, last_day = calendar.monthrange(new_year, new_month)
    new_day = min(installed_at.day, last_day)
    
    return installed_at.replace(year=new_year, month=new_month, day=new_day)


def compute_remaining_years(expiration_date: datetime | None) -> float | None:
    if not expiration_date:
        return None
    now = datetime.now(timezone.utc)
    exp = expiration_date.replace(tzinfo=timezone.utc) if expiration_date.tzinfo is None else expiration_date
    delta_days = (exp - now).days
    remaining = delta_days / 365.2425
    return round(remaining, 2)


def compute_lifecycle_warning(installed_at: datetime | None, lifespan_years: float | None) -> bool:
    if not installed_at or not lifespan_years or lifespan_years <= 0:
        return False
    exp = compute_expiration_date(installed_at, lifespan_years)
    remaining = compute_remaining_years(exp)
    if remaining is None:
        return False
    threshold = 0.1 * lifespan_years
    return remaining <= threshold
