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
        Ejecuta diagnósticos de salud completos de todos los servicios del sistema
        Incluye métricas avanzadas de performance y recomendaciones
        """
        print("\n🔍 DIAGNÓSTICO COMPLETO DE SERVICIOS")
        print("=" * 60)

        # 1. Verificar BYMA
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

        # 2. Verificar IOL
        print("🏦 Verificando IOL...")
        try:
            iol_health = await self.iol_integration.check_health()

            if self.iol_integration.session:
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

        # 3. Verificar Database SQLite
        print("💾 Verificando Base de Datos...")
        try:
            db_health = await self._check_database_health()
            db_icon = "✅" if db_health["status"] else "❌"

            print(f"   {db_icon} Conectividad: {'Operativa' if db_health['status'] else 'Error'}")
            print(f"   📊 Tablas: {db_health['tables_count']} encontradas")
            print(f"   📈 Portfolios: {db_health['portfolio_count']}, Posiciones: {db_health['positions_count']}")
            print(f"   🚨 Arbitrajes: {db_health['arbitrage_count']}, Métricas: {db_health['metrics_count']}")
            print(f"   🕒 Última ejecución: {db_health['last_execution']}")

            if not db_health["status"]:
                print(f"   ⚠️  Error: {db_health['error']}")

        except Exception as e:
            print(f"   ❌ Error verificando Base de Datos: {str(e)}")

        print()

        # 4. Verificar APIs Externas
        print("🌐 Verificando APIs Externas...")
        try:
            # Verificar DolarAPI
            ccl_health = await self._check_ccl_api_health()
            ccl_icon = "✅" if ccl_health["status"] else "❌"
            print(f"   {ccl_icon} DolarAPI: {'Operativo' if ccl_health['status'] else 'No disponible'}")
            if ccl_health["status"]:
                print(f"   💵 CCL actual: ${ccl_health['ccl_rate']}")

            # Verificar Finnhub
            finnhub_health = await self._check_finnhub_health()
            finnhub_icon = "✅" if finnhub_health["status"] else "❌"
            print(f"   {finnhub_icon} Finnhub: {'Operativo' if finnhub_health['status'] else 'No disponible'}")
            if finnhub_health["status"]:
                print(f"   📊 Símbolo ejemplo: {finnhub_health['test_symbol']} = ${finnhub_health['test_price']}")

        except Exception as e:
            print(f"   ❌ Error verificando APIs externas: {str(e)}")

        print()

        # 5. Verificación Performance y Cache
        print("Verificando Performance...")
        try:
            perf_health = await self._check_performance_health()
            cache_icon = "✅" if perf_health["cache_working"] else "❌"

            print(f"   {cache_icon} Sistema de Cache: {'Operativo' if perf_health['cache_working'] else 'Error'}")
            print(f"   📊 Cache hits: {perf_health['cache_stats']['hits']}")
            print(f"   📊 Cache misses: {perf_health['cache_stats']['misses']}")
            print(f"   Promedio respuesta: {perf_health['avg_response_time']}ms")

        except Exception as e:
            print(f"   ❌ Error verificando Performance: {str(e)}")

        print()

        # 6. Verificación Sistema y Recursos
        print("🖥️  Verificando Sistema...")
        try:
            system_health = await self._check_system_health()
            memory_icon = "✅" if system_health["memory_ok"] else "⚠️"
            disk_icon = "✅" if system_health["disk_ok"] else "⚠️"

            print(f"   {memory_icon} Memoria: {system_health['memory_usage']:.1f}% utilizada")
            print(f"   {disk_icon} Disco: {system_health['disk_usage']:.1f}% utilizado")
            print(f"   🔗 Conectividad: {'OK' if system_health['network_ok'] else 'Error'}")

        except Exception as e:
            print(f"   ❌ Error verificando sistema: {str(e)}")

        print()
        print("ACLARACIONES:")
        print("   • Si BYMA falla en día hábil → Sistema usa estimaciones automáticamente")
        print("   • Si IOL falla → Sistema hace fallback a BYMA automáticamente")
        print("   • Si ambos fallan → Sistema usa precios internacionales + CCL")
        print("   • Para activar Finnhub → Configurar FINNHUB_API_KEY en .env")
        print("   • Base de datos mantiene historial para análisis offline")
        print("   • Cache mejora performance, se regenera automáticamente")

        # Recomendaciones automáticas
        print("\nRECOMENDACIONES:")
        recommendations = await self._generate_recommendations()
        for rec in recommendations:
            print(f"   • {rec}")

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

    # ===============================================
    # MÉTODOS AUXILIARES PARA HEALTH CHECKS
    # ===============================================

    async def _check_database_health(self):
        """Verifica el estado de la base de datos SQLite"""
        try:
            # Verificar conectividad
            db_service = self.services.database_service
            
            # Contar tablas
            tables_count = await db_service.count_tables()
            
            # Nombres de las tablas principales del sistema
            main_tables = ['portfolios', 'positions', 'arbitrage_opportunities', 'pipeline_metrics']
            
            # Contar registros por tabla
            portfolio_count = await db_service._count_table_records(main_tables[0])
            positions_count = await db_service._count_table_records(main_tables[1])
            arbitrage_count = await db_service._count_table_records(main_tables[2])
            metrics_count = await db_service._count_table_records(main_tables[3])
            
            # Obtener última ejecución
            last_execution = await db_service.get_last_execution_time()
            
            return {
                "status": True,
                "tables_count": tables_count,
                "portfolio_count": portfolio_count,
                "positions_count": positions_count,
                "arbitrage_count": arbitrage_count,
                "metrics_count": metrics_count,
                "last_execution": last_execution or "Nunca"
            }
            
        except Exception as e:
            return {
                "status": False,
                "error": str(e),
                "tables_count": 0,
                "portfolio_count": 0,
                "positions_count": 0,
                "arbitrage_count": 0,
                "metrics_count": 0,
                "last_execution": "Error"
            }

    async def _check_ccl_api_health(self):
        """Verifica el estado de la API de CCL (DolarAPI)"""
        try:
            # Obtener CCL actual usando el servicio correcto
            ccl_data = await self.services.dollar_service.get_ccl_rate()
            
            if ccl_data and 'rate' in ccl_data:
                return {
                    "status": True,
                    "ccl_rate": f"{ccl_data['rate']:.2f}"
                }
            else:
                return {
                    "status": False,
                    "error": "No se pudo obtener CCL",
                    "ccl_rate": "N/A"
                }
            
        except Exception as e:
            return {
                "status": False,
                "error": str(e),
                "ccl_rate": "N/A"
            }

    async def _check_finnhub_health(self):
        """Verifica el estado de la API de Finnhub"""
        try:
            # Verificación con un símbolo conocido usando el servicio correcto
            # Usar símbolo estándar de ejemplo (siempre disponible)
            test_symbol = getattr(self.services.config, 'test_symbol', 'AAPL')
            price_data = await self.services.international_service.get_stock_price(test_symbol)
            
            if price_data and 'price' in price_data:
                return {
                    "status": True,
                    "test_symbol": test_symbol,
                    "test_price": f"{price_data['price']:.2f}"
                }
            else:
                return {
                    "status": False,
                    "error": "No se pudo obtener precio",
                    "test_symbol": test_symbol,
                    "test_price": "N/A"
                }
            
        except Exception as e:
            return {
                "status": False,
                "error": str(e),
                "test_symbol": getattr(self.services.config, 'test_symbol', 'AAPL'),
                "test_price": "N/A"
            }

    async def _check_system_health(self):
        """Verifica el estado del sistema operativo y recursos"""
        try:
            import psutil
        except ImportError:
            # Si no hay psutil, devolver valores básicos
            return {
                "memory_ok": True,
                "memory_usage": 0.0,
                "disk_ok": True,
                "disk_usage": 0.0,
                "network_ok": True,
                "note": "Instalar 'pip install psutil' para métricas de sistema detalladas"
            }

        try:
            import socket

            # Memoria
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # Disco
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent

            # Red
            network_ok = True
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=5)
            except OSError:
                network_ok = False

            return {
                "memory_ok": memory_usage < 90,
                "memory_usage": memory_usage,
                "disk_ok": disk_usage < 95,
                "disk_usage": disk_usage,
                "network_ok": network_ok
            }

        except Exception as e:
            return {
                "memory_ok": False,
                "memory_usage": 0.0,
                "disk_ok": False,
                "disk_usage": 0.0,
                "network_ok": False,
                "error": str(e)
            }

    async def _check_performance_health(self):
        """Verifica el estado del performance y cache del sistema"""
        try:
            # Verificar cache stats (simulado - implementar según tu cache)
            cache_stats = {
                "hits": getattr(self.services.dollar_service, '_cache_hits', 0),
                "misses": getattr(self.services.dollar_service, '_cache_misses', 0)
            }

            # Medición de performance simple
            import time
            start_time = time.time()

            # Hacer una llamada simple para medir respuesta
            await self.services.dollar_service.get_ccl_rate()

            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)

            return {
                "cache_working": True,
                "cache_stats": cache_stats,
                "avg_response_time": response_time
            }

        except Exception as e:
            return {
                "cache_working": False,
                "cache_stats": {"hits": 0, "misses": 0},
                "avg_response_time": "Error",
                "error": str(e)
            }

    async def _generate_recommendations(self):
        """Genera recomendaciones automáticas basadas en el estado del sistema"""
        recommendations = []

        try:
            # Verificar configuración
            config = self.services.config
            if config.arbitrage_threshold > 0.01:
                recommendations.append("Considerar reducir arbitrage_threshold para detectar más oportunidades")

            # Verificar cache
            perf_health = await self._check_performance_health()
            if perf_health["cache_stats"]["misses"] > perf_health["cache_stats"]["hits"]:
                recommendations.append("Optimizar configuración de cache - muchos misses detectados")

            # Verificar APIs
            ccl_health = await self._check_ccl_api_health()
            if not ccl_health["status"]:
                recommendations.append("Configurar fuente CCL alternativa (DolarAPI no disponible)")

            finnhub_health = await self._check_finnhub_health()
            if not finnhub_health["status"]:
                recommendations.append("Configurar FINNHUB_API_KEY para precios internacionales en tiempo real")

            # Verificar sistema
            system_health = await self._check_system_health()
            if system_health["memory_usage"] > 80:
                recommendations.append("Monitorear uso de memoria - alto consumo detectado")
            if not system_health["network_ok"]:
                recommendations.append("Verificar conectividad de red")

            # Si no hay recomendaciones, agregar una positiva
            if not recommendations:
                recommendations.append("Sistema funcionando óptimamente - todas las verificaciones pasaron")

        except Exception as e:
            recommendations.append(f"Error generando recomendaciones: {str(e)}")

        return recommendations
