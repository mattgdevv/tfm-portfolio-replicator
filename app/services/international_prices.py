"""
Servicio para obtener precios internacionales de acciones
Solo usa Finnhub - Yahoo Finance eliminado para simplicidad
"""

import os
import asyncio
import requests
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timedelta
import logging

# Configurar logging
logger = logging.getLogger(__name__)

PriceSource = Literal["finnhub"]

class InternationalPriceService:
    """Servicio para obtener precios de acciones internacionales usando Finnhub"""
    
    def __init__(self, config=None):
        # Configuración mediante config opcional (backward compatible)
        self.timeout = config.request_timeout if config else 10
        # Leer API key desde Config o fallback a .env
        if config and hasattr(config, 'finnhub_api_key'):
            self.finnhub_api_key = config.finnhub_api_key
        else:
            self.finnhub_api_key = os.getenv("FINNHUB_API_KEY")
        self.finnhub_base_url = "https://finnhub.io/api/v1"
        
        # Estado de fuentes
        self.sources_status = {
            "finnhub": bool(self.finnhub_api_key)
        }
        
        # Rate limiting para Finnhub (60 calls/min = 1 call/segundo)
        self.last_finnhub_call = 0
        self.finnhub_min_interval = 1.0  # segundos
        
        # Cache para precios (TTL de 72 horas para cubrir fines de semana)
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_hours = 72  # 72 horas = 3 días
        
        
    def _get_from_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene precio desde caché si está disponible y válido"""
        if symbol not in self._price_cache:
            return None
            
        cached_data = self._price_cache[symbol]
        cache_time = cached_data.get('cached_at')
        
        if not cache_time:
            return None
            
        # Verificar si el caché expiró
        cache_age = datetime.now() - cache_time
        if cache_age > timedelta(hours=self._cache_ttl_hours):
            # Caché expirado, eliminarlo
            del self._price_cache[symbol]
            return None
            
        logger.debug(f"[CACHE] Cache hit para {symbol}: ${cached_data['price']:.2f} USD (age: {cache_age})")
        return cached_data.copy()
        
    def _set_cache(self, symbol: str, price_data: Dict[str, Any]) -> None:
        """Guarda precio en caché con timestamp"""
        cache_entry = price_data.copy()
        cache_entry['cached_at'] = datetime.now()
        cache_entry['cache_source'] = 'finnhub'
        self._price_cache[symbol] = cache_entry
        logger.debug(f"[CACHE] Precio de {symbol} guardado en caché: ${price_data['price']:.2f} USD")
        
    async def get_stock_price(self, symbol: str, preferred_source: PriceSource = "finnhub") -> Optional[Dict[str, Any]]:
        """
        Obtiene el precio de una acción internacional usando Finnhub con fallback a caché
        
        Args:
            symbol: Símbolo de la acción (ej: "TSLA", "PLTR")
            preferred_source: Fuente preferida (solo "finnhub" disponible)
            
        Returns:
            Dict con información del precio o None si falla
        """
        
        # Solo Finnhub disponible
        sources = ["finnhub"]
            
        attempted_sources = []
        
        for source in sources:
            if not self.sources_status.get(source, False):
                logger.warning(f"🚫 Fuente {source} no disponible para {symbol}")
                continue
                
            try:
                logger.debug(f"[SEARCH] Obteniendo precio de {symbol} desde: {source}")
                attempted_sources.append(source)
                
                if source == "finnhub":
                    result = await self._get_finnhub_price(symbol)
                else:
                    continue
                    
                if result:
                    logger.debug(f"[SUCCESS] Precio de {symbol} obtenido desde {source}: ${result['price']}")
                    
                    # Guardar en caché para futuros fallbacks
                    self._set_cache(symbol, result)
                    
                    # Finnhub es la única fuente
                    logger.debug(f"[DATA] {symbol}: Precio obtenido desde {source.upper()}")
                    
                    return {
                        **result,
                        "symbol": symbol,
                        "source": source,
                        "preferred_source": preferred_source,
                        "fallback_used": False,
                        "cache_used": False,
                        "attempted_sources": attempted_sources,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except Exception as e:
                logger.debug(f"[ERROR] {source} falló para {symbol}: {str(e)}")
                # No deshabilitar fuentes globalmente por errores de símbolos individuales
                # Las fuentes pueden fallar para un símbolo pero funcionar para otros
                
        # Si llegamos aquí, todas las fuentes fallaron - intentar caché
        logger.warning(f"[ERROR] Finnhub falló para {symbol}, intentando caché...")
        cached_result = self._get_from_cache(symbol)
        
        if cached_result:
            logger.info(f"[CACHE] Usando precio desde caché para {symbol}: ${cached_result['price']:.2f} USD")
            
            return {
                **cached_result,
                "symbol": symbol,
                "source": "cache",
                "preferred_source": preferred_source,
                "fallback_used": True,
                "cache_used": True,
                "attempted_sources": attempted_sources + ["cache"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Si llegamos aquí, tanto Finnhub como caché fallaron
        logger.warning(f"[ERROR] No se pudo obtener precio de {symbol} desde ninguna fuente (incluyendo caché)")
        return None
    
    async def _get_finnhub_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene precio desde Finnhub API"""
        
        if not self.finnhub_api_key:
            raise Exception("FINNHUB_API_KEY no configurada")
        
        # Rate limiting: esperar si es necesario
        now = datetime.now().timestamp()
        time_since_last_call = now - self.last_finnhub_call
        if time_since_last_call < self.finnhub_min_interval:
            wait_time = self.finnhub_min_interval - time_since_last_call
            logger.debug(f"⏳ Rate limiting: esperando {wait_time:.1f}s para {symbol}")
            await asyncio.sleep(wait_time)
        
        try:
            url = f"{self.finnhub_base_url}/quote"
            params = {
                "symbol": symbol,
                "token": self.finnhub_api_key
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Actualizar timestamp del último call
            self.last_finnhub_call = datetime.now().timestamp()
            
            # Validar datos
            current_price = data.get("c")  # current price
            if not current_price or current_price <= 0:
                raise ValueError(f"Precio inválido para {symbol}: {current_price}")
            
            return {
                "price": float(current_price),
                "currency": "USD",
                "previous_close": data.get("pc"),
                "day_high": data.get("h"),
                "day_low": data.get("l"),
                "day_open": data.get("o"),
                "timestamp_unix": data.get("t"),
                "source_name": "Finnhub",
                "raw_data": data
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error de conexión Finnhub: {str(e)}")
        except (ValueError, KeyError) as e:
            raise Exception(f"Error procesando datos Finnhub: {str(e)}")
    
    async def get_multiple_prices(self, symbols: list, preferred_source: PriceSource = "finnhub") -> Dict[str, Dict]:
        """
        Obtiene precios de múltiples símbolos de forma eficiente
        
        Args:
            symbols: Lista de símbolos (ej: ["TSLA", "PLTR", "AMD"])
            preferred_source: Fuente preferida
            
        Returns:
            Dict con símbolo como key y datos de precio como value
        """
        
        logger.info(f"[DATA] Obteniendo precios de {len(symbols)} símbolos: {symbols}")
        
        # Ejecutar todas las consultas en paralelo
        tasks = [
            self.get_stock_price(symbol, preferred_source) 
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        prices = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"[ERROR] Error obteniendo {symbol}: {result}")
                prices[symbol] = None
            else:
                prices[symbol] = result
        
        successful = sum(1 for p in prices.values() if p is not None)
        logger.info(f"[SUCCESS] Precios obtenidos exitosamente: {successful}/{len(symbols)}")
        
        return prices
    
    def get_available_sources(self) -> Dict[str, bool]:
        """Retorna el estado de todas las fuentes"""
        return self.sources_status.copy()
