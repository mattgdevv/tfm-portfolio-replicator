"""
Detector de Arbitraje entre CEDEARs y Activos Subyacentes
Núcleo del TFM - detecta oportunidades de arbitraje comparando precios
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# ❌ ELIMINADO: imports de servicios globales - usar DI
# from .international_prices import international_price_service
# from .dollar_rate import dollar_service  
# from .byma_historical import byma_historical_service
from ..processors.cedeares import CEDEARProcessor

# Configurar logging
logger = logging.getLogger(__name__)

class ArbitrageOpportunity:
    """Representa una oportunidad de arbitraje detectada"""
    
    def __init__(self, symbol: str, cedear_price_usd: float, underlying_price_usd: float, 
                 difference_usd: float, difference_percentage: float, ccl_rate: float,
                 cedear_price_ars: float = None, iol_session_active: bool = False):
        self.symbol = symbol
        self.cedear_price_usd = cedear_price_usd
        self.underlying_price_usd = underlying_price_usd
        self.difference_usd = difference_usd
        self.difference_percentage = difference_percentage
        self.ccl_rate = ccl_rate
        self.cedear_price_ars = cedear_price_ars
        self.iol_session_active = iol_session_active
        self.timestamp = datetime.now().isoformat()
        
        # Determinar recomendación
        if difference_usd > 0:  # CEDEAR más barato
            self.recommendation = "Comprar CEDEAR, vender subyacente"
            self.action = "BUY_CEDEAR"
        else:  # Subyacente más barato
            self.recommendation = "Comprar subyacente, vender CEDEAR"
            self.action = "BUY_UNDERLYING"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la oportunidad a diccionario"""
        return {
            "symbol": self.symbol,
            "cedear_price_usd": self.cedear_price_usd,
            "underlying_price_usd": self.underlying_price_usd,
            "difference_usd": self.difference_usd,
            "difference_percentage": self.difference_percentage,
            "ccl_rate": self.ccl_rate,
            "cedear_price_ars": self.cedear_price_ars,
            "recommendation": self.recommendation,
            "action": self.action,
            "iol_session_active": self.iol_session_active,
            "timestamp": self.timestamp
        }

