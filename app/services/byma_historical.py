"""
Servicio para obtener datos históricos de BYMA
Incluye CCL histórico y precios de CEDEARs
"""

import requests
import json
import asyncio
from datetime import datetime, timedelta
try:
    import holidays
    AR_HOLIDAYS = holidays.country_holidays('AR')
except Exception:
    holidays = None
    AR_HOLIDAYS = None
from typing import Dict, List, Optional, Any
import logging
import urllib3

# Configurar logging
logger = logging.getLogger(__name__)

# Suppress SSL warnings for BYMA API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BYMAHistoricalService:
    """Servicio para obtener datos históricos de BYMA"""
    
    def __init__(self):
        self.base_url = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
        self.timeout = 15
        self.session = requests.Session()
        
        # Headers comunes
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Portfolio-Replicator/1.0"
        }
        
        # Cache simple para evitar requests repetidos
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos

    @staticmethod
    def get_last_business_day(reference: Optional[datetime] = None) -> datetime:
        """Devuelve el último día hábil (evita fines de semana y feriados AR si disponible)."""
        ref = reference or datetime.now()
        cur = ref
        # Retroceder si es fin de semana o feriado
        def is_business_day(d: datetime) -> bool:
            if d.weekday() >= 5:  # 5 sáb, 6 dom
                return False
            if AR_HOLIDAYS is not None:
                # Comparar por fecha (YYYY-MM-DD)
                try:
                    date_only = d.date()
                    if date_only in AR_HOLIDAYS:
                        return False
                except Exception:
                    pass
            return True

        while not is_business_day(cur):
            cur -= timedelta(days=1)
        # Si hoy es hábil pero aún no hay cierre, el caller decide si usar ayer.
        return cur
    
    async def get_cedear_price_eod(self, symbol: str, date: Optional[str] = None) -> Optional[float]:
        """
        Obtiene precio de cierre (EOD) de un CEDEAR desde BYMA
        
        Args:
            symbol: Símbolo del CEDEAR (ej: "TSLA")
            date: Fecha en formato YYYY-MM-DD (opcional, por defecto ayer)
            
        Returns:
            Precio de cierre en ARS o None si no se encuentra
        """
        
        try:
            # Obtener datos actuales de CEDEARs
            cedeares_data = await self._get_cedeares_data()
            
            if not cedeares_data:
                logger.error("❌ No se pudieron obtener datos de CEDEARs desde BYMA")
                return None
            
            # Buscar el CEDEAR específico
            for cedear in cedeares_data:
                if cedear.get('symbol') == symbol:
                    # Para datos EOD, usamos el precio actual como proxy
                    # TODO: Implementar endpoint específico para datos históricos cuando esté disponible
                    price = cedear.get('trade') or cedear.get('settlementPrice')
                    
                    if price and price > 0:
                        logger.debug(f"📈 BYMA EOD {symbol}: ${price:.2f} ARS")
                        return float(price)
                    else:
                        logger.warning(f"⚠️  Precio no válido para {symbol}: {price}")
                        return None
            
            logger.warning(f"⚠️  CEDEAR {symbol} no encontrado en datos BYMA")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio EOD BYMA para {symbol}: {str(e)}")
            return None
    
    async def get_ccl_rate_historical(self, date: Optional[str] = None) -> Optional[float]:
        """
        Obtiene el valor del CCL para la fecha indicada usando el dataset histórico
        publicado por BYMA (endpoint `get_indice_dolar`). Si no se pasa fecha,
        devuelve el valor del día hábil anterior.

        El dataset completo se cachea durante `self._cache_timeout` segundos para
        evitar descargas repetitivas.

        Args:
            date: Fecha en formato ``YYYY-MM-DD``. Si es ``None`` se utiliza ayer.

        Returns:
            Valor de cierre del CCL (float) o ``None`` si no se encuentra.
        """

        try:
            # 1️⃣ Determinar la fecha objetivo (último día hábil)
            if date is None:
                target_dt = self.get_last_business_day(datetime.now())
            else:
                target_dt = self.get_last_business_day(datetime.strptime(date, "%Y-%m-%d"))

            # 2️⃣ Obtener o descargar el dataset histórico
            cache_key = "ccl_historical_data"
            data = self._get_from_cache(cache_key)
            if data is None:
                url = "https://data-widgets.byma.com.ar/wp-admin/admin-ajax.php"
                payload = {"action": "get_indice_dolar"}
                logger.debug("🔍 Descargando dataset histórico CCL desde BYMA…")
                
                # WordPress AJAX requiere form data, no JSON
                headers = {
                    "User-Agent": "Portfolio-Replicator/1.0"
                    # NO incluir Content-Type: application/json
                }
                
                resp = self.session.post(
                    url,
                    data=payload,  # form data, no json=payload
                    headers=headers,
                    timeout=self.timeout,
                    verify=False  # BYMA widget usa certificado intermedio que falla
                )
                resp.raise_for_status()
                raw = resp.json()
                if isinstance(raw, dict) and "result" in raw:
                    data = raw["result"]
                    self._set_cache(cache_key, data)
                else:
                    logger.warning("⚠️  Formato inesperado en respuesta del CCL histórico BYMA")
                    return None

            if not data:
                logger.warning("⚠️  Dataset CCL histórico vacío")
                return None

            # 3️⃣ Construir índice por fecha para búsqueda rápida
            by_date = {item.get("date"): item for item in data if "date" in item}

            # 4️⃣ Buscar el registro por fecha; si no está, retroceder 1–2 hábiles
            def find_record(dt: datetime):
                return by_date.get(dt.strftime("%Y-%m-%d"))

            used_dt = target_dt
            record = find_record(target_dt)
            if not record:
                fallback_dt = self.get_last_business_day(target_dt - timedelta(days=1))
                record = find_record(fallback_dt)
                if record:
                    used_dt = fallback_dt
            if not record:
                fallback_dt2 = self.get_last_business_day(target_dt - timedelta(days=2))
                record = find_record(fallback_dt2)
                if record:
                    used_dt = fallback_dt2
            if not record:
                logger.warning(f"⚠️  No se encontró CCL histórico para {target_dt.strftime('%Y-%m-%d')} (ni con retroceso 1–2 hábiles)")
                return None

            price = record.get("cclClosingPrice") or record.get("bymaClosingPrice")
            if price:
                logger.debug(f"💱 BYMA CCL histórico {used_dt.strftime('%Y-%m-%d')}: ${float(price):.2f} ARS/USD")
                return float(price)

            logger.warning(f"⚠️  Registro de CCL inválido para {date_str}: {record}")
            return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo CCL histórico BYMA: {str(e)}")
            return None
    
    async def _get_cedeares_data(self) -> Optional[List[Dict]]:
        """Obtiene datos de CEDEARs desde BYMA API"""
        
        cache_key = "cedeares_data"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.base_url}/cedears"
            payload = {
                "excludeZeroPxAndQty": True,
                "T1": True,
                "T0": False,
                "Content-Type": "application/json, text/plain"
            }
            
            logger.debug("🔍 Obteniendo datos de CEDEARs desde BYMA...")
            
            response = self.session.post(
                url, 
                json=payload, 
                headers=self.headers, 
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                logger.debug(f"✅ Obtenidos {len(data)} CEDEARs desde BYMA")
                self._set_cache(cache_key, data)
                return data
            else:
                logger.warning("⚠️  Respuesta BYMA vacía o formato incorrecto")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión BYMA CEDEARs: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing JSON BYMA CEDEARs: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado BYMA CEDEARs: {str(e)}")
            return None
    
    async def _get_indices_data(self) -> Optional[List[Dict]]:
        """Obtiene datos de índices desde BYMA API"""
        
        cache_key = "indices_data"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Intentar diferentes endpoints para índices
            possible_urls = [
                f"{self.base_url}/indices",
                f"{self.base_url}/index",
                f"{self.base_url}/indicators"
            ]
            
            for url in possible_urls:
                try:
                    logger.debug(f"🔍 Probando endpoint índices: {url}")
                    
                    # Para índices, puede que no necesite payload
                    response = self.session.get(
                        url,
                        headers=self.headers,
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            logger.debug(f"✅ Obtenidos {len(data)} índices desde BYMA")
                            self._set_cache(cache_key, data)
                            return data
                        
                except requests.exceptions.RequestException:
                    continue
            
            logger.warning("⚠️  No se encontraron endpoints válidos para índices BYMA")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error inesperado BYMA índices: {str(e)}")
            return None
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Obtiene datos del cache si no han expirado"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._cache_timeout:
                logger.debug(f"📦 Usando cache para {key}")
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Guarda datos en el cache con timestamp"""
        self._cache[key] = (data, datetime.now().timestamp())
    
    async def get_multiple_cedear_prices_eod(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Obtiene precios EOD para múltiples CEDEARs en paralelo
        
        Args:
            symbols: Lista de símbolos de CEDEARs
            
        Returns:
            Diccionario {symbol: price} o None si hay error
        """
        
        logger.debug(f"🔍 Obteniendo precios EOD BYMA para {len(symbols)} símbolos: {symbols}")
        
        # Optimización: obtener todos los CEDEARs de una vez
        cedeares_data = await self._get_cedeares_data()
        
        if not cedeares_data:
            return {symbol: None for symbol in symbols}
        
        # Crear diccionario de búsqueda rápida
        cedear_dict = {cedear.get('symbol'): cedear for cedear in cedeares_data}
        
        results = {}
        
        for symbol in symbols:
            if symbol in cedear_dict:
                cedear = cedear_dict[symbol]
                price = cedear.get('trade') or cedear.get('settlementPrice')
                
                if price and price > 0:
                    results[symbol] = float(price)
                    logger.debug(f"📈 BYMA EOD {symbol}: ${price:.2f} ARS")
                else:
                    results[symbol] = None
                    logger.warning(f"⚠️  Precio no válido para {symbol}: {price}")
            else:
                results[symbol] = None
                logger.warning(f"⚠️  CEDEAR {symbol} no encontrado en BYMA")
        
        found_count = sum(1 for price in results.values() if price is not None)
        logger.info(f"✅ BYMA EOD: {found_count}/{len(symbols)} precios obtenidos")
        
        return results
    
    def check_service_health(self) -> bool:
        """Verifica si el servicio BYMA está disponible"""
        try:
            url = f"{self.base_url}/cedears"
            payload = {"excludeZeroPxAndQty": True, "T1": True, "T0": False}
            
            response = self.session.post(
                url, 
                json=payload, 
                headers=self.headers, 
                timeout=5,
                verify=False
            )
            
            return response.status_code == 200
            
        except Exception:
            return False

# ❌ ELIMINADO: instancia global - usar build_services() para DI
# byma_historical_service = BYMAHistoricalService()  # DEPRECATED - use build_services()