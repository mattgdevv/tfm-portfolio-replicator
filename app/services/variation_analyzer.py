"""
Analizador de Variaciones de CEDEARs
Analiza si los CEDEARs se mueven más o menos de lo esperado vs sus subyacentes
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

# [ERROR] ELIMINADO: import de servicio global - migrar a DI cuando sea necesario
# from .international_prices import international_price_service
# [ERROR] ELIMINADO: imports de servicios globales - migrar a DI cuando sea necesario  
# from .dollar_rate import dollar_service
# from .byma_historical import byma_historical_service
from ..processors.cedeares import CEDEARProcessor
from ..utils.business_days import get_market_status_message

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class CEDEARVariationAnalysis:
    """Análisis de variación de un CEDEAR vs su subyacente"""
    
    symbol: str
    
    # Precios históricos (ayer)
    precio_cedear_ayer_ars: float
    precio_underlying_ayer_usd: float
    ccl_ayer: float
    
    # Precios actuales (hoy)
    precio_cedear_hoy_ars: float
    precio_underlying_hoy_usd: float
    ccl_hoy: float
    
    # Variaciones calculadas
    var_cedear: float  # variación local (%)
    var_underlying: float  # variación subyacente (%)
    var_ccl: float  # variación CCL (%)

    
    # Metadatos
    mode: str  # "full" o "limited"
    timestamp: str
    
    def get_strongest_factor(self) -> str:
        """Identifica el factor que más influyó en la variación"""
        factors = {
            "CEDEAR": abs(self.var_cedear),
            "Subyacente": abs(self.var_underlying),
            "CCL": abs(self.var_ccl)
        }
        return max(factors, key=factors.get)


class VariationAnalyzer:
    """Analizador de variaciones de CEDEARs"""
    
    def __init__(self, cedear_processor, international_service, dollar_service, byma_integration, price_fetcher, iol_session=None):
        """
        Constructor con Dependency Injection estricta

        Args:
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
            international_service: Servicio de precios internacionales (REQUERIDO)
            dollar_service: Servicio de cotización dólar (REQUERIDO)
            byma_integration: Servicio BYMA histórico (REQUERIDO)
            price_fetcher: Servicio unificado de obtención de precios (REQUERIDO)
            iol_session: Sesión IOL para modo completo (opcional)
        """
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
        if international_service is None:
            raise ValueError("international_service es requerido - use build_services() para crear instancias")
        if dollar_service is None:
            raise ValueError("dollar_service es requerido - use build_services() para crear instancias")
        if byma_integration is None:
            raise ValueError("byma_integration es requerido - use build_services() para crear instancias")
        if price_fetcher is None:
            raise ValueError("price_fetcher es requerido - use build_services() para crear instancias")

        self.iol_session = iol_session
        self.cedear_processor = cedear_processor
        self.international_service = international_service
        self.dollar_service = dollar_service
        self.byma_integration = byma_integration
        self.price_fetcher = price_fetcher
        self.mode = "full" if iol_session else "limited"
        
    def set_iol_session(self, session):
        """Establece la sesión de IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
        self.price_fetcher.set_iol_session(session)  # Sincronizar con PriceFetcher
        # Log removido para reducir ruido
    
    async def analyze_single_variation(self, symbol: str) -> Optional[CEDEARVariationAnalysis]:
        """
        Analiza la variación de un CEDEAR específico
        
        Args:
            symbol: Símbolo del CEDEAR (ej: "TSLA")
            
        Returns:
            CEDEARVariationAnalysis o None si hay error
        """
        
        logger.debug(f"[SEARCH] Analizando variación para {symbol} (modo: {self.mode})")
        
        try:
            # 1. Obtener precios actuales del subyacente
            underlying_today = await self.international_service.get_stock_price(symbol)
            if not underlying_today:
                logger.error(f"[ERROR] No se pudo obtener precio actual de {symbol}")
                return None
            
            # 2. Obtener precios históricos del subyacente (ayer)
            underlying_yesterday = await self._get_historical_underlying_price(symbol)
            if not underlying_yesterday:
                logger.error(f"[ERROR] No se pudo obtener precio histórico de {symbol}")
                return None
            
            # 3. Obtener precios del CEDEAR (hoy y ayer)
            cedear_today_ars, cedear_yesterday_ars = await self.price_fetcher.get_cedear_price(symbol, include_historical=True)
            if not cedear_today_ars or not cedear_yesterday_ars:
                logger.error(f"[ERROR] No se pudo obtener precios CEDEAR para {symbol}")
                return None
            
            # 4. Obtener CCL (hoy y ayer)
            ccl_today, ccl_yesterday = await self._get_ccl_prices()
            if not ccl_today or not ccl_yesterday:
                logger.error(f"[ERROR] No se pudo obtener precios CCL")
                return None
            
            # 5. Calcular variaciones
            var_cedear = (cedear_today_ars - cedear_yesterday_ars) / cedear_yesterday_ars
            var_underlying = (underlying_today["price"] - underlying_yesterday) / underlying_yesterday
            var_ccl = (ccl_today - ccl_yesterday) / ccl_yesterday
            
            # 6. Crear análisis
            analysis = CEDEARVariationAnalysis(
                symbol=symbol,
                precio_cedear_ayer_ars=cedear_yesterday_ars,
                precio_underlying_ayer_usd=underlying_yesterday,
                ccl_ayer=ccl_yesterday,
                precio_cedear_hoy_ars=cedear_today_ars,
                precio_underlying_hoy_usd=underlying_today["price"],
                ccl_hoy=ccl_today,
                var_cedear=var_cedear,
                var_underlying=var_underlying,
                var_ccl=var_ccl,
                mode=self.mode,
                timestamp=datetime.now().isoformat()
            )
            
            logger.debug(f"[SUCCESS] Análisis completado para {symbol}: var_cedear={var_cedear:.1%}")
            return analysis
            
        except Exception as e:
            logger.error(f"[ERROR] Error analizando variación de {symbol}: {str(e)}")
            return None
    
    async def _get_historical_underlying_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio histórico (ayer) del activo subyacente"""
        
        try:
            # Yahoo Finance eliminado - datos históricos no disponibles
            logger.warning(f"[WARNING]  Datos históricos no disponibles para {symbol} (Yahoo eliminado)")
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo precio histórico de {symbol}: {str(e)}")
            return None
    
    
    async def _get_ccl_prices(self) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precios del CCL (hoy y ayer)"""
        
        try:
            # CCL actual
            ccl_data = await self.dollar_service.get_ccl_rate()
            ccl_today = ccl_data["rate"] if ccl_data else None
            
            # CCL histórico desde BYMA
            ccl_yesterday = await self.byma_integration.get_ccl_rate_historical()
            
            if not ccl_yesterday:
                ccl_yesterday = ccl_today  # Fallback al actual
                logger.debug("[WARNING]  Usando CCL actual como histórico")
            
            logger.debug(f"[CCL] CCL: Hoy=${ccl_today:.0f}, Ayer=${ccl_yesterday:.0f} ARS/USD")
            return ccl_today, ccl_yesterday
            
        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo precios CCL: {str(e)}")
            return None, None
    
    async def analyze_portfolio_variations(self, symbols: List[str]) -> List[CEDEARVariationAnalysis]:
        """
        Analiza variaciones para una lista de símbolos (portfolio completo)
        
        Args:
            symbols: Lista de símbolos de CEDEARs
            
        Returns:
            Lista de análisis de variación
        """
        
        logger.debug(f"[SEARCH] Analizando variaciones para {len(symbols)} símbolos: {symbols}")
        
        # Ejecutar análisis en paralelo
        tasks = [
            self.analyze_single_variation(symbol)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados válidos
        analyses = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"[ERROR] Error analizando variación de {symbol}: {result}")
            elif result is not None:
                analyses.append(result)
        
        logger.info(f"[SUCCESS] Análisis de variaciones completado: {len(analyses)}/{len(symbols)}")
        return analyses
    
    def format_variation_report(self, analyses: List[CEDEARVariationAnalysis]) -> str:
        """Formatea un reporte de variaciones para mostrar al usuario"""
        
        if not analyses:
            return "ℹ️  No hay análisis de variaciones disponibles"
        
        report = "\n[DATA] ANÁLISIS DE VARIACIONES DIARIAS\n"
        report += "=" * 70 + "\n"
        report += f"Modo: {'🔴 TIEMPO REAL (IOL)' if self.mode == 'full' else '🟡 REAL (BYMA)'}\n\n"
        
        # Encabezado de tabla simplificada
        report += "┌─────────┬────────────┬─────────────┬──────────┬─────────────────────┐\n"
        report += "│ Símbolo │ Var. CEDEAR│ Var. Acción │ Var. CCL │ Factor Principal    │\n"
        report += "├─────────┼────────────┼─────────────┼──────────┼─────────────────────┤\n"
        
        for analysis in analyses:
            symbol = analysis.symbol[:7]  # Truncar si es muy largo
            var_cedear = f"{analysis.var_cedear:+.1%}"
            var_underlying = f"{analysis.var_underlying:+.1%}"
            var_ccl = f"{analysis.var_ccl:+.1%}"
            strongest_factor = analysis.get_strongest_factor()
            
            report += f"│ {symbol:<7} │ {var_cedear:>10} │ {var_underlying:>11} │ {var_ccl:>8} │ {strongest_factor:<19} │\n"
        
        report += "└─────────┴────────────┴─────────────┴──────────┴─────────────────────┘\n"
        
        return report
    
