from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Optional

import holidays


Market = Literal["AR", "US"]

# Mapping de días de la semana en español
WEEKDAY_NAMES = {
    0: "lunes",
    1: "martes", 
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo"
}


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


def get_market_status_message(market: Market = "AR") -> Optional[str]:
    """
    Genera un mensaje informativo cuando el mercado está cerrado
    
    Returns:
        Mensaje explicativo si mercado cerrado, None si abierto
    """
    now = datetime.now()
    
    if is_business_day_by_market(now, market):
        return None  # Mercado abierto
    
    # Mercado cerrado - generar mensaje explicativo
    day_name = WEEKDAY_NAMES[now.weekday()]
    
    # Verificar si es feriado
    holidays_obj = _get_holidays_for_market(market)
    today = now.date()
    
    if today in holidays_obj:
        # Es feriado
        holiday_name = holidays_obj.get(today)
        return f"🏦 Mercados cerrados ({day_name} - {holiday_name}) - Usando precios internacionales y CCL para estimar precios de CEDEARs"
    else:
        # Es fin de semana
        return f"🏦 Mercados cerrados ({day_name}) - Usando precios internacionales y CCL para estimar precios de CEDEARs"

