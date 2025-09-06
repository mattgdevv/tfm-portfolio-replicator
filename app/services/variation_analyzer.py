"""
Analizador de Variaciones de CEDEARs
Analiza si los CEDEARs se mueven más o menos de lo esperado vs sus subyacentes
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

# ❌ ELIMINADO: import de servicio global - migrar a DI cuando sea necesario
# from .international_prices import international_price_service
# ❌ ELIMINADO: imports de servicios globales - migrar a DI cuando sea necesario  
# from .dollar_rate import dollar_service
# from .byma_historical import byma_historical_service
from ..processors.cedeares import CEDEARProcessor

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
    
    def __init__(self, cedear_processor, international_service, dollar_service, byma_service, iol_session=None):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
            international_service: Servicio de precios internacionales (REQUERIDO)
            dollar_service: Servicio de cotización dólar (REQUERIDO)
            byma_service: Servicio BYMA histórico (REQUERIDO)
            iol_session: Sesión IOL para modo completo (opcional)
        """
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
        if international_service is None:
            raise ValueError("international_service es requerido - use build_services() para crear instancias")
        if dollar_service is None:
            raise ValueError("dollar_service es requerido - use build_services() para crear instancias")
        if byma_service is None:
            raise ValueError("byma_service es requerido - use build_services() para crear instancias")
            
        self.iol_session = iol_session
        self.cedear_processor = cedear_processor
        self.international_service = international_service
        self.dollar_service = dollar_service
        self.byma_service = byma_service
        self.mode = "full" if iol_session else "limited"
        
    def set_iol_session(self, session):
        """Establece la sesión de IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
        logger.info(f"🔄 VariationAnalyzer modo cambiado a: {self.mode}")
    
    async def analyze_single_variation(self, symbol: str) -> Optional[CEDEARVariationAnalysis]:
        """
        Analiza la variación de un CEDEAR específico
        
        Args:
            symbol: Símbolo del CEDEAR (ej: "TSLA")
            
        Returns:
            CEDEARVariationAnalysis o None si hay error
        """
        
        logger.debug(f"🔍 Analizando variación para {symbol} (modo: {self.mode})")
        
        try:
            # 1. Obtener precios actuales del subyacente
            underlying_today = await self.international_service.get_stock_price(symbol)
            if not underlying_today:
                logger.error(f"❌ No se pudo obtener precio actual de {symbol}")
                return None
            
            # 2. Obtener precios históricos del subyacente (ayer)
            underlying_yesterday = await self._get_historical_underlying_price(symbol)
            if not underlying_yesterday:
                logger.error(f"❌ No se pudo obtener precio histórico de {symbol}")
                return None
            
            # 3. Obtener precios del CEDEAR (hoy y ayer)
            cedear_today_ars, cedear_yesterday_ars = await self._get_cedear_prices(symbol)
            if not cedear_today_ars or not cedear_yesterday_ars:
                logger.error(f"❌ No se pudo obtener precios CEDEAR para {symbol}")
                return None
            
            # 4. Obtener CCL (hoy y ayer)
            ccl_today, ccl_yesterday = await self._get_ccl_prices()
            if not ccl_today or not ccl_yesterday:
                logger.error(f"❌ No se pudo obtener precios CCL")
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
            
            logger.debug(f"✅ Análisis completado para {symbol}: var_cedear={var_cedear:.1%}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analizando variación de {symbol}: {str(e)}")
            return None
    
    async def _get_historical_underlying_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio histórico (ayer) del activo subyacente"""
        
        try:
            # Yahoo Finance eliminado - datos históricos no disponibles
            logger.warning(f"⚠️  Datos históricos no disponibles para {symbol} (Yahoo eliminado)")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio histórico de {symbol}: {str(e)}")
            return None
    
    async def _get_cedear_prices(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precios del CEDEAR (hoy y ayer)"""
        
        if self.mode == "full" and self.iol_session:
            return await self._get_iol_cedear_prices(symbol)
        else:
            return await self._get_byma_real_cedear_prices(symbol)
    
    async def _get_iol_cedear_prices(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precios del CEDEAR desde IOL (actual + histórico)"""
        
        try:
            # Precio actual desde IOL
            url_today = f"https://api.invertironline.com/api/v2/bcba/Titulos/{symbol}/Cotizacion"
            response = self.iol_session.get(url_today, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            precio_hoy = data.get("ultimoPrecio")
            
            if not precio_hoy or precio_hoy <= 0:
                raise ValueError(f"Precio IOL inválido para {symbol}: {precio_hoy}")
            
            # Para precio de ayer, podríamos usar:
            # 1. API histórica de IOL (si existe)
            # 2. Precio de cierre anterior del mismo endpoint
            # 3. Fallback a cálculo teórico
            
            # Por ahora usar el precio de cierre anterior si está disponible
            precio_ayer = data.get("cierreAnterior") or data.get("apertura")
            
            if not precio_ayer:
                # Fallback: calcular teórico para ayer
                logger.warning(f"⚠️  No hay precio histórico IOL para {symbol}, usando teórico")
                _, precio_ayer = await self._get_theoretical_cedear_prices(symbol)
            
            logger.debug(f"💰 IOL {symbol}: Hoy=${precio_hoy:.0f}, Ayer=${precio_ayer:.0f} ARS")
            return float(precio_hoy), float(precio_ayer)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precios IOL para {symbol}: {str(e)}")
            return None, None
    
    async def _get_byma_real_cedear_prices(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precios REALES del CEDEAR desde BYMA (hoy y ayer)"""
        
        try:
            # Obtener datos actuales de CEDEARs desde BYMA
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
            
            # Extraer precios reales
            precio_hoy = cedear_data.get('trade') or cedear_data.get('closingPrice')
            precio_ayer = cedear_data.get('previousClosingPrice')
            
            if not precio_hoy or precio_hoy <= 0:
                logger.warning(f"⚠️  Precio actual inválido para {symbol}: {precio_hoy}")
                return None, None
                
            if not precio_ayer or precio_ayer <= 0:
                logger.warning(f"⚠️  Precio anterior inválido para {symbol}: {precio_ayer}")
                return None, None
            
            logger.debug(f"📈 BYMA REAL {symbol}: Hoy=${precio_hoy:.0f}, Ayer=${precio_ayer:.0f} ARS")
            return float(precio_hoy), float(precio_ayer)
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precios reales BYMA para {symbol}: {str(e)}")
            return None, None
    
    async def _get_ccl_prices(self) -> tuple[Optional[float], Optional[float]]:
        """Obtiene precios del CCL (hoy y ayer)"""
        
        try:
            # CCL actual
            ccl_data = await self.dollar_service.get_ccl_rate()
            ccl_today = ccl_data["rate"] if ccl_data else None
            
            # CCL histórico desde BYMA
            ccl_yesterday = await self.byma_service.get_ccl_rate_historical()
            
            if not ccl_yesterday:
                ccl_yesterday = ccl_today  # Fallback al actual
                logger.debug("⚠️  Usando CCL actual como histórico")
            
            logger.debug(f"💱 CCL: Hoy=${ccl_today:.0f}, Ayer=${ccl_yesterday:.0f} ARS/USD")
            return ccl_today, ccl_yesterday
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precios CCL: {str(e)}")
            return None, None
    
    async def analyze_portfolio_variations(self, symbols: List[str]) -> List[CEDEARVariationAnalysis]:
        """
        Analiza variaciones para una lista de símbolos (portfolio completo)
        
        Args:
            symbols: Lista de símbolos de CEDEARs
            
        Returns:
            Lista de análisis de variación
        """
        
        logger.debug(f"🔍 Analizando variaciones para {len(symbols)} símbolos: {symbols}")
        
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
                logger.error(f"❌ Error analizando variación de {symbol}: {result}")
            elif result is not None:
                analyses.append(result)
        
        logger.info(f"✅ Análisis de variaciones completado: {len(analyses)}/{len(symbols)}")
        return analyses
    
    def format_variation_report(self, analyses: List[CEDEARVariationAnalysis]) -> str:
        """Formatea un reporte de variaciones para mostrar al usuario"""
        
        if not analyses:
            return "ℹ️  No hay análisis de variaciones disponibles"
        
        report = "\n📊 ANÁLISIS DE VARIACIONES DIARIAS\n"
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
    
    def format_detailed_analysis(self, analysis: CEDEARVariationAnalysis) -> str:
        """Formatea un análisis detallado para un CEDEAR específico"""
        
        report = f"\n📈 ANÁLISIS DETALLADO - {analysis.symbol}\n"
        report += "=" * 50 + "\n"
        
        report += f"🕒 Precios:\n"
        report += f"   Subyacente: ${analysis.precio_underlying_ayer_usd:.2f} → ${analysis.precio_underlying_hoy_usd:.2f} USD\n"
        report += f"   CEDEAR:     ${analysis.precio_cedear_ayer_ars:.0f} → ${analysis.precio_cedear_hoy_ars:.0f} ARS\n"
        report += f"   CCL:        ${analysis.ccl_ayer:.0f} → ${analysis.ccl_hoy:.0f} ARS/USD\n\n"
        
        report += f"📊 Variaciones:\n"
        report += f"   CEDEAR Local:      {analysis.var_cedear:+.2%}\n"
        report += f"   Subyacente:        {analysis.var_underlying:+.2%}\n"
        report += f"   CCL:               {analysis.var_ccl:+.2%}\n\n"
        
        report += f"🔍 Factor principal: {analysis.get_strongest_factor()}\n"
        
        return report

# ❌ ELIMINADO: instancia global - usar build_services() para DI
# variation_analyzer = VariationAnalyzer()  # DEPRECATED - use build_services()