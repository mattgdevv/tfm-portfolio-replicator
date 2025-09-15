"""
Servicio para obtener cotizaciones del dólar con sistema de fallback
"""

import requests
import asyncio
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fuentes de dólar disponibles para el sistema ETL
DollarSource = Literal["dolarapi_ccl", "ccl_al30", "dolarapi_mep"]

class DollarRateService:
    """Servicio para obtener cotizaciones del dólar con múltiples fuentes"""
    
    def __init__(self, config=None):
        # Configuración mediante config opcional (backward compatible)
        if config:
            self.timeout = getattr(config, 'request_timeout', 30)  # Usar 30s por defecto en lugar de 10
            self._cache_ttl_seconds = getattr(config, 'cache_ttl_seconds', 300)  # 5 minutos por defecto
            self.preferred_ccl_source = getattr(config, 'preferred_ccl_source', 'dolarapi_ccl')
        else:
            # Valores por defecto mejorados para mantener compatibilidad
            self.timeout = 30  # Aumentado de 10 a 30 segundos
            self._cache_ttl_seconds = 300  # Aumentado de 180 a 300 segundos (5 minutos)
            self.preferred_ccl_source = 'dolarapi_ccl'
            
        self.sources_status = {
            "dolarapi_ccl": True,
            "ccl_al30": False,  # Requiere autenticación IOL
            "dolarapi_mep": True,
            # CCL implícito Yahoo eliminado para simplicidad
        }
        self.last_health_check = {}
        self.iol_session = None  # Sesión de IOL para CCL AL30
        # Cache en memoria (TTL corto)
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def set_iol_session(self, session):
        """Establece la sesión de IOL para poder usar CCL AL30"""
        self.iol_session = session
        self.sources_status["ccl_al30"] = session is not None
        if session:
            logger.info("🔐 Sesión IOL establecida - CCL AL30 disponible")
        else:
            logger.info("🔓 Sesión IOL no disponible - CCL AL30 deshabilitado")
        
    async def get_ccl_rate(self, preferred_source: Optional[DollarSource] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene la cotización CCL con estrategia robusta de fallback
        
        Estrategia de fallback robusta:
        1. DolarAPI (primario - más confiable y rápido)
        2. IOL AL30/AL30D (secundario - requiere autenticación pero muy preciso)  
        3. Yahoo CCL Implícito (terciario - calculado y confiable)
        
        Args:
            preferred_source: Fuente preferida. Si None, usa configuración global.
            
        Returns:
            Dict con información de la cotización o None si fallan todas
        """
        
        # Determinar fuente preferida
        if preferred_source is None:
            preferred_source = self.preferred_ccl_source
            
        # Estrategia de fallback simple (sin Yahoo)
        if preferred_source == "dolarapi_ccl":
            # DolarAPI primero, luego IOL
            sources = ["dolarapi_ccl", "ccl_al30"]
        elif preferred_source == "ccl_al30":
            # IOL primero (si disponible), luego DolarAPI
            sources = ["ccl_al30", "dolarapi_ccl"]
        else:
            # Fallback general
            sources = ["dolarapi_ccl", "ccl_al30"]
            
        attempted_sources = []
        
        # 0) Revisar cache por fuente en orden de prioridad
        for source in sources:
            cached = self._get_from_cache(f"ccl:{source}")
            if cached:
                logger.debug(f"♻️  CCL cache hit: {source} -> ${cached['rate']}")  # Cambio a debug para reducir ruido
                cached["source"] = source
                cached["preferred_source"] = preferred_source
                cached["fallback_used"] = source != preferred_source
                cached["attempted_sources"] = [source]
                cached["timestamp"] = datetime.now().isoformat()
                return cached

        # 1) Intentar fuentes en vivo
        for source in sources:
            if not self.sources_status.get(source, False):
                logger.warning(f"🚫 Fuente {source} marcada como no disponible, saltando...")
                continue
                
            try:
                logger.debug(f"🔍 Intentando obtener CCL desde: {source}")
                attempted_sources.append(source)
                
                if source == "dolarapi_ccl":
                    result = await self._get_dolarapi_ccl()
                elif source == "ccl_al30":
                    result = await self._get_ccl_al30()
                # CCL implícito Yahoo eliminado
                else:
                    continue
                    
                if result:
                    logger.debug(f"✅ CCL obtenido exitosamente desde {source}: ${result['rate']}")
                    
                    # Mensaje conciso sobre fallback
                    if source != preferred_source:
                        fallback_info = f"usando {result.get('source_name', source)}"
                        logger.info(f"📊 CCL: ${result['rate']:.2f} ({fallback_info})")
                    else:
                        logger.info(f"📊 CCL: ${result['rate']:.2f} (fuente primaria)")
                    
                    full = {
                        **result,
                        "source": source,
                        "preferred_source": preferred_source,
                        "fallback_used": source != preferred_source,
                        "attempted_sources": attempted_sources,
                        "timestamp": datetime.now().isoformat()
                    }
                    # Guardar en cache por fuente
                    self._set_cache(f"ccl:{source}", full)
                    return full
                    
            except Exception as e:
                logger.debug(f"❌ Error en fuente {source}: {str(e)}")
                self.sources_status[source] = False
                # No imprimir errores por fuente individual - solo al final si todas fallan
                
        # Si llegamos aquí, todas las fuentes fallaron
        logger.error(f"❌ Todas las fuentes CCL fallaron. Fuentes intentadas: {attempted_sources}")
        
        # ÚLTIMO RECURSO: Intentar cache expirado como fallback
        for source in sources:
            cached_expired = self._get_from_cache_expired_ok(f"ccl:{source}")
            if cached_expired:
                age_seconds = (datetime.now() - cached_expired.get("_ts", datetime.now())).total_seconds()
                age_minutes = int(age_seconds / 60)
                
                logger.warning(f"⚠️ Usando CCL en cache expirado de {source} (edad: {age_minutes} min)")
                print(f"⚠️ Usando CCL en cache expirado: ${cached_expired['rate']:.2f} (edad: {age_minutes} min)")
                
                # Limpiar metadatos internos y agregar info de fallback
                result = {k: v for k, v in cached_expired.items() if k != "_ts"}
                result.update({
                    "source": source,
                    "preferred_source": preferred_source,
                    "fallback_used": True,
                    "cache_fallback": True,
                    "attempted_sources": attempted_sources,
                    "timestamp": datetime.now().isoformat()
                })
                return result
        
        # Si no hay ni cache expirado, entonces sí fallar
        print(f"❌ ERROR: No se pudo obtener cotización CCL")
        print(f"   • Fuentes intentadas: {', '.join(attempted_sources)}")
        if "ccl_al30" in attempted_sources and not self.iol_session:
            print(f"   • Consejo: Autentique con IOL para habilitar fallback AL30")
        return None

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts = entry.get("_ts")
        if not ts:
            return None
        age = (datetime.now() - ts).total_seconds()
        if age > self._cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        # Devolver copia sin metadatos internos
        data = {k: v for k, v in entry.items() if k != "_ts"}
        return data

    def _set_cache(self, key: str, value: Dict[str, Any]) -> None:
        to_store = dict(value)
        to_store["_ts"] = datetime.now()
        self._cache[key] = to_store
    
    def _get_from_cache_expired_ok(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene entrada del cache aunque esté expirada.
        Usado como último fallback cuando todas las fuentes fallan.
        """
        entry = self._cache.get(key)
        if not entry:
            return None
        # No verificar TTL - devolver aunque esté expirado
        return entry

    
    async def _get_dolarapi_ccl(self) -> Optional[Dict[str, Any]]:
        """Obtiene CCL desde dolarapi.com"""
        
        url = "https://dolarapi.com/v1/dolares/contadoconliqui"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Validar datos
            if not data.get("venta") or data["venta"] <= 0:
                raise ValueError("Datos inválidos: precio venta no válido")
                
            return {
                "rate": float(data["venta"]),
                "buy": float(data.get("compra", 0)),
                "sell": float(data["venta"]),
                "last_update": data.get("fechaActualizacion"),
                "source_name": data.get("nombre", "CCL"),
                "raw_data": data
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error de conexión dolarapi: {str(e)}")
        except (ValueError, KeyError) as e:
            raise Exception(f"Error procesando datos dolarapi: {str(e)}")
    
    async def _get_ccl_al30(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene CCL calculado desde bonos AL30/AL30D usando IOL
        CCL = AL30 (ARS) / AL30D (USD)
        """
        if not self.iol_session:
            raise Exception("Sesión de IOL no disponible. No se puede obtener CCL AL30.")
            
        try:
            # URLs para obtener cotizaciones de bonos desde IOL
            al30_url = "https://api.invertironline.com/api/v2/bCBA/Titulos/AL30/Cotizacion"
            al30d_url = "https://api.invertironline.com/api/v2/bCBA/Titulos/AL30D/Cotizacion"
            
            # Obtener cotizaciones en paralelo usando la sesión de IOL
            async def get_bond_price(url: str, bond_name: str) -> float:
                try:
                    response = self.iol_session.get(url, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Buscar el precio de venta (ultimoPrecio según documentación IOL)
                    price = data.get("ultimoPrecio")
                    if not price or price <= 0:
                        raise ValueError(f"Precio inválido para {bond_name}: {price}")
                    
                    return float(price)
                    
                except Exception as e:
                    raise Exception(f"Error obteniendo {bond_name}: {str(e)}")
            
            # Obtener precios en paralelo
            al30_price, al30d_price = await asyncio.gather(
                get_bond_price(al30_url, "AL30"),
                get_bond_price(al30d_url, "AL30D")
            )
            
            # Calcular CCL
            ccl_rate = al30_price / al30d_price
            
            logger.info(f"📊 CCL AL30 calculado: AL30=${al30_price} / AL30D=${al30d_price} = ${ccl_rate}")
            
            return {
                "rate": ccl_rate,
                "buy": ccl_rate,  # Mismo valor para compra/venta
                "sell": ccl_rate,
                "last_update": datetime.now().isoformat(),
                "source_name": "CCL AL30",
                "al30_price": al30_price,
                "al30d_price": al30d_price,
                "calculation_method": "AL30/AL30D (IOL)"
            }
            
        except Exception as e:
            raise Exception(f"Error calculando CCL AL30: {str(e)}")
    
    async def get_mep_rate(self) -> Optional[Dict[str, Any]]:
        """Obtiene cotización MEP desde dolarapi"""
        
        url = "https://dolarapi.com/v1/dolares/bolsa"
        
        try:
            logger.info("🔍 Obteniendo MEP desde dolarapi...")
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Validar datos
            if not data.get("venta") or data["venta"] <= 0:
                raise ValueError("Datos MEP inválidos")
                
            result = {
                "rate": float(data["venta"]),
                "buy": float(data.get("compra", 0)),
                "sell": float(data["venta"]),
                "last_update": data.get("fechaActualizacion"),
                "source_name": data.get("nombre", "MEP"),
                "source": "dolarapi_mep",
                "timestamp": datetime.now().isoformat(),
                "raw_data": data
            }
            
            logger.info(f"✅ MEP obtenido: ${result['rate']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo MEP: {str(e)}")
            return None
    
