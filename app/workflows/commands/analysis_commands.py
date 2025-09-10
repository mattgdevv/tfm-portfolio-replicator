"""
ETL Analysis Commands
Comandos para análisis de datos y transformaciones (arbitraje, cache management)
"""

from app.core.services import Services
from app.models.portfolio import Portfolio, Position


class AnalysisCommands:
    """Comandos de análisis y transformación de datos para el pipeline ETL"""
    
    def __init__(self, services: Services, iol_integration):
        """
        Constructor con dependency injection
        
        Args:
            services: Container de servicios DI
            iol_integration: Integración IOL para análisis completo
        """
        self.services = services
        self.iol_integration = iol_integration
    
    async def analyze_portfolio(self, portfolio: Portfolio, from_iol: bool = False) -> dict:
        """
        Analiza un portfolio para detectar oportunidades de arbitraje
        
        Args:
            portfolio: Portfolio a analizar
            from_iol: Si el portfolio viene de IOL (para configuración automática)
            
        Returns:
            dict: Resultado del análisis de arbitraje
        """
        threshold_pct = self.services.config.arbitrage_threshold * 100
        print(f"\n🔍 Analizando oportunidades de arbitraje (threshold: {threshold_pct:.1f}%)...")
        
        # Configurar sesión IOL
        iol_session = None
        if hasattr(self.iol_integration, 'session') and self.iol_integration.session:
            if from_iol:
                # Si venimos de la opción 1 (IOL), usar automáticamente IOL
                iol_session = self.iol_integration.session
                print("🔴 Modo: COMPLETO (IOL + Finnhub)")
            else:
                # Si venimos de otra opción, preguntar
                print("🔑 Credenciales IOL detectadas.")
                use_iol = input("¿Usar IOL para análisis más preciso? (s/n): ").strip().lower()
                if use_iol == 's':
                    iol_session = self.iol_integration.session
                    print("🔴 Modo: COMPLETO (IOL + Finnhub)")
                else:
                    print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
        else:
            print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
        
        # Configurar el servicio unificado
        # Configurar sesión IOL en todos los servicios que la necesitan
        self.services.unified_analysis.set_iol_session(iol_session)
        self.services.variation_analyzer.set_iol_session(iol_session)
        self.services.price_fetcher.set_iol_session(iol_session)
        
        # Realizar análisis
        analysis_result = await self.services.unified_analysis.analyze_portfolio(
            portfolio, 
            threshold=self.services.config.arbitrage_threshold
        )
        
        # Mostrar resultados
        summary_text = self.services.unified_analysis.format_analysis_summary(analysis_result)
        print(summary_text)
        
        # Mostrar alertas detalladas si hay oportunidades
        opportunities = analysis_result["arbitrage_opportunities"]
        if opportunities:
            print("\n" + "="*60)
            for opp in opportunities:
                alert_text = self.services.arbitrage_detector.format_alert(opp)
                print(alert_text)
            print("="*60)
        
        return analysis_result
    
    async def analyze_specific_cedeares(self) -> dict:
        """
        Análisis de arbitraje para CEDEARs específicos seleccionados por el usuario
        
        Returns:
            dict: Resultado del análisis de arbitraje
        """
        print("\n📊 Análisis de Arbitraje de CEDEARs")
        print("=" * 50)
        print("Esta función analiza oportunidades de arbitraje para CEDEARs específicos")
        print("que tu eliges, usando el mismo sistema que el análisis de portfolio.")
        print()
        
        # Solicitar símbolos
        symbols_input = input("🔍 Introduce símbolos de CEDEARs (separados por comas): ").strip()
        
        if not symbols_input:
            print("❌ No se introdujeron símbolos")
            return None
        
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
        if not symbols:
            print("❌ No se encontraron símbolos válidos")
            return None
            
        print(f"\n🔍 Analizando {len(symbols)} símbolos: {symbols}")
        
        # Crear portfolio temporal
        temp_positions = []
        for symbol in symbols:
            if self.services.cedear_processor.is_cedear(symbol):
                position = Position(
                    symbol=symbol,
                    quantity=1,
                    price=None,
                    currency="ARS",
                    total_value=None
                )
                temp_positions.append(position)
            else:
                print(f"⚠️  {symbol} no es un CEDEAR conocido, saltando...")
        
        if not temp_positions:
            print("❌ No se encontraron CEDEARs válidos")
            return None
            
        temp_portfolio = Portfolio(positions=temp_positions, source="Manual")
        
        # Análisis usando sistema unificado
        analysis_result = await self.services.unified_analysis.analyze_portfolio(
            temp_portfolio, 
            threshold=self.services.config.arbitrage_threshold
        )
        
        # Mostrar resultados
        summary_text = self.services.unified_analysis.format_analysis_summary(analysis_result)
        print(summary_text)
        
        return analysis_result
    
    async def refresh_ccl_cache(self) -> bool:
        """
        Invalida el cache de CCL y fuerza un refetch
        
        Returns:
            bool: True si se refrescó exitosamente
        """
        print("\n🔄 Refrescando CCL...")
        try:
            # Limpiar cache conocido
            for key in ["ccl:dolarapi_ccl", "ccl:ccl_al30"]:
                self.services.dollar_service._cache.pop(key, None)
            
            # Obtener nuevo valor
            result = await self.services.dollar_service.get_ccl_rate()
            
            if result:
                print(f"✅ CCL actualizado: ${result['rate']:.2f} (fuente: {result.get('source_name', result.get('source'))})")
                return True
            else:
                print("❌ No se pudo refrescar CCL")
                return False
        except Exception as e:
            print(f"❌ Error refrescando CCL: {e}")
            return False
