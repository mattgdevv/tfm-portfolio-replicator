"""
Servicio unificado de análisis para todo el sistema
Consolida lógica de precios, arbitraje y variaciones
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

# ❌ ELIMINADO: imports de servicios globales - usar DI  
# from .international_prices import international_price_service
# from .dollar_rate import dollar_service
# from .arbitrage_detector import arbitrage_detector, ArbitrageOpportunity

from .arbitrage_detector import ArbitrageOpportunity
from ..processors.cedeares import CEDEARProcessor
from ..models.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)

class UnifiedAnalysisService:
    """Servicio unificado que maneja todos los análisis de precios y arbitraje"""
    
    def __init__(self, arbitrage_detector, cedear_processor, international_service, config=None):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            arbitrage_detector: Detector de arbitraje configurado (REQUERIDO)
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
            international_service: Servicio de precios internacionales (REQUERIDO)
        """
        if arbitrage_detector is None:
            raise ValueError("arbitrage_detector es requerido - use build_services() para crear instancias")
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
        if international_service is None:
            raise ValueError("international_service es requerido - use build_services() para crear instancias")
            
        self.arbitrage_detector = arbitrage_detector
        self.cedear_processor = cedear_processor
        self.international_service = international_service
        self.config = config  # Almacenar config para usar threshold por defecto
    
    def set_iol_session(self, session):
        """Configura sesión IOL para análisis completo"""
        self.arbitrage_detector.set_iol_session(session)
    
    async def analyze_portfolio(self, portfolio: Portfolio, threshold: float = None) -> Dict[str, Any]:
        """
        Análisis completo de portfolio - precios + arbitraje unificado
        
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
        
        # Análisis de arbitraje unificado
        opportunities = []
        price_data = {}
        sources_used = set()
        
        for symbol in cedear_symbols:
            try:
                # Usar ArbitrageDetector unificado (ya tiene fallback integrado)
                opportunity = await self.arbitrage_detector.detect_single_arbitrage(symbol, threshold)
                
                # Obtener datos de precios para métricas
                underlying_data = await self.international_service.get_stock_price(symbol)
                if underlying_data:
                    price_data[symbol] = {
                        "underlying_price_usd": underlying_data["price"],
                        "source": underlying_data.get("source", "unknown"),
                        "fallback_used": underlying_data.get("fallback_used", False)
                    }
                    sources_used.add(underlying_data.get("source", "unknown"))
                
                if opportunity:
                    opportunities.append(opportunity)
                    logger.info(f"🚨 Arbitraje detectado en {symbol}: {opportunity.difference_percentage:.1%}")
            
            except Exception as e:
                logger.error(f"❌ Error analizando {symbol}: {e}")
                continue
        
        # Generar resumen
        mode = "COMPLETO (IOL)" if self.arbitrage_detector.mode == "full" else "LIMITADO"
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
    
    async def get_portfolio_prices(self, portfolio: Portfolio) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene precios para todas las posiciones del portfolio
        Unifica la lógica de precios para IOL y Excel
        """
        price_results = {}
        
        for position in portfolio.positions:
            if self.cedear_processor.is_cedear(position.symbol):
                try:
                    # Para CEDEARs: usar lógica unificada de ArbitrageDetector
                    # Usar PriceFetcher para obtener precio del CEDEAR
                    cedear_price_ars, _ = await self.arbitrage_detector.price_fetcher.get_cedear_price(position.symbol)
                    
                    # Obtener información del subyacente
                    underlying_data = await self.international_service.get_stock_price(position.symbol)
                    
                    # Calcular precio por acción del CEDEAR (dividir por ratio)
                    accion_usd = None
                    if cedear_price_ars:
                        cedear_info = self.cedear_processor.get_underlying_asset(position.symbol)
                        if cedear_info:
                            ratio = cedear_info.get("ratio", "1:1")
                            conversion_ratio = self.cedear_processor.parse_ratio(ratio)
                            # Obtener CCL aproximado para convertir a USD
                            ccl_rate = 1300.0  # Valor por defecto
                            accion_usd = (cedear_price_ars / ccl_rate) * conversion_ratio
                    
                    if cedear_price_ars and underlying_data:
                        price_results[position.symbol] = {
                            "cedear_price_ars": cedear_price_ars,
                            "action_via_cedear_usd": accion_usd,
                            "underlying_price_usd": underlying_data["price"],
                            "source": underlying_data.get("source", "unknown"),
                            "fallback_used": underlying_data.get("fallback_used", False)
                        }
                
                except Exception as e:
                    logger.debug(f"❌ Error obteniendo precios para {position.symbol}: {e}")
                    continue
        
        return price_results
    
    def format_analysis_summary(self, analysis_result: Dict[str, Any]) -> str:
        """Formatea resumen de análisis de manera consistente"""
        summary = analysis_result["summary"]
        opportunities = analysis_result["arbitrage_opportunities"]
        
        # Header
        mode_emoji = "🔴" if "COMPLETO" in summary["mode"] else "🟡"
        result = f"\n{mode_emoji} Modo {summary['mode']}: Usando precios desde {summary['sources_used']}\n"
        
        # Resultados
        if opportunities:
            result += f"\n🚨 {len(opportunities)} oportunidades de arbitraje detectadas (>{summary['threshold']:.1%}):\n"
            for opp in opportunities:
                result += f"  • {opp.symbol}: {opp.difference_percentage:+.1%} - {opp.recommendation}\n"
        else:
            result += f"\n✅ No se detectaron oportunidades de arbitraje superiores al {summary['threshold']:.1%}\n"
        
        return result
