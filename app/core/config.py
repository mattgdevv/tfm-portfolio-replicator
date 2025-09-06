"""
Configuración centralizada del sistema
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Configuración centralizada para Portfolio Replicator"""
    
    # Mercado
    market: str = "argentina"
    
    # APIs y credenciales
    finnhub_api_key: str = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # IOL
    iol_username: str = field(default_factory=lambda: os.getenv("IOL_USERNAME", ""))
    iol_password: str = field(default_factory=lambda: os.getenv("IOL_PASSWORD", ""))
    
    # Fuentes CCL (orden de prioridad)
    ccl_sources: List[str] = field(default_factory=lambda: ["dolarapi", "iol_al30"])
    
    # Umbrales y configuraciones
    arbitrage_threshold: float = 0.005  # 0.5%
    cache_ttl_seconds: int = 180
    
    # Configuraciones de portfolio
    DEFAULT_CURRENCY: str = "ARS"
    
    # Configuraciones de red
    request_timeout: int = 30
    retry_attempts: int = 3
    
    # Modo mock para testing
    mock_iol: bool = field(default_factory=lambda: os.getenv("MOCK_IOL", "0") == "1")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Crea configuración desde variables de entorno"""
        return cls()
    
    def validate(self) -> None:
        """Valida que la configuración sea válida"""
        if not self.finnhub_api_key:
            print("⚠️  FINNHUB_API_KEY no configurada - precios internacionales limitados")
        
        if not self.gemini_api_key:
            print("⚠️  GEMINI_API_KEY no configurada - mapeo Excel/CSV limitado")
        
        if self.arbitrage_threshold <= 0:
            raise ValueError("arbitrage_threshold debe ser > 0")