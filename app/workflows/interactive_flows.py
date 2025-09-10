"""
ETL Interactive Flows
Coordinador de flujos interactivos para UI (NO es un pipeline automático)

Este módulo coordina comandos ETL especializados para crear flujos interactivos
que requieren input del usuario en cada paso. Para pipelines automáticos
usar scripts/etl_cli.py
"""

from app.core.services import Services
from app.models.portfolio import Portfolio
from .commands.extraction_commands import ExtractionCommands
from .commands.analysis_commands import AnalysisCommands
from .commands.monitoring_commands import MonitoringCommands


class InteractiveFlows:
    """
    Coordinador de flujos interactivos para análisis de portfolios
    
    IMPORTANTE: Este NO es un pipeline ETL automático. Es un coordinador
    de comandos para flujos interactivos que requieren input del usuario.
    
    Para pipelines ETL automáticos usar: scripts/etl_cli.py
    
    Flujos disponibles:
    - Extracción IOL con análisis interactivo
    - Extracción archivo con análisis interactivo  
    - Comandos individuales de monitoreo
    - Comandos individuales de análisis
    """
    
    def __init__(self, services: Services, iol_integration, portfolio_processor):
        """
        Constructor del coordinador de flujos interactivos
        
        Args:
            services: Container de servicios DI completo
            iol_integration: Integración IOL configurada
            portfolio_processor: Procesador de portfolios
        """
        self.services = services
        self.iol_integration = iol_integration
        self.portfolio_processor = portfolio_processor
        
        # Inicializar comandos especializados
        self.extraction = ExtractionCommands(services, iol_integration, portfolio_processor)
        self.analysis = AnalysisCommands(services, iol_integration) 
        self.monitoring = MonitoringCommands(services, iol_integration)
    
    async def interactive_iol_extraction_and_analysis(self) -> bool:
        """
        Flujo interactivo: Extracción IOL + Análisis + Guardado
        
        Returns:
            bool: True si el flujo se ejecutó exitosamente
        """
        try:
            # 1. Extracción
            portfolio = await self.extraction.extract_iol_portfolio()
            if not portfolio:
                return False
            
            # 2. Procesamiento
            cedeares_count, converted = await self.extraction.process_extracted_portfolio(
                portfolio, "IOL"
            )
            
            # 3. Análisis opcional (INTERACTIVO)
            analyze = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
            if analyze == 's':
                await self.analysis.analyze_portfolio(portfolio, from_iol=True)
            else:
                print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
            
            # 4. Guardado opcional (INTERACTIVO)
            save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
            if save == 's':
                await self.monitoring.save_results(portfolio, converted if cedeares_count > 0 else None)
            
            return True
            
        except Exception as e:
            print(f"❌ Error en flujo IOL: {e}")
            return False
    
    async def interactive_file_extraction_and_analysis(self) -> bool:
        """
        Flujo interactivo: Extracción Archivo + Análisis + Guardado
        
        Returns:
            bool: True si el flujo se ejecutó exitosamente
        """
        try:
            # 1. Extracción
            portfolio = await self.extraction.extract_file_portfolio()
            if not portfolio:
                return False
            
            # 2. Procesamiento
            cedeares_count, converted = await self.extraction.process_extracted_portfolio(
                portfolio, "Excel/CSV"
            )
            
            # 3. Análisis opcional (INTERACTIVO)
            analyze = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
            if analyze == 's':
                await self.analysis.analyze_portfolio(portfolio, from_iol=False)
            else:
                print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
            
            # 4. Guardado opcional (INTERACTIVO)
            save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
            if save == 's':
                await self.monitoring.save_results(portfolio, converted if cedeares_count > 0 else None)
            
            return True
            
        except Exception as e:
            print(f"❌ Error en flujo archivo: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_cedear_monitoring_command(self):
        """
        Comando de monitoreo: Lista de CEDEARs
        """
        await self.monitoring.show_cedeares_list()
    
    async def run_data_update_command(self):
        """
        Comando de actualización: Datos CEDEARs desde BYMA
        """
        await self.monitoring.update_cedeares_data()
    
    async def run_configuration_command(self):
        """
        Comando de configuración: Fuente CCL
        """
        await self.monitoring.configure_ccl_source()
    
    async def run_arbitrage_analysis_command(self):
        """
        Comando de análisis específico: CEDEARs seleccionados
        """
        await self.analysis.analyze_specific_cedeares()
    
    async def run_cache_refresh_command(self):
        """
        Comando de cache: Refresh CCL
        """
        await self.analysis.refresh_ccl_cache()
    
    async def run_health_monitoring_command(self):
        """
        Comando de monitoreo: Diagnósticos completos
        """
        await self.monitoring.run_health_diagnostics()
