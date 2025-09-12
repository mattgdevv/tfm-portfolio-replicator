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
from ..utils.business_days import get_market_status_message
from ..models.portfolio import Portfolio

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
                 byma_integration,
                 cedear_processor,
                 price_fetcher,
                 iol_session=None,
                 config=None):
        """
        Constructor con Dependency Injection estricta - TODAS las dependencias son requeridas

        Args:
            international_service: Servicio de precios internacionales (REQUERIDO)
            dollar_service_dep: Servicio de cotización dólar (REQUERIDO)
            byma_integration: Servicio BYMA histórico (REQUERIDO)
            cedear_processor: Procesador CEDEARs (REQUERIDO)
            price_fetcher: Servicio unificado de obtención de precios (REQUERIDO)
            iol_session: Sesión IOL para modo completo (opcional)
        """
        # Validación estricta de dependencias
        if international_service is None:
            raise ValueError("international_service es requerido - use build_services() para crear instancias")
        if dollar_service_dep is None:
            raise ValueError("dollar_service_dep es requerido - use build_services() para crear instancias")
        if byma_integration is None:
            raise ValueError("byma_integration es requerido - use build_services() para crear instancias")
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
        if price_fetcher is None:
            raise ValueError("price_fetcher es requerido - use build_services() para crear instancias")

        self.iol_session = iol_session
        self.international_service = international_service
        self.dollar_service_instance = dollar_service_dep
        self.byma_integration = byma_integration
        self.cedear_processor = cedear_processor
        self.price_fetcher = price_fetcher
        self.config = config  # Almacenar config para usar threshold por defecto
        
        self.mode = "full" if iol_session else "limited"
        
    def set_iol_session(self, session):
        """Establece la sesión de IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
        self.price_fetcher.set_iol_session(session)  # Sincronizar con PriceFetcher
        # Log removido para reducir ruido

    def _get_cedear_conversion_info(self, symbol: str) -> tuple[str, float]:
        """
        Helper method para obtener información de conversión del CEDEAR.
        Encapsula lógica repetitiva usada en múltiples métodos.

        Returns:
            tuple: (ratio_str, conversion_ratio_float)
        """
        cedear_info = self.cedear_processor.get_underlying_asset(symbol)
        if not cedear_info:
            raise ValueError(f"No se encontró información del CEDEAR {symbol}")

        ratio = cedear_info.get("ratio", "1:1")
        conversion_ratio = self.cedear_processor.parse_ratio(ratio)
        return ratio, conversion_ratio

    async def _get_ccl_rate_safe(self) -> float:
        """
        Helper method para obtener CCL rate de forma segura con fallback.
        Encapsula lógica repetitiva usada en múltiples métodos.

        Returns:
            float: CCL rate o fallback 1300.0 si no disponible
        """
        ccl_data = await self.dollar_service_instance.get_ccl_rate()
        return ccl_data["rate"] if ccl_data else 1300.0

    async def detect_single_arbitrage(self, symbol: str, threshold_percentage: float = None) -> Optional[ArbitrageOpportunity]:
        """
        Detecta arbitraje para un símbolo específico
        
        Args:
            symbol: Símbolo del CEDEAR (ej: "TSLA")
            threshold_percentage: Umbral mínimo para considerar arbitraje (usa config.arbitrage_threshold si None)
            
        Returns:
            ArbitrageOpportunity si hay oportunidad, None si no
        """
        
        # Usar threshold de config si no se especifica
        if threshold_percentage is None:
            threshold_percentage = self.config.arbitrage_threshold if self.config else 0.005
        
        logger.debug(f"🔍 Analizando arbitraje para {symbol} (modo: {self.mode}, threshold: {threshold_percentage})")
        
        try:
            # 1. Obtener precio del activo subyacente (siempre Yahoo/Finnhub)
            underlying_data = await self.international_service.get_stock_price(symbol)
            if not underlying_data:
                logger.error(f"❌ No se pudo obtener precio subyacente para {symbol}")
                return None
            
            underlying_price_usd = underlying_data["price"]
            logger.debug(f"📈 {symbol} subyacente: ${underlying_price_usd:.2f} USD")
            
            # 2. Obtener precio de 1 acción vía CEDEARs
            cedear_price_ars, accion_via_cedear_usd = await self.price_fetcher.get_cedear_price_with_action_usd(symbol)
            if not accion_via_cedear_usd:
                # FALLBACK: Intentar estimación teórica
                logger.warning(f"⚠️  No se pudo obtener precio real de {symbol}, intentando estimación teórica...")
                cedear_teorico_ars, accion_teorica_usd = await self.price_fetcher.get_theoretical_cedear_price(symbol, underlying_price_usd)
                
                if accion_teorica_usd:
                    logger.info(f"🔮 Usando precio teórico para {symbol}: ${accion_teorica_usd:.2f} USD (CEDEAR teórico: ${cedear_teorico_ars:.0f} ARS)")
                    cedear_price_ars = cedear_teorico_ars
                    accion_via_cedear_usd = accion_teorica_usd
                else:
                    logger.error(f"❌ No se pudo estimar precio teórico para {symbol}")
                    return None
            
            logger.debug(f"🏦 {symbol} acción vía CEDEAR: ${accion_via_cedear_usd:.2f} USD (CEDEAR: ${cedear_price_ars:.0f} ARS)")
            
            # 3. Calcular diferencia entre precio directo y vía CEDEARs
            difference_usd = underlying_price_usd - accion_via_cedear_usd
            difference_percentage = abs(difference_usd) / underlying_price_usd
            
            logger.debug(f"📊 Diferencia: ${difference_usd:.2f} USD ({difference_percentage:.1%})")
            
            # 4. Verificar si supera el umbral
            if difference_percentage >= threshold_percentage:
                # Obtener CCL rate usado
                ccl_rate = await self._get_ccl_rate_safe()
                
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
    
    
    
    

    async def detect_portfolio_arbitrages(self, symbols: List[str], threshold_percentage: float = None) -> List[ArbitrageOpportunity]:
        """
        Detecta arbitrajes para una lista de símbolos (portfolio completo)
        
        Args:
            symbols: Lista de símbolos de CEDEARs
            threshold_percentage: Umbral mínimo para considerar arbitraje (usa config.arbitrage_threshold si None)
            
        Returns:
            Lista de oportunidades de arbitraje detectadas
        """
        
        # Usar threshold de config si no se especifica
        if threshold_percentage is None:
            threshold_percentage = self.config.arbitrage_threshold if self.config else 0.005
        
        logger.debug(f"🔍 Analizando arbitrajes para {len(symbols)} símbolos: {symbols}, threshold: {threshold_percentage}")
        
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

    async def analyze_portfolio(self, portfolio: 'Portfolio', threshold: float = None) -> Dict[str, Any]:
        """
        Análisis completo de portfolio - reemplaza UnifiedAnalysisService

        Args:
            portfolio: Portfolio a analizar
            threshold: Umbral de arbitraje (usa config.arbitrage_threshold si None)

        Returns:
            Dict con análisis completo: precios, arbitraje, métricas
        """

        # Usar threshold de config si no se especifica
        if threshold is None:
            threshold = self.config.arbitrage_threshold if self.config else 0.005

        logger.info(f"🔍 Analizando portfolio con {len(portfolio.positions)} posiciones (threshold: {threshold})")

        # Extraer solo CEDEARs para análisis
        cedear_symbols = []
        for pos in portfolio.positions:
            if self.cedear_processor.is_cedear(pos.symbol):
                cedear_symbols.append(pos.symbol)

        if not cedear_symbols:
            logger.warning("⚠️  No se encontraron CEDEARs en el portfolio")
            return {"arbitrage_opportunities": [], "price_data": {}, "summary": "No CEDEARs found"}

        logger.info(f"📊 Analizando {len(cedear_symbols)} CEDEARs: {cedear_symbols}")

        # Análisis de arbitraje usando el método existente
        opportunities = await self.detect_portfolio_arbitrages(cedear_symbols, threshold)

        # Obtener datos de precios para métricas
        price_data = {}
        sources_used = set()

        for symbol in cedear_symbols:
            try:
                underlying_data = await self.international_service.get_stock_price(symbol)
                if underlying_data:
                    price_data[symbol] = {
                        "underlying_price_usd": underlying_data["price"],
                        "source": underlying_data.get("source", "unknown"),
                        "fallback_used": underlying_data.get("fallback_used", False)
                    }
                    sources_used.add(underlying_data.get("source", "unknown"))
            except Exception as e:
                logger.debug(f"❌ Error obteniendo precios para {symbol}: {e}")
                continue

        # Generar resumen
        mode = "COMPLETO (IOL)" if self.iol_session else "LIMITADO"
        sources_summary = ", ".join(sources_used) if sources_used else "ninguna"

        summary = {
            "mode": mode,
            "total_cedeares": len(cedear_symbols),
            "opportunities_found": len(opportunities),
            "sources_used": sources_summary,
            "threshold": threshold
        }

        return {
            "arbitrage_opportunities": opportunities,
            "price_data": price_data,
            "summary": summary
        }
