"""
Configuración centralizada del sistema
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Configuración centralizada para Portfolio Replicator"""
    
    # Mercado
    market: str = "argentina"
    
    # APIs y credenciales (se cargan dinámicamente)
    finnhub_api_key: str = ""
    gemini_api_key: str = ""
    
    # IOL (se cargan dinámicamente)
    iol_username: str = ""
    iol_password: str = ""
    
    # Fuentes CCL (orden de prioridad)
    ccl_sources: List[str] = field(default_factory=lambda: ["dolarapi", "iol_al30"])
    preferred_ccl_source: str = "dolarapi_ccl"  # Compatible con app/config.py
    
    # Umbrales y configuraciones
    arbitrage_threshold: float = 0.005  # 0.5%
    cache_ttl_seconds: int = 180
    
    # Configuraciones de portfolio
    DEFAULT_CURRENCY: str = "ARS"
    
    # Configuraciones de red
    request_timeout: int = 30
    retry_attempts: int = 3
    
    
    @classmethod
    def from_env(cls) -> "Config":
        """Crea configuración desde variables de entorno y archivos .prefs.json"""
        # 0. Cargar archivo .env si existe
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv no instalado, continuar
        
        config = cls()
        
        # 1. Cargar desde .prefs.json si existe
        prefs_file = Path(".prefs.json")
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                    
                # Aplicar valores desde .prefs.json
                if 'arbitrage_threshold' in prefs:
                    config.arbitrage_threshold = float(prefs['arbitrage_threshold'])
                if 'request_timeout' in prefs:
                    config.request_timeout = int(prefs['request_timeout'])
                if 'cache_ttl_seconds' in prefs:
                    config.cache_ttl_seconds = int(prefs['cache_ttl_seconds'])
                    
                print(f"📄 Configuración cargada desde .prefs.json")
            except Exception as e:
                print(f"⚠️  Error leyendo .prefs.json: {e}")
        
        # 2. Variables de entorno tienen prioridad (sobrescriben .prefs.json)
        
        # Cargar API keys desde variables de entorno
        config.finnhub_api_key = os.getenv("FINNHUB_API_KEY", "")
        config.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        config.iol_username = os.getenv("IOL_USERNAME", "")
        config.iol_password = os.getenv("IOL_PASSWORD", "")
        
        # Cargar otros valores de configuración
        if os.getenv("ARBITRAGE_THRESHOLD"):
            config.arbitrage_threshold = float(os.getenv("ARBITRAGE_THRESHOLD"))
        if os.getenv("REQUEST_TIMEOUT"):
            config.request_timeout = int(os.getenv("REQUEST_TIMEOUT"))
        if os.getenv("CACHE_TTL_SECONDS"):
            config.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS"))
            
        return config
    
    def validate(self) -> None:
        """Valida que la configuración sea válida"""
        if not self.finnhub_api_key:
            print("⚠️  FINNHUB_API_KEY no configurada - precios internacionales limitados")
        
        if not self.gemini_api_key:
            print("⚠️  GEMINI_API_KEY no configurada - mapeo Excel/CSV limitado")
        
        if self.arbitrage_threshold <= 0:
            raise ValueError("arbitrage_threshold debe ser > 0")