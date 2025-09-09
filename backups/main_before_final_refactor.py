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
            print("7. Probar análisis de variaciones de CEDEARs")
            print("8. Refrescar CCL (ignorar cache)")
            
            choice = input("\nElige una opción (1-8): ").strip()
            
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
                await self.services.analysis_service.test_variation_analysis()
            elif choice == "8":
                await self.services.analysis_service.refresh_ccl_cache()
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
            await self.process_and_show_portfolio(portfolio, "IOL")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def handle_excel_portfolio(self):
        """Maneja la carga de portfolio desde archivo Excel o CSV"""
        print("\n📁 Cargando portfolio desde archivo Excel/CSV...")
        
        try:
            # Intentar usar tkinter para selección de archivo
            file_path = None
            
            # Usar tkinter simple como sugieres
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                # Crear ventana principal
                root = tk.Tk()
                root.title("Adjuntar archivo de portfolio")
                root.geometry("400x200")
                
                # Centrar la ventana
                root.eval('tk::PlaceWindow . center')
                
                # Variable para almacenar el archivo seleccionado
                file_path = None
                
                # Función que se ejecuta al presionar el botón
                def adjuntar_archivo():
                    nonlocal file_path
                    archivo = filedialog.askopenfilename(
                        title="Seleccionar archivo de portfolio",
                        filetypes=[
                            ("Archivos Excel", "*.xlsx *.xls"),
                            ("Archivos CSV", "*.csv"),
                            ("Todos los archivos", "*.*")
                        ]
                    )
                    if archivo:
                        file_path = archivo
                        print(f"✅ Archivo seleccionado: {archivo}")
                        root.quit()  # Cerrar la ventana
                    else:
                        print("❌ No se seleccionó ningún archivo")
                        root.quit()
                
                # Crear el botón y agregarlo a la ventana
                boton = tk.Button(root, text="📎 Adjuntar archivo", command=adjuntar_archivo, 
                                font=("Arial", 14), bg="#4CAF50", fg="white", 
                                relief="raised", bd=3)
                boton.pack(pady=50)
                
                # Texto explicativo
                label = tk.Label(root, text="Selecciona tu archivo de portfolio\n(Excel o CSV)", 
                               font=("Arial", 12))
                label.pack(pady=20)
                
                print("🔍 Abriendo ventana para adjuntar archivo...")
                
                # Iniciar el bucle principal
                root.mainloop()
                
                # Si no se seleccionó archivo, usar modo manual
                if not file_path:
                    print("\n📝 Cambiando a modo manual...")
                    print("💡 Puedes arrastrar el archivo desde Finder/Explorer a esta terminal")
                    print("   O escribir la ruta completa del archivo")
                    
                    file_path = input("📎 Archivo (arrastra o escribe ruta): ").strip()
                    
                    # Limpiar la ruta si el usuario arrastró el archivo
                    if file_path.startswith("'") and file_path.endswith("'"):
                        file_path = file_path[1:-1]
                    elif file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]
                
            except Exception as e:
                print(f"⚠️  Error con interfaz gráfica: {e}")
                print("🔄 Cambiando a modo manual...")
                print("💡 Puedes arrastrar el archivo desde Finder/Explorer a esta terminal")
                print("   O escribir la ruta completa del archivo")
                
                file_path = input("📎 Archivo (arrastra o escribe ruta): ").strip()
                
                # Limpiar la ruta si el usuario arrastró el archivo
                if file_path.startswith("'") and file_path.endswith("'"):
                    file_path = file_path[1:-1]
                elif file_path.startswith('"') and file_path.endswith('"'):
                    file_path = file_path[1:-1]
            
            if not file_path:
                print("❌ No se seleccionó ningún archivo")
                return
            
            # Convertir a Path object (caja de herramientas)
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ Archivo no encontrado: {file_path}")
                return
                
            print(f"📁 Archivo seleccionado: {file_path.name}")
            
            # Selector de broker
            print("\n🏦 ¿De qué broker es tu archivo?")
            print("1. Cocos Capital")
            print("2. Bull Market") 
            print("3. Otro broker (formato estándar)")
            
            broker_choice = input("Elige opción (1-3): ").strip()
            
            if broker_choice == "1":
                broker = "Cocos Capital"
                print("✅ Cocos Capital seleccionado")
            elif broker_choice == "2":
                broker = "Bull Market"
                print("✅ Bull Market seleccionado")
            elif broker_choice == "3":
                broker = "Estándar"
                print("✅ Formato estándar seleccionado")
                print("💡 Usa CSV con columnas: 'symbol,quantity'")
            else:
                print("⚠️  Opción inválida, usando formato estándar")
                broker = "Estándar"
            
            # Procesar archivo con el broker seleccionado
            print("📊 Procesando archivo...")
            portfolio = await self.portfolio_processor.process_file(str(file_path), broker)
            
            # Procesar y mostrar resultados
            await self.process_and_show_portfolio(portfolio, broker or f"Archivo {file_path.suffix}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"🔍 Tipo de file_path: {type(file_path) if 'file_path' in locals() else 'No definido'}")
            print(f"🔍 Valor de file_path: {file_path if 'file_path' in locals() else 'No definido'}")
            print("💡 Asegúrate de que el archivo tenga el formato correcto")
    
    async def process_and_show_portfolio(self, portfolio: Portfolio, source: str):
        """Procesa y muestra los resultados del portfolio"""
        print(f"\n📋 Portfolio obtenido desde {source}")
        print(f"📊 Total de posiciones: {len(portfolio.positions)}")
        
        # Contar CEDEARs
        cedeares_count = sum(1 for pos in portfolio.positions if pos.is_cedear)
        print(f"🏦 CEDEARs encontrados: {cedeares_count}")
        
        # Obtener cotización del dólar (CCL). Preferir IOL si hay sesión; sino usar DollarRateService (dolarapi/IOL fallback)
        try:
            dollar_rate = None
            # Intentar vía IOL si hay sesión válida
            try:
                dollar_rate = await self.iol_integration.get_dollar_rate()
            except Exception as e_iol:
                print(f"⚠️  No se pudo obtener CCL desde IOL: {e_iol}")
            # Fallback a DollarRateService (usa preferencia y agrega implícito como último)
            if not dollar_rate or dollar_rate <= 0:
                from app.config import settings
                ccl_result = await self.services.dollar_service.get_ccl_rate(settings.PREFERRED_CCL_SOURCE)
                dollar_rate = (ccl_result.get("rate") if isinstance(ccl_result, dict) else ccl_result) or 1000.0
        except Exception as e:
            print(f"⚠️  No se pudo obtener CCL: {e}")
            dollar_rate = 1000.0
        
        # Mostrar mensaje de mercado cerrado si aplica
        market_message = get_market_status_message("AR")
        if market_message:
            print(f"\n{market_message}")
        
        # Mostrar posiciones en formato tabla
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
        missing_symbols = []
        for pos in portfolio.positions:
            if pos.is_cedear and pos.underlying_symbol and pos.total_value is None:
                if pos.symbol not in missing_symbols:
                    missing_symbols.append(pos.symbol)
        prefetch_prices: dict[str, float] = {}
        if missing_symbols:
            async def fetch_symbol(symbol: str):
                try:
                    price_ars, _ = await self.services.arbitrage_detector._get_cedear_price_usd(symbol)
                    return symbol, price_ars
                except Exception:
                    return symbol, None
            results = await asyncio.gather(*(fetch_symbol(s) for s in missing_symbols))
            prefetch_prices = {s: p for s, p in results if p}

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
                    precio_ars = prefetch_prices.get(pos.symbol)
                    if precio_ars is None:
                        try:
                            precio_ars, _precio_usd_unit = await self.services.arbitrage_detector._get_cedear_price_usd(pos.symbol)
                        except Exception:
                            precio_ars = None
                        
                        # Fallback: calcular precio usando Finnhub + CCL cuando BYMA no tiene el CEDEAR
                        if precio_ars is None and pos.is_cedear:
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
                                                ratio = float(ratio_str.split(":")[0])
                                            else:
                                                ratio = float(ratio_str)
                                        except:
                                            ratio = 1.0
                                    
                                    # Calcular precio CEDEAR estimado: (Precio_USD / Ratio) * CCL
                                    precio_ars = (underlying_price_usd / ratio) * ccl_rate
                                    
                            except Exception as e:
                                print(f"⚠️  Fallback falló para {pos.symbol}: {e}")
                                precio_ars = None
                    if precio_ars and precio_ars > 0:
                        total_value_ars = precio_ars * (pos.quantity or 0)
                        total_ars += total_value_ars
                        actions = pos.underlying_quantity or 0
                        value_usd = total_value_ars / dollar_rate if dollar_rate else 0
                        total_usd += value_usd
                        print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {actions:>10.1f} │ ${value_usd:>14,.2f} │")
                    else:
                        actions = pos.underlying_quantity or 0
                        print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ {'(Ver análisis)':>15} │ {actions:>10.1f} │ {'(Ver análisis)':>15} │")
            elif pos.is_fci_usd:
                # Es un FCI en dólares
                total_value_usd = pos.total_value  # Valor en USD
                total_value_ars = total_value_usd * dollar_rate  # Convertir a ARS
                total_ars += total_value_ars
                total_usd += total_value_usd
                print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {'-':>10} │ ${total_value_usd:>14,.2f} │")
            elif pos.is_fci_ars:
                # Es un FCI en pesos
                total_value_ars = pos.total_value
                total_ars += total_value_ars
                value_usd = total_value_ars / dollar_rate
                total_usd += value_usd
                print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {'-':>10} │ ${value_usd:>14,.2f} │")
            else:
                # Otro tipo de activo (acciones locales, bonos, etc.)
                if pos.total_value is not None:
                    total_value_ars = pos.total_value
                    total_ars += total_value_ars
                    value_usd = total_value_ars / dollar_rate
                    total_usd += value_usd
                    print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ ${total_value_ars:>14,.0f} │ {'-':>10} │ ${value_usd:>14,.2f} │")
                else:
                    # Price no disponible del archivo
                    print(f"│ {pos.symbol:<7} │ {pos.quantity:>8.0f} │ {'(Sin precio)':>15} │ {'-':>10} │ {'(Sin precio)':>15} │")
        
        print("├─────────┼──────────┼─────────────────┼─────────────┼─────────────────┤")
        print(f"│ TOTAL   │          │ ${total_ars:>14,.0f} │            │ ${total_usd:>14,.2f} │")
        print("└─────────┴──────────┴─────────────────┴─────────────┴─────────────────┘")
        # Restaurar niveles de logs
        detector_logger.setLevel(previous_level_detector)
        dollar_logger.setLevel(previous_level_dollar)
        print(f"💱 Cotización USD: ${dollar_rate:,.2f} ARS")
        
        # Mostrar disclaimer si hay posiciones de archivos externos
        external_usd_positions = [p for p in portfolio.positions 
                                if p.currency.upper() == 'USD' and hasattr(p, 'dollar_source')]
        if external_usd_positions:
            sources = set(p.dollar_source for p in external_usd_positions if p.dollar_source)
            if sources:
                print(f"\n⚠️  DISCLAIMER: Los valores en ARS para posiciones externas se calcularon")
                print(f"   usando cotización {', '.join(sources)}. Los valores pueden diferir")
                print(f"   ligeramente de los del broker original debido a diferencias en la")
                print(f"   cotización del dólar utilizada.")
        
        # Convertir a subyacentes
        converted = None
        if cedeares_count > 0:
            print(f"\n🔄 Convirtiendo {cedeares_count} CEDEARs a subyacentes...")
            converted = self.portfolio_processor.convert_portfolio_to_underlying(portfolio)
            
            print(f"✅ Conversión completada: {converted.conversion_summary['total_cedeares']} CEDEARs convertidos")
            
            # Preguntar si desea analizar arbitrajes
            print(f"\n📊 Portfolio cargado exitosamente con {len(portfolio.positions)} posiciones")
            run_analysis = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
            
            if run_analysis == 's':
                # Análisis unificado de arbitraje
                try:
                    print(f"\n🔍 Analizando oportunidades de arbitraje (threshold: 0.5%)...")
                    
                    # Para Excel: por defecto modo limited, preguntar si usar IOL
                    iol_session = None
                    if (self.iol_integration and hasattr(self.iol_integration, 'session') 
                        and self.iol_integration.session):
                        print("🔑 Credenciales IOL detectadas.")
                        use_iol = input("¿Usar IOL para análisis más preciso? (s/n): ").strip().lower()
                        if use_iol == 's':
                            iol_session = self.iol_integration.session
                            print("🔴 Modo: COMPLETO (IOL + Finnhub)")
                        else:
                            print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
                    else:
                        print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
                    
                    # Siempre configurar la sesión (puede ser None)
                    self.services.unified_analysis.set_iol_session(iol_session)
                    
                    # Realizar análisis unificado
                    analysis_result = await self.services.unified_analysis.analyze_portfolio(portfolio, threshold=0.005)
                    
                    # Mostrar resultados de manera consistente
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
                        
                except Exception as e:
                    print(f"\n⚠️  Error analizando arbitrajes: {e}")
                    print("💡 El portfolio se procesó correctamente, solo falló el análisis de arbitraje")
            else:
                print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
        
        # Preguntar si guardar resultados
        save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
        if save == 's':
            await self.services.file_service.save_results(portfolio, converted if cedeares_count > 0 else None)
    
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

async def main():
    """Función principal con Dependency Injection estricta"""
    print("🏗️  Ejecutando con Dependency Injection estricta...")
    config = Config.from_env()
    services = build_services(config)
    
    replicator = PortfolioReplicator(services)
    await replicator.run()

if __name__ == "__main__":
    asyncio.run(main())