class ArbitrageDetector:
    """Detector de oportunidades de arbitraje entre CEDEARs y subyacentes"""
    
    def __init__(self, 
                 international_service,
                 dollar_service_dep, 
                 byma_service,
                 cedear_processor,
                 iol_session=None):
        """
        Constructor con Dependency Injection estricta - TODAS las dependencias son requeridas
        
        Args:
            international_service: Servicio de precios internacionales (REQUERIDO)
            dollar_service_dep: Servicio de cotización dólar (REQUERIDO)
            byma_service: Servicio BYMA histórico (REQUERIDO)
            cedear_processor: Procesador CEDEARs (REQUERIDO)
            iol_session: Sesión IOL para modo completo (opcional)
        """
        # Validación estricta de dependencias
        if international_service is None:
            raise ValueError("international_service es requerido - use build_services() para crear instancias")
        if dollar_service_dep is None:
            raise ValueError("dollar_service_dep es requerido - use build_services() para crear instancias")
        if byma_service is None:
            raise ValueError("byma_service es requerido - use build_services() para crear instancias")
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
            
        self.iol_session = iol_session
        self.international_service = international_service
        self.dollar_service_instance = dollar_service_dep
        self.byma_service = byma_service
        self.cedear_processor = cedear_processor
        
        self.mode = "full" if iol_session else "limited"
        # cache por símbolo: {'SYMBOL': {'price_ars': float, 'price_usd': float, 'source': str, 'ts': float}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds: int = 180
        
    def set_iol_session(self, session):
        """Establece la sesión de IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
        logger.info(f"🔄 Modo cambiado a: {self.mode}")
    
    async def detect_single_arbitrage(self, symbol: str, threshold_percentage: float = 0.005) -> Optional[ArbitrageOpportunity]:
        """
        Detecta arbitraje para un símbolo específico
        
        Args:
            symbol: Símbolo del CEDEAR (ej: "TSLA")
            threshold_percentage: Umbral mínimo para considerar arbitraje (default: 0.5%)
            
        Returns:
            ArbitrageOpportunity si hay oportunidad, None si no
        """
        
        logger.debug(f"🔍 Analizando arbitraje para {symbol} (modo: {self.mode})")
        
        try:
            # 1. Obtener precio del activo subyacente (siempre Yahoo/Finnhub)
            underlying_data = await self.international_service.get_stock_price(symbol)
            if not underlying_data:
                logger.error(f"❌ No se pudo obtener precio subyacente para {symbol}")
                return None
            
            underlying_price_usd = underlying_data["price"]
            logger.debug(f"📈 {symbol} subyacente: ${underlying_price_usd:.2f} USD")
            
            # 2. Obtener precio de 1 acción vía CEDEARs
            cedear_price_ars, accion_via_cedear_usd = await self._get_cedear_price_usd(symbol)
            if not accion_via_cedear_usd:
                logger.error(f"❌ No se pudo obtener precio de acción vía CEDEAR para {symbol}")
                return None
            
            logger.debug(f"🏦 {symbol} acción vía CEDEAR: ${accion_via_cedear_usd:.2f} USD (CEDEAR: ${cedear_price_ars:.0f} ARS)")
            
            # 3. Calcular diferencia entre precio directo y vía CEDEARs
            difference_usd = underlying_price_usd - accion_via_cedear_usd
            difference_percentage = abs(difference_usd) / underlying_price_usd
            
            logger.debug(f"📊 Diferencia: ${difference_usd:.2f} USD ({difference_percentage:.1%})")
            
            # 4. Verificar si supera el umbral
            if difference_percentage >= threshold_percentage:
                # Obtener CCL rate usado
                ccl_data = await self.dollar_service_instance.get_ccl_rate()
                ccl_rate = ccl_data["rate"] if ccl_data else 1300.0  # Fallback
                
                opportunity = ArbitrageOpportunity(
                    symbol=symbol,
                    cedear_price_usd=accion_via_cedear_usd,
                    underlying_price_usd=underlying_price_usd,
                    difference_usd=difference_usd,
                    difference_percentage=difference_percentage,
                    ccl_rate=ccl_rate,
                    cedear_price_ars=cedear_price_ars,
                    iol_session_active=(self.mode == "full")
                )
                
                logger.info(f"🚨 OPORTUNIDAD DETECTADA: {symbol} - {difference_percentage:.1%}")
                return opportunity
            else:
                logger.debug(f"✅ {symbol}: Diferencia {difference_percentage:.1%} < {threshold_percentage:.1%} (sin arbitraje)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error analizando {symbol}: {str(e)}")
            return None
    
    async def _get_cedear_price_usd(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        Obtiene el precio del CEDEAR en ARS y lo convierte a USD
        
        Returns:
            tuple: (precio_ars, precio_usd)
        """
        
        if self.mode == "full" and self.iol_session:
            # Modo completo: precio en tiempo real desde IOL
            return await self._get_iol_cedear_price(symbol)
        else:
            # Modo limitado: precio real desde BYMA API únicamente
            return await self._get_byma_real_cedear_price(symbol)
    
    async def _get_iol_cedear_price(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precio CEDEAR desde IOL API (modo completo)"""
        
        try:
            url = f"https://api.invertironline.com/api/v2/bcba/Titulos/{symbol}/Cotizacion"
            response = self.iol_session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            precio_cedear_ars = data.get("ultimoPrecio")
            
            if not precio_cedear_ars or precio_cedear_ars <= 0:
                raise ValueError(f"Precio IOL inválido para {symbol}: {precio_cedear_ars}")
            
            # Obtener ratio de conversión
            cedear_info = self.cedear_processor.get_underlying_asset(symbol)
            if not cedear_info:
                raise ValueError(f"No se encontró información del CEDEAR {symbol}")
            
            ratio = cedear_info.get("ratio", "1:1")
            conversion_ratio = self.cedear_processor.parse_ratio(ratio)
            
            # Obtener CCL
            ccl_data = await self.dollar_service_instance.get_ccl_rate()
            ccl_rate = ccl_data["rate"] if ccl_data else 1300.0
            
            # Calcular precio de 1 acción vía CEDEARs
            # Precio_Acción_vía_CEDEAR = (Precio_CEDEAR_ARS × Ratio) ÷ CCL
            precio_accion_via_cedear_usd = (precio_cedear_ars * conversion_ratio) / ccl_rate
            
            logger.debug(f"💰 IOL {symbol}: (${precio_cedear_ars:.0f} × {conversion_ratio}) ÷ ${ccl_rate:.0f} = ${precio_accion_via_cedear_usd:.2f} USD")
            return precio_cedear_ars, precio_accion_via_cedear_usd
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio IOL para {symbol}: {str(e)}")
            return None, None
    
    async def _get_theoretical_cedear_price(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Calcula precio teórico del CEDEAR usando datos de cierre BYMA (modo limitado)"""
        
        try:
            # Obtener información del CEDEAR
            cedear_info = self.cedear_processor.get_underlying_asset(symbol)
            if not cedear_info:
                return None, None
            
            # Obtener ratio de conversión
            ratio = cedear_info.get("ratio", "1:1")
            conversion_ratio = self.cedear_processor.parse_ratio(ratio)
            
            # Obtener precio subyacente para calcular precio teórico del CEDEAR
            underlying_data = await self.international_service.get_stock_price(symbol)
            if not underlying_data:
                return None, None
            
            underlying_price_usd = underlying_data["price"]
            
            # Obtener CCL
            ccl_data = await self.dollar_service_instance.get_ccl_rate()
            ccl_rate = ccl_data["rate"] if ccl_data else 1300.0
            
            # Calcular precio teórico del CEDEAR
            # Si 1 acción cuesta X USD, entonces 1 CEDEAR debería costar (X USD ÷ Ratio) × CCL ARS
            precio_cedear_teorico_usd = underlying_price_usd / conversion_ratio
            precio_cedear_teorico_ars = precio_cedear_teorico_usd * ccl_rate
            
            # Para comparar, necesitamos el precio de 1 acción vía CEDEARs
            # Precio_Acción_vía_CEDEAR = (Precio_CEDEAR_ARS × Ratio) ÷ CCL
            precio_accion_via_cedear_usd = (precio_cedear_teorico_ars * conversion_ratio) / ccl_rate
            
            logger.debug(f"🧮 Teórico {symbol}: CEDEAR=${precio_cedear_teorico_ars:.0f} ARS → Acción vía CEDEAR=${precio_accion_via_cedear_usd:.2f} USD")
            return precio_cedear_teorico_ars, precio_accion_via_cedear_usd
            
        except Exception as e:
            logger.error(f"❌ Error calculando precio teórico para {symbol}: {str(e)}")
            return None, None
    
    async def _get_byma_real_cedear_price(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precio CEDEAR real desde BYMA API (modo limitado estandarizado)"""
        
        try:
            # Obtener información del CEDEAR
            cedear_info = self.cedear_processor.get_underlying_asset(symbol)
            if not cedear_info:
                logger.error(f"❌ No se encontró información del CEDEAR {symbol}")
                return None, None
            
            # Obtener ratio de conversión
            ratio = cedear_info.get("ratio", "1:1")
            conversion_ratio = self.cedear_processor.parse_ratio(ratio)
            
            # Obtener precio CEDEAR real desde BYMA
            cedeares_data = await self.byma_service._get_cedeares_data()
            if not cedeares_data:
                logger.error(f"❌ No se pudieron obtener datos de CEDEARs desde BYMA")
                return None, None
            
            # Buscar el CEDEAR específico
            cedear_data = None
            for cedear in cedeares_data:
                if cedear.get('symbol') == symbol:
                    cedear_data = cedear
                    break
            
            if not cedear_data:
                logger.warning(f"⚠️  CEDEAR {symbol} no encontrado en datos BYMA")
                return None, None
            
            # Extraer precio real (preferir 'trade' sobre 'closingPrice')
            precio_cedear_ars = cedear_data.get('trade') or cedear_data.get('closingPrice')
            
            if not precio_cedear_ars or precio_cedear_ars <= 0:
                logger.warning(f"⚠️  Precio BYMA inválido para {symbol}: {precio_cedear_ars}")
                return None, None
            
            # Obtener CCL
            ccl_data = await self.dollar_service_instance.get_ccl_rate()
            ccl_rate = ccl_data["rate"] if ccl_data else 1300.0
            
            # Calcular precio de 1 acción vía CEDEARs reales
            # Precio_Acción_vía_CEDEAR = (Precio_CEDEAR_ARS × Ratio) ÷ CCL
            precio_accion_via_cedear_usd = (precio_cedear_ars * conversion_ratio) / ccl_rate
            
            logger.debug(f"🏦 BYMA Real {symbol}: CEDEAR=${precio_cedear_ars:.0f} ARS → Acción vía CEDEAR=${precio_accion_via_cedear_usd:.2f} USD")
            return precio_cedear_ars, precio_accion_via_cedear_usd
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio BYMA real para {symbol}: {str(e)}")
            return None, None

    def clear_cedear_cache(self) -> None:
        self._cache.clear()

    def set_cedear_cache_ttl(self, seconds: int) -> None:
        self._cache_ttl_seconds = max(0, int(seconds))
    
    async def detect_portfolio_arbitrages(self, symbols: List[str], threshold_percentage: float = 0.005) -> List[ArbitrageOpportunity]:
        """
        Detecta arbitrajes para una lista de símbolos (portfolio completo)
        
        Args:
            symbols: Lista de símbolos de CEDEARs
            threshold_percentage: Umbral mínimo para considerar arbitraje
            
        Returns:
            Lista de oportunidades de arbitraje detectadas
        """
        
        logger.debug(f"🔍 Analizando arbitrajes para {len(symbols)} símbolos: {symbols}")
        
        # Ejecutar análisis en paralelo para eficiencia
        tasks = [
            self.detect_single_arbitrage(symbol, threshold_percentage)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar oportunidades válidas
        opportunities = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Error analizando {symbol}: {result}")
            elif result is not None:
                opportunities.append(result)
        
        logger.info(f"🎯 Oportunidades detectadas: {len(opportunities)}/{len(symbols)}")
        return opportunities
    
    def format_alert(self, opportunity: ArbitrageOpportunity) -> str:
        """Formatea una alerta de arbitraje para mostrar al usuario"""
        
        symbol = opportunity.symbol
        diff_usd = opportunity.difference_usd
        diff_pct = opportunity.difference_percentage
        cedear_usd = opportunity.cedear_price_usd
        underlying_usd = opportunity.underlying_price_usd
        
        # Determinar dirección de la oportunidad
        if diff_usd > 0:
            direction = "📈 CEDEAR SUBVALUADO"
            profit_text = f"Ganancia potencial: +${abs(diff_usd):.2f} USD"
        else:
            direction = "📉 CEDEAR SOBREVALUADO" 
            profit_text = f"Ganancia potencial: +${abs(diff_usd):.2f} USD"
        
        mode_text = "🔴 TIEMPO REAL (IOL)" if opportunity.iol_session_active else "🟡 BYMA (sin IOL)"
        
        # Alinear contenido en ancho fijo y evitar emojis de ancho variable dentro del recuadro
        inner_width = 42
        top = "┌" + "─" * (inner_width + 2) + "┐"
        bottom = "└" + "─" * (inner_width + 2) + "┘"

        symbol_line = f"{symbol} - {direction}"
        if len(symbol_line) > inner_width:
            symbol_line = symbol_line[:inner_width - 1] + "…"

        line = lambda text: f"│ {text:<{inner_width}} │"

        # Quitar emojis en líneas internas para mantener el ancho estable
        mode_clean = "TIEMPO REAL (IOL)" if opportunity.iol_session_active else "BYMA (sin IOL)"
        profit_clean = profit_text.replace("💰 ", "").strip()

        alert = (
            "\n"
            + "🚨 OPORTUNIDAD DE ARBITRAJE DETECTADA 🚨\n"
            + top + "\n"
            + line(symbol_line) + "\n"
            + line("") + "\n"
            + line(f"Subyacente (NYSE): ${underlying_usd:>9.2f} USD") + "\n"
            + line(f"CEDEAR:            ${cedear_usd:>9.2f} USD") + "\n"
            + line("") + "\n"
            + line(f"{profit_clean}") + "\n"
            + line(f"Diferencia: {diff_pct:>6.1%}") + "\n"
            + line("") + "\n"
            + line("RECOMENDACIÓN:") + "\n"
            + line(f"   {opportunity.recommendation}") + "\n"
            + line("") + "\n"
            + line(f"Modo: {mode_clean}") + "\n"
            + bottom
        )
        
        return alert

# ❌ ELIMINADO: instancia global - usar build_services() para DI
# arbitrage_detector = ArbitrageDetector()  # DEPRECATED - use build_services()