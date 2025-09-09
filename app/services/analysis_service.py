"""
Servicio para análisis y testing de portfolios
"""
from getpass import getpass
from pathlib import Path
import json
from typing import Optional

from app.models.portfolio import Portfolio, Position


class AnalysisService:
    """Servicio para análisis de variaciones y testing"""
    
    def __init__(self, services, cedear_processor, iol_integration):
        self.services = services
        self.cedear_processor = cedear_processor
        self.iol_integration = iol_integration
    
    async def test_arbitrage_analysis(self):
        """Análisis de arbitraje para CEDEARs individuales"""
        print("\n📊 Análisis de Arbitraje de CEDEARs")
        print("=" * 50)
        print("Esta función analiza oportunidades de arbitraje para CEDEARs específicos")
        print("que tu eliges, usando el mismo sistema que el análisis de portfolio.")
        print()
        
        # Preguntar símbolos para analizar
        print("📝 Introduce los símbolos de CEDEARs a analizar")
        print("💡 Ejemplos: TSLA, AAPL, GOOGL, MSFT, AMZN")
        print("   (separados por comas)")
        print()
        
        symbols_input = input("🔍 CEDEARs a analizar: ").strip()
        
        if not symbols_input:
            print("❌ No se introdujeron símbolos")
            return
        
        # Procesar símbolos
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
        
        if not symbols:
            print("❌ No se encontraron símbolos válidos")
            return
        
        print(f"\n🔍 Analizando {len(symbols)} símbolos: {symbols}")
        
        # Preguntar si quiere usar IOL
        use_iol = input("\n¿Usar datos de IOL para mayor precisión? (s/n): ").strip().lower()
        
        iol_session = None
        if use_iol == 's':
            try:
                # Solicitar credenciales IOL
                print("\n🔐 Autenticación IOL requerida...")
                username = input("Usuario IOL: ").strip()
                password = getpass("Contraseña IOL: ")
                
                if username and password:
                    print("🔐 Autenticando con IOL...")
                    await self.iol_integration.authenticate(username, password)
                    iol_session = self.iol_integration.session
                    print("✅ Autenticado correctamente con IOL")
                else:
                    print("⚠️  Credenciales no proporcionadas, usando modo limitado")
                    
            except Exception as e:
                print(f"❌ Error de autenticación IOL: {e}")
                print("⚠️  Continuando en modo limitado")
        
        try:
            # Configurar el servicio unificado
            self.services.unified_analysis.set_iol_session(iol_session)
            if iol_session:
                print("🔴 Modo: COMPLETO (IOL + Finnhub)")
            else:
                print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
            
            # Crear un portfolio temporal con los símbolos solicitados
            temp_positions = []
            for symbol in symbols:
                # Verificar que sea CEDEAR
                if self.cedear_processor.is_cedear(symbol):
                    position = Position(
                        symbol=symbol,
                        quantity=1,  # Cantidad dummy para análisis
                        price=None,
                        currency="ARS",
                        total_value=None
                    )
                    temp_positions.append(position)
                else:
                    print(f"⚠️  {symbol} no es un CEDEAR conocido, saltando...")
            
            if not temp_positions:
                print("❌ No se encontraron CEDEARs válidos")
                return
            
            temp_portfolio = Portfolio(positions=temp_positions, source="Manual")
            
            # Realizar análisis unificado
            print(f"\n🔍 Analizando arbitraje para {len(temp_positions)} CEDEARs...")
            analysis_result = await self.services.unified_analysis.analyze_portfolio(temp_portfolio, threshold=self.services.config.arbitrage_threshold)
            
            # Mostrar resultados
            summary_text = self.services.unified_analysis.format_analysis_summary(analysis_result)
            print(summary_text)
            
            # Mostrar detalles de precios obtenidos
            price_data = analysis_result.get("price_data", {})
            if price_data:
                print(f"\n📊 Precios obtenidos:")
                for symbol, data in price_data.items():
                    source = data.get("source", "unknown")
                    price = data.get("underlying_price_usd", 0)
                    fallback = " (fallback)" if data.get("fallback_used") else ""
                    print(f"  • {symbol}: ${price:.2f} USD desde {source.upper()}{fallback}")
            
            # Mostrar alertas detalladas si hay oportunidades
            opportunities = analysis_result["arbitrage_opportunities"]
            if opportunities:
                print("\n" + "="*60)
                for opp in opportunities:
                    alert_text = self.services.arbitrage_detector.format_alert(opp)
                    print(alert_text)
                print("="*60)

                
        except Exception as e:
            print(f"❌ Error en análisis de arbitraje: {e}")
            import traceback
            traceback.print_exc()

    async def refresh_ccl_cache(self):
        """Invalida el cache de CCL y fuerza un refetch de la fuente preferida."""
        print("\n🔄 Refrescando CCL...")
        try:
            # Limpiar entradas conocidas del cache
            for key in ["ccl:dolarapi_ccl", "ccl:ccl_al30"]:
                self.services.dollar_service._cache.pop(key, None)
            # Traer nuevamente usando la preferencia
            from app.config import settings
            result = await self.services.dollar_service.get_ccl_rate(settings.PREFERRED_CCL_SOURCE)
            if result:
                print(f"✅ CCL actualizado: ${result['rate']:.2f} (fuente: {result.get('source_name', result.get('source'))})")
            else:
                print("❌ No se pudo refrescar CCL")
        except Exception as e:
            print(f"❌ Error refrescando CCL: {e}")
