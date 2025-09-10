"""
Servicio para mostrar y formatear portfolios
"""
import asyncio
import logging
from typing import Optional

from app.models.portfolio import Portfolio
from app.utils.business_days import get_market_status_message


class PortfolioDisplayService:
    """Servicio para procesar y mostrar portfolios con formato de tabla"""
    
    def __init__(self, services, iol_integration, cedear_processor):
        self.services = services
        self.iol_integration = iol_integration
        self.cedear_processor = cedear_processor
    
    async def process_and_show_portfolio(self, portfolio: Portfolio, source: str):
        """Procesa y muestra los resultados del portfolio"""
        print(f"\n📋 Portfolio obtenido desde {source}")
        print(f"📊 Total de posiciones: {len(portfolio.positions)}")
        
        # Contar CEDEARs
        cedeares_count = sum(1 for pos in portfolio.positions if pos.is_cedear)
        print(f"🏦 CEDEARs encontrados: {cedeares_count}")
        
        # Obtener cotización del dólar (CCL). Preferir IOL si hay sesión; sino usar DollarRateService (dolarapi/IOL fallback)
        dollar_rate = await self._get_dollar_rate()
        
        # Mostrar mensaje de mercado cerrado si aplica
        market_message = get_market_status_message("AR")
        if market_message:
            print(f"\n{market_message}")
        
        # Mostrar posiciones en formato tabla
        await self._display_portfolio_table(portfolio, dollar_rate)
        
        return cedeares_count
    
    async def _get_dollar_rate(self) -> float:
        """Obtiene la cotización del dólar CCL"""
        try:
            dollar_rate = None
            # Intentar vía IOL si hay sesión válida
            try:
                dollar_rate = await self.iol_integration.get_dollar_rate()
            except Exception as e_iol:
                print(f"⚠️  No se pudo obtener CCL desde IOL: {e_iol}")
            # Fallback a DollarRateService (usa preferencia y agrega implícito como último)
            if not dollar_rate or dollar_rate <= 0:
                ccl_result = await self.services.dollar_service.get_ccl_rate()
                dollar_rate = (ccl_result.get("rate") if isinstance(ccl_result, dict) else ccl_result) or 1000.0
        except Exception as e:
            print(f"⚠️  No se pudo obtener CCL: {e}")
            dollar_rate = 1000.0
        
        return dollar_rate
    
    async def _display_portfolio_table(self, portfolio: Portfolio, dollar_rate: float):
        """Muestra el portfolio en formato tabla"""
        print("\n📊 PORTFOLIO (ARS)")
        print("┌─────────┬──────────┬─────────────────┬─────────────┬─────────────────┐")
        print("│ Símbolo │ CEDEARs  │ Valor ARS       │ Acciones    │ Valor USD       │")
        print("├─────────┼──────────┼─────────────────┼─────────────┼─────────────────┤")
        
        total_ars = 0
        total_usd = 0
        
        # Silenciar logs informativos durante el render de la tabla
        detector_logger = logging.getLogger("app.services.arbitrage_detector")
        previous_level_detector = detector_logger.level
        detector_logger.setLevel(logging.ERROR)
        dollar_logger = logging.getLogger("app.services.dollar_rate")
        previous_level_dollar = dollar_logger.level
        dollar_logger.setLevel(logging.ERROR)
        
        # Prefetch paralelo de precios CEDEAR (para posiciones sin total_value)
        prefetch_prices = await self._prefetch_missing_prices(portfolio)

        for pos in portfolio.positions:
            if pos.is_cedear and pos.underlying_symbol:
                # Es un CEDEAR
                if pos.total_value is not None:
                    total_value_ars = pos.total_value
                    total_ars += total_value_ars
                    actions = pos.underlying_quantity or 0
                    value_usd = total_value_ars / dollar_rate
                    total_usd += value_usd
                    print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {actions:>10.1f} │ ${value_usd:>14,.2f} │")
                else:
                    # Price no disponible del archivo - usar prefetch o resolver si falta
                    precio_ars = await self._get_position_price(pos, prefetch_prices)
                    
                    if precio_ars and precio_ars > 0:
                        total_value_ars = precio_ars * pos.quantity
                        total_ars += total_value_ars
                        actions = pos.underlying_quantity or 0
                        value_usd = total_value_ars / dollar_rate
                        total_usd += value_usd
                        print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {actions:>10.1f} │ ${value_usd:>14,.2f} │")
                    else:
                        print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${'N/A':>14} │ {'N/A':>10} │ ${'N/A':>14} │")
            else:
                # No es CEDEAR o no tiene underlying_symbol
                if pos.total_value is not None:
                    # 🔧 FIX 2025-01-XX: Manejo correcto de monedas en FCIs
                    # Problema: FCIs en USD mostraban valores incorrectos porque se asumía
                    # que IOL devolvía todos los valores en ARS, causando error de ~2000x
                    #
                    # Solución: Lógica condicional basada en pos.currency
                    # - FCIs en USD: IOL devuelve en USD → multiplicar por dollar_rate
                    # - Otros activos: IOL devuelve en ARS → dividir por dollar_rate
                    if pos.currency == "USD" and (pos.is_fci_usd or pos.is_fci_ars):
                        # FCI en USD: IOL devuelve valor en USD, convertir a ARS
                        total_value_usd = pos.total_value
                        total_value_ars = total_value_usd * dollar_rate
                        value_usd = total_value_usd  # Ya está en USD
                    else:
                        # CEDEAR u otros activos: IOL devuelve valor en ARS
                        total_value_ars = pos.total_value
                        value_usd = total_value_ars / dollar_rate

                    total_ars += total_value_ars
                    total_usd += value_usd
                    print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {'-':>10} │ ${value_usd:>14,.2f} │")
                else:
                    print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${'N/A':>14} │ {'-':>10} │ ${'N/A':>14} │")
        
        # Restaurar niveles de logging
        detector_logger.setLevel(previous_level_detector)
        dollar_logger.setLevel(previous_level_dollar)
        
        # Mostrar totales
        print("├─────────┼──────────┼─────────────────┼─────────────┼─────────────────┤")
        print(f"│ {'TOTAL':<7} │ {'':<8} │ ${total_ars:>14,.0f} │ {'':<10} │ ${total_usd:>14,.2f} │")
        print("└─────────┴──────────┴─────────────────┴─────────────┴─────────────────┘")
        print(f"💱 Cotización USD: ${dollar_rate:,.2f} ARS")
    
    async def _prefetch_missing_prices(self, portfolio: Portfolio) -> dict:
        """Prefetch paralelo de precios CEDEAR para posiciones sin total_value"""
        missing_symbols = []
        for pos in portfolio.positions:
            if pos.is_cedear and pos.underlying_symbol and pos.total_value is None:
                if pos.symbol not in missing_symbols:
                    missing_symbols.append(pos.symbol)
        
        prefetch_prices: dict[str, float] = {}
        if missing_symbols:
            async def fetch_symbol(symbol: str):
                try:
                    price_ars, _ = await self.services.price_fetcher.get_cedear_price(symbol)
                    return symbol, price_ars
                except Exception:
                    return symbol, None
            results = await asyncio.gather(*(fetch_symbol(s) for s in missing_symbols))
            prefetch_prices = {s: p for s, p in results if p}
        
        return prefetch_prices
    
    async def _get_position_price(self, pos, prefetch_prices: dict) -> Optional[float]:
        """Obtiene el precio de una posición usando diferentes fuentes"""
        # Usar precio prefetch si está disponible
        precio_ars = prefetch_prices.get(pos.symbol)
        if precio_ars is not None:
            return precio_ars
        
        # Intentar obtener precio directamente
        try:
            precio_ars, _ = await self.services.price_fetcher.get_cedear_price(pos.symbol)
            if precio_ars is not None:
                return precio_ars
        except Exception:
            pass
        
        # Fallback: calcular precio usando Finnhub + CCL cuando BYMA no tiene el CEDEAR
        if pos.is_cedear:
            try:
                # Obtener precio subyacente en USD
                underlying_data = await self.services.international_service.get_stock_price(pos.symbol)
                
                if underlying_data:
                    underlying_price_usd = underlying_data["price"]
                    ccl_data = await self.services.dollar_service.get_ccl_rate()
                    ccl_rate = ccl_data["rate"] if ccl_data else 1300.0
                    
                    # Obtener ratio de conversión
                    cedear_info = self.cedear_processor.get_cedear_info(pos.symbol)
                    ratio = 1.0
                    if cedear_info:
                        ratio_str = cedear_info.get("ratio", "1:1")
                        try:
                            if ":" in ratio_str:
                                cedear_shares, underlying_shares = ratio_str.split(":")
                                ratio = float(underlying_shares) / float(cedear_shares)
                        except (ValueError, ZeroDivisionError):
                            ratio = 1.0
                    
                    # Calcular precio CEDEAR en ARS
                    precio_ars = (underlying_price_usd * ratio) * ccl_rate
                    return precio_ars
            except Exception:
                pass
        
        return None
