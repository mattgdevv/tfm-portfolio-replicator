"""
Integración para obtener datos históricos de BYMA
Incluye CCL histórico y precios de CEDEARs
"""

import requests
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import urllib3

from ..utils.business_days import get_last_business_day_by_market, is_business_day_by_market, get_market_status_message

# Configurar logging
logger = logging.getLogger(__name__)

# Suppress SSL warnings for BYMA API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BYMAIntegration:
    """Servicio para obtener datos históricos de BYMA"""
    
    def __init__(self, config=None):
        self.base_url = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
        self.timeout = getattr(config, 'request_timeout', 15) if config else 15
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
        return get_last_business_day_by_market("AR", reference)
    
    def _is_market_closed(self) -> bool:
        """Verifica si mercados argentinos están cerrados (fines de semana o feriados)"""
        return not is_business_day_by_market(datetime.now(), "AR")
    
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

        # 🏦 Check market status FIRST - evita requests innecesarios cuando mercado cerrado
        market_message = get_market_status_message("AR")
        if market_message:
            logger.info(market_message)
            return None  # ✅ Trigger fallback limpio, sin errores

        # 🔍 Check BYMA health en días hábiles - detectar caídas de servicio
        if is_business_day_by_market(datetime.now(), "AR"):
            health_check = await self.check_byma_health()
            if not health_check["status"]:
                fallback_message = f"⚠️ BYMA no responde en día hábil ({health_check['response_time']}s) - {health_check['error']} - Usando precios internacionales y CCL para estimar precios de CEDEARs"
                logger.warning(fallback_message)
                return None  # ✅ Trigger fallback limpio con mensaje informativo
        
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

    async def check_byma_health(self) -> Dict[str, Any]:
        """
        Verifica el estado de salud de BYMA API

        Returns:
            Dict con información de salud:
            - status: bool (True si operativo)
            - response_time: float (tiempo de respuesta en segundos)
            - error: str (mensaje de error si falla)
            - business_day: bool (si es día hábil)
        """
        import time
        start_time = time.time()

        result = {
            "status": False,
            "response_time": 0.0,
            "error": "",
            "business_day": is_business_day_by_market(datetime.now(), "AR")
        }

        try:
            # Usar la misma configuración que la request real
            url = f"{self.base_url}/cedears"
            payload = {
                "excludeZeroPxAndQty": True,
                "T1": True,
                "T0": False
            }

            # Usar la sesión HTTP como la request real
            response = self.session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
                verify=False
            )

            response_time = time.time() - start_time
            result["response_time"] = round(response_time, 2)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data and len(data) > 0:  # Verificar que hay datos
                        result["status"] = True
                        result["error"] = ""
                    else:
                        result["error"] = "API responde pero sin datos"
                except json.JSONDecodeError:
                    result["error"] = "Respuesta inválida (no JSON)"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:100]}"

        except requests.exceptions.Timeout:
            result["response_time"] = 10.0
            result["error"] = "Timeout (10s)"
        except requests.exceptions.ConnectionError:
            result["response_time"] = time.time() - start_time
            result["error"] = "Error de conexión"
        except Exception as e:
            result["response_time"] = time.time() - start_time
            result["error"] = f"Error desconocido: {str(e)}"

        return result

    async def check_iol_health(self, iol_session=None) -> Dict[str, Any]:
        """
        Verifica el estado de salud de IOL

        Args:
            iol_session: Sesión de IOL opcional para verificar autenticación

        Returns:
            Dict con información de salud:
            - status: bool (True si operativo)
            - authenticated: bool (True si sesión válida)
            - error: str (mensaje de error si falla)
        """
        result = {
            "status": False,
            "authenticated": False,
            "error": ""
        }

        if not iol_session:
            result["error"] = "Sin sesión IOL"
            return result

        try:
            # Verificar si la sesión IOL existe y está configurada
            if iol_session and hasattr(iol_session, 'headers'):
                # Verificar si tiene headers de autorización (indicativo de autenticación)
                if 'Authorization' in iol_session.headers:
                    result["authenticated"] = True

                    # Hacer una request de prueba simple (timeout más corto para health check)
                    health_check_url = "https://api.invertironline.com/api/v2/Usuario"
                    health_timeout = min(self.timeout, 5)  # Usar config pero máximo 5s para health check
                    response = iol_session.get(health_check_url, timeout=health_timeout)

                    if response.status_code == 200:
                        result["status"] = True
                    else:
                        result["error"] = f"HTTP {response.status_code}"
                else:
                    result["error"] = "Sesión sin autenticación"
            else:
                result["error"] = "Sesión no inicializada"

        except Exception as e:
            result["error"] = f"Error verificando IOL: {str(e)}"

        if result["authenticated"]:
            result["status"] = True

        return result

