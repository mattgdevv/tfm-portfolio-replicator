"""
ETL Monitoring Commands
Comandos para monitoreo, configuración y diagnósticos del sistema
"""

from app.core.services import Services


class MonitoringCommands:
    """Comandos de monitoreo y configuración para el pipeline ETL"""
    
    def __init__(self, services: Services, iol_integration):
        """
        Constructor con dependency injection
        
        Args:
            services: Container de servicios DI
            iol_integration: Integración IOL para diagnósticos
        """
        self.services = services
        self.iol_integration = iol_integration
    
    async def show_cedeares_list(self):
        """
        Muestra la lista completa de CEDEARs disponibles
        """
        print("\n📋 Lista de CEDEARs disponibles...")
        self.services.cedear_processor.show_cedeares_list()
    
    async def update_cedeares_data(self):
        """
        Actualiza los datos de CEDEARs desde BYMA
        """
        print("\n🔄 Actualizando datos de CEDEARs desde BYMA...")
        self.services.cedear_processor.update_byma_cedeares()
    
    async def configure_ccl_source(self):
        """
        Configura la fuente de cotización CCL
        """
        print("\n⚙️  Configurando fuente CCL...")
        await self.services.config_service.configure_ccl_source()
    
    async def run_health_diagnostics(self):
        """
        Ejecuta diagnósticos de salud de todos los servicios (BYMA/IOL)
        """
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
    
    async def save_results(self, portfolio, converted_portfolio=None):
        """
        Guarda los resultados del análisis en archivos
        
        Args:
            portfolio: Portfolio original
            converted_portfolio: Portfolio convertido (opcional)
        """
        print("\n💾 Guardando resultados...")
        await self.services.file_service.save_results(portfolio, converted_portfolio)
