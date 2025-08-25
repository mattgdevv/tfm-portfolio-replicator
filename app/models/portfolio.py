from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Position(BaseModel):
    symbol: str
    quantity: float
    price: Optional[float] = None
    currency: str
    total_value: Optional[float] = None
    # Campos para conversiones de CEDEARs
    is_cedear: bool = False
    underlying_symbol: Optional[str] = None
    underlying_quantity: Optional[float] = None
    conversion_ratio: Optional[float] = None
    # Campos para FCIs
    is_fci_usd: bool = False
    is_fci_ars: bool = False
    # Campos para cotización del dólar
    dollar_rate: Optional[float] = None
    dollar_source: Optional[str] = None
    total_value_ars: Optional[float] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.total_value is None and self.price is not None:
            self.total_value = self.quantity * self.price

class ConvertedPortfolio(BaseModel):
    """Portfolio con activos convertidos a subyacentes."""
    original_positions: List[Position]
    converted_positions: List[Position]
    broker: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    conversion_summary: dict = Field(default_factory=dict)

class Portfolio(BaseModel):
    positions: List[Position]
    broker: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 10,
                        "price": 100.5,
                        "currency": "ARS",
                        "total_value": 1005.0
                    }
                ],
                "broker": "iol",
                "timestamp": "2024-03-14T12:00:00"
            }
        } 