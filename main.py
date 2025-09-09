#!/usr/bin/env python3
"""
Portfolio Replicator MVP
Programa principal para procesar portafolios y convertir CEDEARs
"""

import asyncio
import logging
from getpass import getpass
from pathlib import Path
from dotenv import load_dotenv

import json
import urllib3
from datetime import datetime

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging silencioso ANTES de importar otros módulos
from app.utils.logging_config import setup_quiet_logging
setup_quiet_logging()

from app.integrations.iol import IOLIntegration
from app.processors.file_processor import PortfolioProcessor
from app.processors.cedeares import CEDEARProcessor
from app.models.portfolio import Portfolio, ConvertedPortfolio
from app.config import settings
# ❌ ELIMINADO: imports de servicios globales - usar DI exclusivamente
# from app.services.dollar_rate import dollar_service
# from app.services.arbitrage_detector import arbitrage_detector  
# from app.services.unified_analysis import unified_analysis
from app.core.config import Config
from app.core.services import build_services, Services
from app.utils.business_days import get_market_status_message

class PortfolioReplicator:
    def __init__(self, services: Services):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            services: Servicios construidos con DI (REQUERIDO - usar build_services())
        """
        if services is None:
            raise ValueError("services es requerido - usar build_services() para crear instancias")
            
        print("✅ [PortfolioReplicator] Usando dependency injection estricta.")
        self.services = services
        # IOLIntegration ahora usa DI estricto
        self.iol_integration = IOLIntegration(
            dollar_service=services.dollar_service,
            cedear_processor=services.cedear_processor
        )
        # PortfolioProcessor ahora viene del container DI
        self.portfolio_processor = services.portfolio_processor
        self.cedear_processor = services.cedear_processor
        self.byma_file = Path("byma_cedeares.json")
        self.byma_url = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/cedears"
        self.byma_payload = {
            "excludeZeroPxAndQty": True,
            "T1": True,
            "T0": False,
            "Content-Type": "application/json, text/plain"
        }
        self.byma_headers = {"Content-Type": "application/json"}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # Cargar preferencia local (si existe)
        self.services.config_service.load_local_preferences()
        # Aplicar TTL de cache CEDEAR desde prefs si existe
        try:
            prefs = self.services.config_service.read_prefs()
            ttl = prefs.get('CEDEAR_CACHE_TTL_SECONDS')
            if ttl is not None:
                self.services.arbitrage_detector.set_cedear_cache_ttl(int(ttl))
        except Exception:
            pass
    
    async def run(self):
        """Ejecuta el programa principal"""
        print("🚀 Portfolio Replicator MVP")
        print("=" * 40)
        
        while True:
            print("\n¿Qué quieres hacer?")
            print("1. Obtener portfolio desde IOL")
            print("2. Cargar portfolio desde archivo Excel/CSV")
            print("3. Ver lista de CEDEARs disponibles")
            print("4. Configurar fuente de cotización CCL")
            print("5. Salir")
            print("6. Actualizar ratios de CEDEARs (PDF BYMA)")
            print("7. Análisis de arbitraje para CEDEARs específicos")
            print("8. Refrescar CCL (ignorar cache)")
            print("9. Diagnóstico de servicios (BYMA/IOL)")

            choice = input("\nElige una opción (1-9): ").strip()
            
            if choice == "1":
                await self.handle_iol_portfolio()
            elif choice == "2":
                await self.handle_excel_portfolio()
            elif choice == "3":
                self.services.utility_service.show_cedeares_list()
            elif choice == "4":
                await self.services.config_service.configure_ccl_source()
                # Guardar preferencia local
                self.services.config_service.save_local_preferences()
            elif choice == "5":
                print("¡Hasta luego!")
                break
            elif choice == "6":
                self.services.utility_service.update_byma_cedeares()
            elif choice == "7":
                await self.services.analysis_service.test_arbitrage_analysis()
            elif choice == "8":
                await self.services.analysis_service.refresh_ccl_cache()
            elif choice == "9":
                await self.handle_health_diagnostics()
            else:
                print("❌ Opción inválida. Intenta de nuevo.")
    
    async def handle_iol_portfolio(self):
        """Maneja la obtención de portfolio desde IOL"""
        print("\n📊 Obteniendo portfolio desde IOL...")
        
        try:
            # Solicitar credenciales
            username = input("Usuario IOL: ").strip()
            password = getpass("Contraseña IOL: ")
            
            if not username or not password:
                print("❌ Usuario y contraseña son requeridos")
                return
            
            # Autenticar con IOL
            print("🔐 Autenticando con IOL...")
            while True:
                try:
                    await self.iol_integration.authenticate(username, password)
                    break  # Si llega aquí, la autenticación fue exitosa
                except Exception as e:
                    if "401" in str(e) or "Unauthorized" in str(e):
                        print("❌ Contraseña incorrecta, intente de nuevo.")
                        password = getpass("Contraseña IOL: ")
                    else:
                        print(f"❌ Error de autenticación: {e}")
                        return
            
            
            # Obtener portfolio
            print("📈 Obteniendo portfolio...")
            portfolio = await self.iol_integration.get_portfolio()
            
            # Procesar y mostrar resultados
            cedeares_count = await self.services.portfolio_display_service.process_and_show_portfolio(portfolio, "IOL")
            
            # Convertir CEDEARs si los hay
            converted = None
            if cedeares_count > 0:
                print(f"\n🔄 Convirtiendo {cedeares_count} CEDEARs a subyacentes...")
                converted = self.portfolio_processor.convert_portfolio_to_underlying(portfolio)
                print("✅ Conversión completada: {} CEDEARs convertidos".format(len(converted.converted_positions) if converted else 0))
            
            print(f"\n📊 Portfolio cargado exitosamente con {len(portfolio.positions)} posiciones")
            
            # Preguntar si quiere análisis de arbitraje
            analyze = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
            if analyze == 's':
                await self._analyze_portfolio(portfolio, from_iol=True)
            else:
                print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
            
            # Preguntar si guardar resultados
            save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
            if save == 's':
                await self.services.file_service.save_results(portfolio, converted if cedeares_count > 0 else None)
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def handle_excel_portfolio(self):
        """Maneja la carga de portfolio desde archivo Excel o CSV"""
        try:
            # Usar el nuevo FileProcessingService
            portfolio = await self.services.file_processing_service.handle_excel_portfolio()
            
            if portfolio and len(portfolio.positions) > 0:
                # Mostrar y procesar el portfolio usando el nuevo servicio
                cedeares_count = await self.services.portfolio_display_service.process_and_show_portfolio(
                    portfolio, "Excel/CSV"
                )
                
                # Convertir CEDEARs si los hay
                converted = None
                if cedeares_count > 0:
                    print(f"\n🔄 Convirtiendo {cedeares_count} CEDEARs a subyacentes...")
                    converted = self.portfolio_processor.convert_portfolio_to_underlying(portfolio)
                    print("✅ Conversión completada: {} CEDEARs convertidos".format(len(converted.converted_positions) if converted else 0))
                
                print(f"\n📊 Portfolio cargado exitosamente con {len(portfolio.positions)} posiciones")
                
                # Preguntar si quiere análisis de arbitraje
                analyze = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
                if analyze == 's':
                    await self._analyze_portfolio(portfolio, from_iol=False)
                else:
                    print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
                
                # Preguntar si guardar resultados
                save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
                if save == 's':
                    await self.services.file_service.save_results(portfolio, converted if cedeares_count > 0 else None)
            else:
                print("❌ No se pudo procesar el archivo o está vacío")
                
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            import traceback
            traceback.print_exc()
    # ✅ MÉTODO ELIMINADO - process_and_show_portfolio() (229 líneas)
    # Ahora usa: services.portfolio_display_service.process_and_show_portfolio()
    
    async def _analyze_portfolio(self, portfolio: Portfolio, from_iol: bool = False):
        """Método auxiliar para análisis de arbitraje"""
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
        analysis_result = await self.services.unified_analysis.analyze_portfolio(portfolio, threshold=self.services.config.arbitrage_threshold)
        
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

    # ✅ MÉTODOS ELIMINADOS - AHORA USAN SERVICIOS:
    # - save_results() → services.file_service.save_results()
    # - show_cedeares_list() → services.utility_service.show_cedeares_list()
    # - update_byma_cedeares() → services.utility_service.update_byma_cedeares()
    # - configure_ccl_source() → services.config_service.configure_ccl_source()
    # - test_variation_analysis() → services.analysis_service.test_variation_analysis()
    # - refresh_ccl_cache() → services.analysis_service.refresh_ccl_cache()
    # - _load_local_preferences() → services.config_service.load_local_preferences()
    # - _save_local_preferences() → services.config_service.save_local_preferences()
    # - _read_prefs() → services.config_service.read_prefs()
    # - _write_prefs() → services.config_service.write_prefs()
    # - process_and_show_portfolio() → services.portfolio_display_service.process_and_show_portfolio()
    # - handle_excel_portfolio() → services.file_processing_service.handle_excel_portfolio()

    async def handle_health_diagnostics(self):
        """Maneja el diagnóstico de salud de servicios BYMA e IOL"""
        print("\n🔍 DIAGNÓSTICO DE SERVICIOS")
        print("=" * 50)

        # Verificar si hay sesión IOL activa
        iol_session = getattr(self.iol_integration, 'session', None)

        # 1. Test BYMA
        print("🏛️  Verificando BYMA...")
        try:
            byma_health = await self.services.byma_integration.check_byma_health()
            status_icon = "✅" if byma_health["status"] else "❌"
            business_day_icon = "📅" if byma_health["business_day"] else "🏖️"

            print(f"   {status_icon} Estado: {'Operativo' if byma_health['status'] else 'No responde'}")
            print(f"   {business_day_icon} Día hábil: {'Sí' if byma_health['business_day'] else 'No'}")
            print(f"   ⏱️  Tiempo respuesta: {byma_health['response_time']}s")

            if not byma_health["status"]:
                print(f"   ⚠️  Error: {byma_health['error']}")

        except Exception as e:
            print(f"   ❌ Error verificando BYMA: {str(e)}")

        print()

        # 2. Test IOL
        print("🏦 Verificando IOL...")
        try:
            iol_health = await self.services.byma_integration.check_iol_health(iol_session)

            if iol_session:
                auth_icon = "🔐" if iol_health["authenticated"] else "🔓"
                print(f"   {auth_icon} Autenticado: {'Sí' if iol_health['authenticated'] else 'No'}")
            else:
                print("   📴 Sin sesión IOL activa")

            status_icon = "✅" if iol_health["status"] else "❌"
            print(f"   {status_icon} Estado: {'Operativo' if iol_health['status'] else 'No disponible'}")

            if not iol_health["status"]:
                print(f"   ⚠️  Error: {iol_health['error']}")

        except Exception as e:
            print(f"   ❌ Error verificando IOL: {str(e)}")

        print()
        print("💡 RECOMENDACIONES:")
        print("   • Si BYMA falla en día hábil → Sistema usa estimaciones automáticamente")
        print("   • Si IOL falla → Sistema hace fallback a BYMA automáticamente")
        print("   • Si ambos fallan → Sistema usa precios internacionales + CCL")

        input("\nPresiona Enter para continuar...")

async def main():
    """Función principal con Dependency Injection estricta"""
    print("🏗️  Ejecutando con Dependency Injection estricta...")
    config = Config.from_env()
    services = build_services(config)
    
    replicator = PortfolioReplicator(services)
    await replicator.run()

if __name__ == "__main__":
    asyncio.run(main())