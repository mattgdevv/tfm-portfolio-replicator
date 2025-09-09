"""
Portfolio App - Interfaz interactiva principal
Contiene toda la lógica de UI que antes estaba en main.py
"""

import asyncio
import logging
import pandas as pd
from getpass import getpass
from pathlib import Path
from tkinter import Tk, filedialog
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.services import Services
from ..models.portfolio import Portfolio, ConvertedPortfolio
from ..integrations.iol import IOLIntegration


class PortfolioApp:
    """
    Aplicación principal del Portfolio Replicator
    Maneja toda la interfaz de usuario interactiva
    """
    
    def __init__(self, services: Services):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            services: Container con todos los servicios configurados
        """
        if services is None:
            raise ValueError("services es requerido - usar build_services() para crear instancias")
        
        print("✅ [PortfolioApp] Usando dependency injection estricta.")
        self.services = services
        # IOLIntegration ahora usa DI estricto
        self.iol_integration = IOLIntegration(
            dollar_service=services.dollar_service,
            cedear_processor=services.cedear_processor
        )

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
                self.show_cedeares_list()
            elif choice == "4":
                await self.configure_ccl_source()
            elif choice == "5":
                print("¡Hasta luego!")
                break
            elif choice == "6":
                self.update_byma_cedeares()
            elif choice == "7":
                await self.test_variation_analysis()
            elif choice == "8":
                await self.refresh_ccl_cache()
            else:
                print("❌ Opción no válida. Intenta de nuevo.")

    async def handle_iol_portfolio(self):
        """Maneja la obtención de portfolio desde IOL"""
        try:
            print("\n🔐 === Autenticación IOL ===")
            
            # Credenciales
            username = input("Usuario IOL: ").strip()
            if not username:
                print("❌ Usuario requerido")
                return
            
            password = getpass("Password IOL: ").strip()
            if not password:
                print("❌ Password requerido")
                return
            
            print("🔐 Autenticando con IOL...")
            while True:
                try:
                    await self.iol_integration.authenticate(username, password)
                    break  # Si llega aquí, la autenticación fue exitosa
                except Exception as e:
                    if "401" in str(e) or "Unauthorized" in str(e):
                        print("❌ Credenciales incorrectas. Intenta de nuevo.")
                        username = input("Usuario IOL: ").strip()
                        password = getpass("Password IOL: ").strip()
                    else:
                        raise  # Re-lanzar si es otro tipo de error
            
            print("✅ Autenticado correctamente")
            
            # Obtener portfolio
            print("📈 Obteniendo portfolio...")
            portfolio = await self.iol_integration.get_portfolio()
            
            # Procesar y mostrar resultados
            await self.process_and_show_portfolio(portfolio, "IOL")
            
        except Exception as e:
            print(f"❌ Error: {e}")

    async def handle_excel_portfolio(self):
        """Maneja la carga de portfolio desde archivo Excel o CSV"""
        try:
            print("\n📁 Cargando portfolio desde archivo Excel/CSV...")
            
            # Crear ventana invisible de tkinter para el diálogo de archivos
            root = Tk()
            root.withdraw()  # Ocultar la ventana principal
            root.lift()      # Traer al frente
            root.attributes('-topmost', True)  # Asegurar que esté arriba
            
            # Variable para capturar el archivo seleccionado
            file_path = None
            
            # Función para abrir el diálogo de archivos en el hilo principal
            def adjuntar_archivo():
                nonlocal file_path
                print("🔍 Abriendo ventana para adjuntar archivo...")
                file_path = filedialog.askopenfilename(
                    title="Selecciona tu archivo de portfolio",
                    filetypes=[
                        ("Archivos Excel/CSV", "*.xlsx *.xls *.csv"),
                        ("Archivos Excel", "*.xlsx *.xls"),
                        ("Archivos CSV", "*.csv"),
                        ("Todos los archivos", "*.*")
                    ]
                )
                root.quit()  # Salir del loop de tkinter
            
            # Ejecutar la función en el hilo principal de tkinter
            root.after(0, adjuntar_archivo)
            root.mainloop()  # Ejecutar el loop de tkinter
            root.destroy()   # Destruir la ventana
            
            if not file_path:
                print("❌ No se seleccionó ningún archivo")
                return
                
            print(f"✅ Archivo seleccionado: {file_path}")
            print(f"📁 Archivo seleccionado: {Path(file_path).name}")
            
            # Preguntar broker
            print("\n🏦 ¿De qué broker es tu archivo?")
            print("1. Cocos Capital")
            print("2. Bull Market")
            print("3. Otro broker (formato estándar)")
            broker_choice = input("Elige opción (1-3): ").strip()
            
            if broker_choice == "1":
                broker = "cocos"
                print("✅ Cocos Capital seleccionado")
            elif broker_choice == "2":
                broker = "bull_market"
                print("✅ Bull Market seleccionado")
            elif broker_choice == "3":
                broker = "generic"
                print("✅ Formato estándar seleccionado")
            else:
                print("❌ Opción no válida, usando formato estándar")
                broker = "generic"
            
            # Procesar archivo
            print("📊 Procesando archivo...")
            portfolio = await self.services.portfolio_processor.process_excel_file(
                file_path, 
                broker_format=broker,
                verbose=True
            )
            
            if not portfolio or not portfolio.positions:
                print("❌ No se pudo procesar el archivo o no contiene posiciones válidas")
                return
            
            # Procesar y mostrar resultados
            await self.process_and_show_portfolio(portfolio, broker_choice)
            
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")

    async def process_and_show_portfolio(self, portfolio: Portfolio, source: str):
        """Procesa y muestra los resultados del portfolio"""
        try:
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
                    from ..config import settings
                    ccl_result = await self.services.dollar_service.get_ccl_rate(settings.PREFERRED_CCL_SOURCE)
                    dollar_rate = (ccl_result.get("rate") if isinstance(ccl_result, dict) else ccl_result) or 1000.0
            except Exception as e:
                print(f"⚠️  No se pudo obtener CCL: {e}")
                dollar_rate = 1000.0
            
            # Mostrar mensaje de mercado cerrado si aplica
            from ..utils.business_days import get_market_status_message
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
            byma_logger = logging.getLogger("app.services.byma_historical")
            variation_logger = logging.getLogger("app.services.variation_analyzer")
            
            original_level_detector = detector_logger.level
            original_level_byma = byma_logger.level
            original_level_variation = variation_logger.level
            
            detector_logger.setLevel(logging.WARNING)
            byma_logger.setLevel(logging.WARNING)
            variation_logger.setLevel(logging.WARNING)
            
            try:
                # Procesar CEDEARs en paralelo para acelerar (limitado a 5 concurrentes)
                cedear_positions = [pos for pos in portfolio.positions if pos.is_cedear]
                semaphore = asyncio.Semaphore(5)  # Limitar concurrencia
                
                async def fetch_symbol(symbol: str):
                    try:
                        async with semaphore:
                            # Obtener precios usando ArbitrageDetector (ya tiene fallback integrado)
                            opportunity = await self.services.arbitrage_detector.detect_single_arbitrage(symbol, threshold=self.services.config.arbitrage_threshold)
                            
                            if opportunity:
                                price_ars = opportunity.cedear_price_ars
                                price_usd = opportunity.underlying_price_usd
                            else:
                                # Fallback: usar precios internacionales directamente
                                underlying_data = await self.services.international_service.get_stock_price(symbol)
                                if underlying_data:
                                    price_usd = underlying_data["price"]
                                    price_ars = price_usd * dollar_rate
                                else:
                                    return None
                            
                            return {
                                "symbol": symbol,
                                "price_ars": price_ars,
                                "price_usd": price_usd
                            }
                    except Exception as e:
                        print(f"❌ Error procesando {symbol}: {e}")
                        return None
                
                # Obtener todos los símbolos únicos de CEDEARs
                unique_symbols = list(set(pos.underlying_symbol for pos in cedear_positions if pos.underlying_symbol))
                
                # Procesar en paralelo
                if unique_symbols:
                    tasks = [fetch_symbol(symbol) for symbol in unique_symbols]
                    price_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Convertir resultados a diccionario
                    price_dict = {}
                    for result in price_results:
                        if result and isinstance(result, dict) and "symbol" in result:
                            price_dict[result["symbol"]] = result
                
                # Mostrar cada posición
                for position in portfolio.positions:
                    if position.is_cedear and position.underlying_symbol:
                        # Es CEDEAR - usar precios calculados
                        symbol = position.underlying_symbol
                        if symbol in price_dict:
                            price_data = price_dict[symbol]
                            price_ars_per_cedear = price_data["price_ars"] / position.conversion_ratio
                            total_ars_position = position.quantity * price_ars_per_cedear
                            total_usd_position = position.underlying_quantity * price_data["price_usd"]
                        else:
                            # Usar precio original si no se pudo obtener actualizado
                            total_ars_position = position.total_value
                            total_usd_position = position.total_value / dollar_rate
                    else:
                        # No es CEDEAR - usar valores originales
                        total_ars_position = position.total_value
                        if position.currency == "USD":
                            total_usd_position = position.total_value
                            total_ars_position = position.total_value * dollar_rate
                        else:
                            total_usd_position = position.total_value / dollar_rate
                    
                    # Formato de la fila
                    print(f"│ {position.symbol:<7} │ {position.quantity:>8} │ ${total_ars_position:>13,.0f} │ {position.underlying_quantity or position.quantity:>11.1f} │ ${total_usd_position:>13,.2f} │")
                    
                    total_ars += total_ars_position
                    total_usd += total_usd_position
                    
            finally:
                # Restaurar niveles de logging
                detector_logger.setLevel(original_level_detector)
                byma_logger.setLevel(original_level_byma)
                variation_logger.setLevel(original_level_variation)
            
            # Mostrar totales
            print("├─────────┼──────────┼─────────────────┼─────────────┼─────────────────┤")
            print(f"│ {'TOTAL':<7} │ {'':>8} │ ${total_ars:>13,.0f} │ {'':>11} │ ${total_usd:>13,.2f} │")
            print("└─────────┴──────────┴─────────────────┴─────────────┴─────────────────┘")
            print(f"💱 Cotización USD: ${dollar_rate:,.2f} ARS")
            
            # Convertir a activos subyacentes
            cedear_count = sum(1 for pos in portfolio.positions if pos.is_cedear)
            if cedear_count > 0:
                print(f"\n🔄 Convirtiendo {cedear_count} CEDEARs a subyacentes...")
                converted_portfolio = self.services.portfolio_processor.convert_cedeares_to_underlying(portfolio)
                print(f"✅ Conversión completada: {len(converted_portfolio.converted_positions)} CEDEARs convertidos")
            else:
                converted_portfolio = None
            
            print(f"\n📊 Portfolio cargado exitosamente con {len(portfolio.positions)} posiciones")
            
            # Preguntar por análisis de arbitraje
            if cedear_count > 0:
                analyze = input("🔍 ¿Deseas analizar oportunidades de arbitraje? (s/n): ").strip().lower()
                if analyze == 's':
                    threshold_pct = self.services.config.arbitrage_threshold * 100
                    print(f"\n🔍 Analizando oportunidades de arbitraje (threshold: {threshold_pct:.1f}%)...")
                    
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
                    
                    # Configurar sesión IOL si está disponible
                    if iol_session:
                        self.services.arbitrage_detector.set_iol_session(iol_session)
                        self.services.variation_analyzer.set_iol_session(iol_session)
                    
                    # Ejecutar análisis usando UnifiedAnalysisService
                    analysis_result = await self.services.unified_analysis.analyze_portfolio(
                        portfolio, threshold=self.services.config.arbitrage_threshold)
                    
                    # Mostrar resultados de manera consistente
                    summary_text = self.services.unified_analysis.format_analysis_summary(analysis_result)
                    print(summary_text)
                    
                    
                else:
                    print("✅ Portfolio cargado. Análisis de arbitraje omitido.")
            
            # Preguntar si guardar
            save = input("\n💾 ¿Guardar resultados en archivo? (s/n): ").strip().lower()
            if save == 's':
                await self.save_results(portfolio, converted_portfolio)
            
        except Exception as e:
            print(f"❌ Error procesando portfolio: {e}")
            raise

    async def save_results(self, original: Portfolio, converted: ConvertedPortfolio = None):
        """Guarda los resultados en archivos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Guardar portfolio original
            original_data = []
            for pos in original.positions:
                original_data.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'price': pos.price,
                    'currency': pos.currency,
                    'total_value': pos.total_value,
                    'is_cedear': pos.is_cedear,
                    'underlying_symbol': pos.underlying_symbol,
                    'underlying_quantity': pos.underlying_quantity
                })
            
            original_df = pd.DataFrame(original_data)
            original_file = f"portfolio_original_{timestamp}.xlsx"
            original_df.to_excel(original_file, index=False)
            print(f"✅ Portfolio original guardado: {original_file}")
            
            # Guardar portfolio convertido si existe
            if converted:
                converted_data = []
                for pos in converted.converted_positions:
                    converted_data.append({
                        'symbol': pos.symbol,
                        'quantity': pos.quantity,
                        'price': pos.price,
                        'currency': pos.currency,
                        'total_value': pos.total_value
                    })
                
                converted_df = pd.DataFrame(converted_data)
                converted_file = f"portfolio_converted_{timestamp}.xlsx"
                converted_df.to_excel(converted_file, index=False)
                print(f"✅ Portfolio convertido guardado: {converted_file}")
                
        except Exception as e:
            print(f"❌ Error guardando archivos: {e}")

    def show_cedeares_list(self):
        """Muestra la lista de CEDEARs disponibles"""
        print("\n🏦 CEDEARs disponibles:")
        cedeares = self.services.cedear_processor.get_all_cedeares()
        
        # Mostrar primeros 10 como ejemplo
        for i, cedear in enumerate(cedeares[:10], 1):
            # Manejar diferentes estructuras de datos
            code = cedear.get('code') or cedear.get('symbol', 'N/A')
            company = cedear.get('company') or cedear.get('name', 'N/A')
            ratio = cedear.get('ratio', 'N/A')
            print(f"  {i}. {code} - {company} (Ratio: {ratio})")
        
        if len(cedeares) > 10:
            print(f"  ... y {len(cedeares) - 10} más")
        
        print(f"\n📊 Total de CEDEARs: {len(cedeares)}")

    def update_byma_cedeares(self):
        """Descarga y parsea el PDF de BYMA para obtener ratios de CEDEARs."""
        print("\n🔄 Descargando y procesando PDF de CEDEARs desde BYMA...")
        
        try:
            import subprocess
            import sys
            
            # Ejecutar el script de descarga
            script_path = Path(__file__).parent.parent.parent / "scripts" / "download_byma_pdf.py"
            result = subprocess.run([sys.executable, str(script_path)], 
                                  capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                print("✅ PDF descargado y procesado exitosamente")
                print(result.stdout)
            else:
                print("❌ Error en el procesamiento:")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Error ejecutando script: {e}")

    async def configure_ccl_source(self):
        """Configura la fuente de cotización CCL"""
        print("\n💱 Configuración de fuente CCL")
        print("=" * 40)
        
        # Cargar preferencias actuales
        prefs = self._load_local_preferences()
        current_source = prefs.get("preferred_ccl_source", "auto")
        
        print(f"🔧 Fuente actual: {current_source}")
        print("\nFuentes disponibles:")
        print("1. auto (automático con fallback)")
        print("2. dolarapi_ccl (DolarAPI CCL)")
        print("3. iol_ccl (IOL CCL - requiere autenticación)")
        print("4. byma_ccl (BYMA histórico)")
        
        choice = input("\nSelecciona nueva fuente (1-4) o Enter para mantener actual: ").strip()
        
        source_map = {
            "1": "auto",
            "2": "dolarapi_ccl", 
            "3": "iol_ccl",
            "4": "byma_ccl"
        }
        
        if choice in source_map:
            new_source = source_map[choice]
            
            # Probar la fuente antes de guardarla
            print(f"\n🧪 Probando fuente '{new_source}'...")
            if await self._test_ccl_source(new_source):
                prefs["preferred_ccl_source"] = new_source
                self._save_local_preferences()
                print(f"✅ Fuente CCL configurada: {new_source}")
            else:
                print(f"❌ Error con la fuente '{new_source}'. Manteniendo configuración actual.")
        else:
            print("✅ Configuración mantenida sin cambios")

    async def _test_ccl_source(self, source: str):
        """Prueba una fuente CCL específica"""
        try:
            result = await self.services.dollar_service.get_ccl_rate(source)
            if result and (isinstance(result, (int, float)) or 
                          (isinstance(result, dict) and result.get("rate"))):
                rate = result.get("rate") if isinstance(result, dict) else result
                print(f"✅ {source}: ${rate:,.2f} ARS")
                return True
            else:
                print(f"❌ {source}: No se pudo obtener cotización")
                return False
        except Exception as e:
            print(f"❌ {source}: Error - {str(e)}")
            return False

    def _load_local_preferences(self):
        """Carga preferencias locales (como fuente CCL preferida) desde un archivo simple."""
        try:
            return self._read_prefs()
        except Exception:
            return {}

    def _save_local_preferences(self):
        """Guarda preferencias locales (como fuente CCL preferida) en un archivo simple."""
        try:
            prefs = self._load_local_preferences()
            self._write_prefs(prefs)
        except Exception as e:
            print(f"⚠️  No se pudieron guardar preferencias: {e}")

    async def test_variation_analysis(self):
        """Análisis unificado de arbitraje para CEDEARs individuales"""
        print("\n📊 Análisis de Arbitraje de CEDEARs")
        print("=" * 50)
        print("Esta función analiza oportunidades de arbitraje para CEDEARs específicos")
        print("usando el mismo sistema unificado que el análisis de portfolio.")
        
        print("\n📝 Introduce los símbolos de CEDEARs a analizar")
        print("💡 Ejemplos: TSLA, AAPL, GOOGL, MSFT, AMZN")
        print("   (separados por comas)")
        
        symbols_input = input("\n🔍 CEDEARs a analizar: ").strip()
        if not symbols_input:
            print("❌ No se proporcionaron símbolos")
            return
        
        # Parsear símbolos
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        print(f"\n🔍 Analizando {len(symbols)} símbolos: {symbols}")
        
        # Preguntar si usar IOL para mayor precisión
        use_iol = input("\n¿Usar datos de IOL para mayor precisión? (s/n): ").strip().lower()
        iol_session = None
        
        if use_iol == 's':
            # Solicitar credenciales IOL
            try:
                username = input("Usuario IOL: ").strip()
                password = getpass("Password IOL: ").strip()
                
                if username and password:
                    print("🔐 Autenticando con IOL...")
                    await self.iol_integration.authenticate(username, password)
                    iol_session = self.iol_integration.session
                    print("✅ Autenticado correctamente con IOL")
                else:
                    print("⚠️  Credenciales no proporcionadas, usando modo limitado")
            except Exception as e:
                print(f"❌ Error autenticando con IOL: {e}")
                print("🔄 Continuando en modo limitado...")
        
        # Configurar servicios con sesión IOL si está disponible
        if iol_session:
            self.services.arbitrage_detector.set_iol_session(iol_session)
            self.services.variation_analyzer.set_iol_session(iol_session)
        
        mode = "COMPLETO (IOL)" if iol_session else "LIMITADO (BYMA + Finnhub)"
        print(f"🟡 Modo: {mode}")
        
        try:
            # Crear portfolio temporal con los símbolos especificados
            from ..models.portfolio import Position
            positions = []
            for symbol in symbols:
                # Verificar que sea un CEDEAR válido
                if self.services.cedear_processor.is_cedear(symbol):
                    underlying_info = self.services.cedear_processor.get_underlying_asset(symbol)
                    if underlying_info:
                        conversion_ratio = self.services.cedear_processor.parse_ratio(underlying_info["ratio"])
                        position = Position(
                            symbol=symbol,
                            quantity=1,  # Cantidad simbólica para análisis
                            price=0,     # Se calculará dinámicamente
                            total_value=0,
                            currency="ARS",
                            is_cedear=True,
                            underlying_symbol=underlying_info["symbol"],
                            underlying_quantity=1/conversion_ratio,
                            conversion_ratio=conversion_ratio
                        )
                        positions.append(position)
                    else:
                        print(f"⚠️  No se encontró información para el CEDEAR: {symbol}")
                else:
                    print(f"⚠️  {symbol} no es un CEDEAR válido")
            
            if not positions:
                print("❌ No se encontraron CEDEARs válidos para analizar")
                return
            
            # Crear portfolio temporal
            temp_portfolio = Portfolio(positions=positions, broker="manual")
            
            print(f"\n🔍 Analizando arbitraje para {len(positions)} CEDEARs...")
            
            # Ejecutar análisis usando UnifiedAnalysisService
            analysis_result = await self.services.unified_analysis.analyze_portfolio(
                temp_portfolio, threshold=self.services.config.arbitrage_threshold)
            
            # Mostrar resultados de manera consistente
            summary_text = self.services.unified_analysis.format_analysis_summary(analysis_result)
            print(summary_text)
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")

    async def refresh_ccl_cache(self):
        """Invalida el cache de CCL y fuerza un refetch de la fuente preferida."""
        print("\n🔄 Refrescando cache de CCL...")
        
        try:
            # Cargar fuente preferida
            prefs = self._load_local_preferences()
            preferred_source = prefs.get("preferred_ccl_source", "auto")
            
            print(f"🎯 Usando fuente: {preferred_source}")
            
            # Forzar refetch (ignorar cache)
            result = await self.services.dollar_service.get_ccl_rate(preferred_source, force_refresh=True)
            
            if result:
                rate = result.get("rate") if isinstance(result, dict) else result
                source_used = result.get("source") if isinstance(result, dict) else preferred_source
                print(f"✅ CCL refrescado: ${rate:,.2f} ARS (fuente: {source_used})")
            else:
                print("❌ No se pudo obtener cotización CCL")
                
        except Exception as e:
            print(f"❌ Error refrescando CCL: {e}")

    def _read_prefs(self) -> dict:
        try:
            import json
            prefs_file = Path("portfolio_prefs.json")
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_prefs(self, data: dict) -> None:
        try:
            import json
            with open("portfolio_prefs.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
