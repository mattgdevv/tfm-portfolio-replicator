#!/usr/bin/env python3
"""
Portfolio Replicator ETL Pipeline
Pipeline ETL para análisis de arbitraje de CEDEARs

Este programa implementa un pipeline ETL completo que:
- Extrae datos de múltiples fuentes (IOL, Excel/CSV, BYMA, Finnhub)
- Transforma los datos (conversión CEDEARs, cálculo arbitraje)
- Carga resultados estructurados (JSON, análisis, alertas)
- Monitorea la salud del sistema (APIs, cache, configuración)
"""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
import urllib3

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging silencioso ANTES de importar otros módulos
from app.utils.logging_config import setup_quiet_logging
setup_quiet_logging()

# Imports del sistema de flujos interactivos
from app.workflows import InteractiveFlows
from app.integrations.iol import IOLIntegration
from app.core.config import Config
from app.core.services import build_services, Services
from app.utils.business_days import get_market_status_message


class PortfolioReplicatorInteractive:
    """
    Aplicación interactiva para replicación de portfolios con detección de arbitraje
    
    IMPORTANTE: Esta es la interfaz INTERACTIVA que requiere input del usuario.
    Para pipelines ETL automáticos usar: python scripts/etl_cli.py
    
    Funcionalidades:
    - Flujos interactivos con comandos especializados
    - Análisis paso a paso con confirmaciones del usuario  
    - UI de menú para exploración manual
    """
    
    def __init__(self, services: Services):
        """
        Constructor con Dependency Injection
        
        Args:
            services: Container de servicios construido con build_services()
        """
        if services is None:
            raise ValueError("services es requerido - usar build_services()")
        
        print("🏗️  [Interactive App] Inicializando con dependency injection...")
        self.services = services
        
        # Configurar integraciones
        self.iol_integration = IOLIntegration(
            dollar_service=services.dollar_service,
            cedear_processor=services.cedear_processor
        )
        
        # Inicializar coordinador de flujos interactivos
        self.interactive_flows = InteractiveFlows(
            services=services,
            iol_integration=self.iol_integration,
            portfolio_processor=services.portfolio_processor
        )
        
        # Configuraciones adicionales
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._load_configurations()
        
        print("✅ [Interactive App] Inicialización completada")
    
    def _load_configurations(self):
        """Carga configuraciones y preferencias locales"""
        try:
            # Cargar preferencias locales
            self.services.config_service.load_local_preferences()
            
            # Aplicar TTL de cache CEDEAR desde prefs si existe
            prefs = self.services.config_service.read_prefs()
            ttl = prefs.get('CEDEAR_CACHE_TTL_SECONDS')
            if ttl is not None:
                self.services.arbitrage_detector.set_cedear_cache_ttl(int(ttl))
                print(f"📊 [Config] Cache TTL aplicado: {ttl}s")
        except Exception:
            pass  # Configuración opcional
    
    async def run(self):
        """Ejecuta el menú principal de la aplicación interactiva"""
        print("🚀 Portfolio Replicator - Aplicación Interactiva")
        print("=" * 55)
        print("📊 Análisis de arbitraje de CEDEARs con flujos interactivos")
        print("💡 Para pipelines automáticos usar: python scripts/etl_cli.py")
        print()
        
        while True:
            print("\n🎯 ¿Qué flujo interactivo deseas ejecutar?")
            print("1. 📥 IOL → Análisis → Guardado (interactivo)")
            print("2. 📄 Archivo → Análisis → Guardado (interactivo)") 
            print("3. 📋 Mostrar lista de CEDEARs")
            print("4. ⚙️  Configurar fuente CCL")
            print("5. 🚪 Salir")
            print("6. 🔄 Actualizar datos CEDEARs")
            print("7. 🎯 Análisis de CEDEARs específicos")
            print("8. 🔄 Refrescar cache CCL")
            print("9. 🏥 Diagnóstico de servicios")

            choice = input("\nElige opción (1-9): ").strip()
            
            if choice == "1":
                await self.interactive_flows.interactive_iol_extraction_and_analysis()
            elif choice == "2":
                await self.interactive_flows.interactive_file_extraction_and_analysis()
            elif choice == "3":
                await self.interactive_flows.run_cedear_monitoring_command()
            elif choice == "4":
                await self.interactive_flows.run_configuration_command()
            elif choice == "5":
                print("\n👋 ¡Hasta luego!")
                break
            elif choice == "6":
                await self.interactive_flows.run_data_update_command()
            elif choice == "7":
                await self.interactive_flows.run_arbitrage_analysis_command()
            elif choice == "8":
                await self.interactive_flows.run_cache_refresh_command()
            elif choice == "9":
                await self.interactive_flows.run_health_monitoring_command()
            else:
                print("❌ Opción inválida. Elige entre 1-9.")


async def main():
    """Función principal de la aplicación interactiva"""
    try:
        print("🌅 Inicializando Portfolio Replicator Interactivo...")
        print(f"📅 {get_market_status_message()}")
        print()
        
        # Construir servicios con DI
        config = Config.from_env()
        services = build_services(config)
        
        # Crear y ejecutar replicador interactivo
        replicator = PortfolioReplicatorInteractive(services)
        await replicator.run()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Aplicación interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico en aplicación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔚 Aplicación finalizada")


if __name__ == "__main__":
    asyncio.run(main())
