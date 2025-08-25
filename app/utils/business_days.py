from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Optional

import holidays


Market = Literal["AR", "US"]


def _get_holidays_for_market(market: Market):
    if market == "AR":
        return holidays.AR()
    if market == "US":
        return holidays.US()
    raise ValueError(f"Unsupported market: {market}")


def is_business_day_by_market(dt: datetime, market: Market) -> bool:
    if dt.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    return dt.date() not in _get_holidays_for_market(market)


def get_last_business_day_by_market(
    market: Market,
    reference_dt: Optional[datetime] = None,
    days_back: int = 0,
) -> datetime:
    """
    Returns the last business day for a given market, optionally going back N business days.
    """
    current = (reference_dt or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)

    # First, step back 'days_back' business days
    steps_remaining = days_back
    while steps_remaining > 0:
        current -= timedelta(days=1)
        if is_business_day_by_market(current, market):
            steps_remaining -= 1

    # Then, if current is not a business day, walk back to previous business day
    while not is_business_day_by_market(current, market):
        current -= timedelta(days=1)

    return current

