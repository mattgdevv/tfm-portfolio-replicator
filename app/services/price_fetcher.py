"""
PriceFetcher - Servicio unificado para obtención de precios de CEDEARs

Elimina duplicación entre ArbitrageDetector y VariationAnalyzer.
Proporciona una interfaz unificada para obtener precios de diferentes fuentes.
"""

import asyncio
from typing import Optional, Tuple
import logging

from ..processors.cedeares import CEDEARProcessor
from ..utils.business_days import get_market_status_message

logger = logging.getLogger(__name__)


class PriceFetcher:
    """
    Servicio unificado para obtención de precios de CEDEARs.

    Elimina la duplicación entre ArbitrageDetector y VariationAnalyzer
    proporcionando una interfaz común para obtener precios de CEDEARs
    desde diferentes fuentes (IOL, BYMA, cálculos teóricos).
    """

    def __init__(self, cedear_processor: CEDEARProcessor, iol_session=None, byma_integration=None, dollar_service=None, config=None):
        """
        Constructor con dependencias.

        Args:
            cedear_processor: Procesador de CEDEARs
            iol_session: Sesión IOL opcional para modo completo
            byma_integration: Integración BYMA para datos históricos
            dollar_service: Servicio de dólar para obtener CCL
            config: Configuración del sistema
        """
        self.cedear_processor = cedear_processor
        self.iol_session = iol_session
        self.byma_integration = byma_integration
        self.dollar_service = dollar_service
        self.config = config
        self.timeout = getattr(config, 'request_timeout', 10) if config else 10
        self.mode = "full" if iol_session else "limited"

    def set_iol_session(self, session):
        """Establece sesión IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
        # Log removido para reducir ruido

    def _get_cedear_conversion_info(self, symbol: str) -> Tuple[str, float]:
        """
        Helper method para obtener información de conversión del CEDEAR.

        Args:
            symbol: Símbolo del CEDEAR

        Returns:
            Tuple: (ratio_str, conversion_ratio_float)
        """
        cedear_info = self.cedear_processor.get_underlying_asset(symbol)
        if not cedear_info:
            raise ValueError(f"No se encontró información del CEDEAR {symbol}")

        ratio = cedear_info.get("ratio")
        if not ratio:
            raise ValueError(f"Ratio no disponible para CEDEAR {symbol} - datos incompletos")
        
        conversion_ratio = self.cedear_processor.parse_ratio(ratio)
        return ratio, conversion_ratio

    async def get_cedear_price(self, symbol: str, include_historical: bool = False) -> Tuple[Optional[float], Optional[float]]:
        """
        Método unificado para obtener precios del CEDEAR.

        Reemplaza _get_cedear_price_usd y _get_cedear_prices.

        Args:
            symbol: Símbolo del CEDEAR
            include_historical: Si True, incluye precio histórico (ayer)

        Returns:
            Tuple: (precio_hoy_ars, precio_ayer_ars) o (precio_hoy_ars, None)
        """
        if self.mode == "full" and self.iol_session:
            return await self._get_iol_cedear_price(symbol, include_historical)
        else:
            return await self._get_byma_cedear_price(symbol, include_historical)

    async def _get_iol_cedear_price(self, symbol: str, include_historical: bool = False) -> Tuple[Optional[float], Optional[float]]:
        """
        Obtiene precios del CEDEAR desde IOL API.

        Args:
            symbol: Símbolo del CEDEAR
            include_historical: Si incluir precio histórico

        Returns:
            Tuple: (precio_hoy_ars, precio_ayer_ars) o (precio_hoy_ars, None)
        """
        try:
            # Obtener precio actual desde IOL
            url_today = f"https://api.invertironline.com/api/v2/bcba/Titulos/{symbol}/Cotizacion"
            response = self.iol_session.get(url_today, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            precio_hoy = data.get("ultimoPrecio")

            if not precio_hoy or precio_hoy <= 0:
                raise ValueError(f"Precio IOL inválido para {symbol}: {precio_hoy}")

            if not include_historical:
                return precio_hoy, None

            # Para precio de ayer, usar precio de cierre anterior si está disponible
            precio_ayer = data.get("cierreAnterior") or data.get("apertura")

            if not precio_ayer:
                logger.warning(f"[WARNING] No hay precio histórico IOL para {symbol}")
                return precio_hoy, None

            logger.debug(f"💰 IOL {symbol}: Hoy=${precio_hoy:.0f}, Ayer=${precio_ayer:.0f} ARS")
            return float(precio_hoy), float(precio_ayer)

        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo precios IOL para {symbol}: {str(e)}")
            return None, None

    async def _get_byma_cedear_price(self, symbol: str, include_historical: bool = False) -> Tuple[Optional[float], Optional[float]]:
        """
        Obtiene precios del CEDEAR desde BYMA API.

        Args:
            symbol: Símbolo del CEDEAR
            include_historical: Si incluir precio histórico

        Returns:
            Tuple: (precio_hoy_ars, precio_ayer_ars) o (precio_hoy_ars, None)
        """
        try:
            # Obtener información del CEDEAR
            _, conversion_ratio = self._get_cedear_conversion_info(symbol)

            # Obtener datos actuales de CEDEARs desde BYMA
            cedeares_data = await self.byma_integration._get_cedeares_data()

            if not cedeares_data:
                # Si no hay datos de BYMA (día no hábil o API down), intentar cache
                market_message = get_market_status_message("AR")
                if market_message:
                    logger.debug(f"🏦 {market_message[:50]}... - No hay datos BYMA para {symbol}")
                else:
                    logger.error(f"[ERROR] No se pudieron obtener datos de CEDEARs desde BYMA")
                return None, None

            # Buscar el CEDEAR específico
            cedear_data = None
            for cedear in cedeares_data:
                if cedear.get('symbol') == symbol:
                    cedear_data = cedear
                    break

            if not cedear_data:
                logger.warning(f"[WARNING] CEDEAR {symbol} no encontrado en datos BYMA")
                return None, None

            # Extraer precios
            precio_hoy = cedear_data.get('trade') or cedear_data.get('closingPrice')

            if not precio_hoy or precio_hoy <= 0:
                logger.warning(f"[WARNING] Precio BYMA inválido para {symbol}: {precio_hoy}")
                return None, None

            if not include_historical:
                return precio_hoy, None

            # Para precio histórico, usar el mismo precio (aproximación)
            # En un futuro se podría implementar consulta histórica real
            logger.debug(f"🏦 BYMA {symbol}: Precio=${precio_hoy:.0f} ARS")
            return precio_hoy, precio_hoy  # Por ahora devolvemos el mismo precio

        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo precios BYMA para {symbol}: {str(e)}")
            return None, None

    async def get_cedear_price_with_action_usd(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Obtiene precio del CEDEAR y calcula precio por acción en USD.
        
        Reemplaza el método _get_cedear_price_usd que fue eliminado.

        Args:
            symbol: Símbolo del CEDEAR

        Returns:
            Tuple: (cedear_price_ars, accion_via_cedear_usd)
        """
        try:
            # Obtener precio del CEDEAR
            cedear_price_ars, _ = await self.get_cedear_price(symbol)
            if not cedear_price_ars:
                return None, None

            # Obtener información de conversión
            _, conversion_ratio = self._get_cedear_conversion_info(symbol)

            # Obtener CCL rate
            ccl_rate = await self._get_ccl_rate_safe()
            if not ccl_rate:
                logger.error(f"[ERROR] No se pudo obtener CCL para calcular precio por acción USD de {symbol}")
                return None, None

            # Calcular precio por acción en USD
            # CEDEAR price ARS / CCL rate = CEDEAR price USD
            # CEDEAR price USD * conversion_ratio = action price USD
            accion_via_cedear_usd = (cedear_price_ars / ccl_rate) * conversion_ratio

            logger.debug(f"💰 {symbol}: CEDEAR=${cedear_price_ars:.0f} ARS → Acción=${accion_via_cedear_usd:.2f} USD")
            return cedear_price_ars, accion_via_cedear_usd

        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo precio con acción USD para {symbol}: {str(e)}")
            return None, None

    async def get_theoretical_cedear_price(self, symbol: str, underlying_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calcula precio teórico del CEDEAR y precio de acción vía CEDEARs basado en precio del subyacente.

        Args:
            symbol: Símbolo del CEDEAR
            underlying_price: Precio del activo subyacente en USD

        Returns:
            Tuple: (cedear_price_ars, accion_via_cedear_usd) - Compatible con get_cedear_price_with_action_usd
        """
        try:
            # Obtener ratio de conversión
            _, conversion_ratio = self._get_cedear_conversion_info(symbol)

            # Calcular precio teórico de 1 CEDEAR individual
            precio_cedear_individual_usd = underlying_price / conversion_ratio

            # Obtener CCL para convertir a ARS
            ccl_rate = await self._get_ccl_rate_safe()
            if not ccl_rate:
                logger.error(f"[ERROR] No se pudo obtener CCL para calcular precio teórico de {symbol}")
                return None, None
            
            # Precio de 1 CEDEAR en ARS
            precio_cedear_individual_ars = precio_cedear_individual_usd * ccl_rate
            
            # Precio de 1 acción vía CEDEARs (para comparar con subyacente)
            # Esto debe ser igual al underlying_price si no hay arbitraje
            accion_via_cedear_teorico_usd = precio_cedear_individual_usd * conversion_ratio

            logger.debug(f"🔮 Teórico {symbol}: 1 CEDEAR=${precio_cedear_individual_ars:.0f} ARS, 1 Acción vía CEDEARs=${accion_via_cedear_teorico_usd:.2f} USD")
            return precio_cedear_individual_ars, accion_via_cedear_teorico_usd

        except Exception as e:
            logger.error(f"[ERROR] Error calculando precio teórico para {symbol}: {str(e)}")
            return None, None

    async def _get_ccl_rate_safe(self) -> Optional[float]:
        """
        Helper method para obtener CCL rate de forma segura.
        
        Returns:
            float: CCL rate o None si no disponible (no usa fallback hardcodeado)
        """
        if not self.dollar_service:
            logger.warning("[WARNING] DollarService no disponible para obtener CCL")
            return None
            
        ccl_data = await self.dollar_service.get_ccl_rate()
        if ccl_data and ccl_data.get("rate"):
            return ccl_data["rate"]
        else:
            logger.warning("[WARNING] No se pudo obtener CCL de ninguna fuente")
            return None
