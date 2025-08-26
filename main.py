#!/usr/bin/env python3
"""
Portfolio Replicator MVP
Programa principal para procesar portafolios y convertir CEDEARs
"""

import asyncio
import logging
import os
import sys
from getpass import getpass
from pathlib import Path

import requests
import json
import urllib3
from datetime import datetime, timedelta

# Configurar logging silencioso ANTES de importar otros módulos
from app.utils.logging_config import setup_quiet_logging
setup_quiet_logging()

from app.integrations.iol import IOLIntegration
from app.processors.file_processor import PortfolioProcessor
from app.processors.cedeares import CEDEARProcessor
from app.models.portfolio import Portfolio, ConvertedPortfolio
from app.config import settings
from app.services.dollar_rate import dollar_service
from app.services.arbitrage_detector import arbitrage_detector
from app.services.unified_analysis import unified_analysis

class PortfolioReplicator:
    def __init__(self):
        self.iol_integration = IOLIntegration()
        self.portfolio_processor = PortfolioProcessor()
        self.cedear_processor = CEDEARProcessor()
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
        self._load_local_preferences()
        # Aplicar TTL de cache CEDEAR desde prefs si existe
        try:
            prefs = self._read_prefs()
            ttl = prefs.get('CEDEAR_CACHE_TTL_SECONDS')
            if ttl is not None:
                from app.services.arbitrage_detector import arbitrage_detector
                arbitrage_detector.set_cedear_cache_ttl(int(ttl))
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
                self.show_cedeares_list()
            elif choice == "4":
                await self.configure_ccl_source()
                # Guardar preferencia local
                self._save_local_preferences()
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
            
            # Solicitar broker (opcional)
            broker = input("Broker (opcional): ").strip() or None
            
            # Procesar archivo directamente con el procesador
            print("📊 Procesando archivo...")
            portfolio = await self.portfolio_processor.process_file(str(file_path), broker or "Unknown")
            
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
                ccl_result = await dollar_service.get_ccl_rate(settings.PREFERRED_CCL_SOURCE)
                dollar_rate = (ccl_result.get("rate") if isinstance(ccl_result, dict) else ccl_result) or 1000.0
        except Exception as e:
            print(f"⚠️  No se pudo obtener CCL: {e}")
            dollar_rate = 1000.0
        
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
                    price_ars, _ = await arbitrage_detector._get_cedear_price_usd(symbol)
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
                            precio_ars, _precio_usd_unit = await arbitrage_detector._get_cedear_price_usd(pos.symbol)
                        except Exception:
                            precio_ars = None
                        
                        # Fallback: calcular precio usando Finnhub + CCL cuando BYMA no tiene el CEDEAR
                        if precio_ars is None and pos.is_cedear:
                            try:
                                # Obtener precio subyacente en USD
                                from app.services.international_prices import international_price_service
                                underlying_data = await international_price_service.get_stock_price(pos.symbol)
                                
                                if underlying_data:
                                    underlying_price_usd = underlying_data["price"]
                                    ccl_data = await dollar_service.get_ccl_rate()
                                    ccl_rate = ccl_data["rate"] if ccl_data else 1300.0
                                    
                                    # Obtener ratio de conversión
                                    from app.processors.cedeares import cedeares_processor
                                    cedear_info = cedeares_processor.get_cedear_info(pos.symbol)
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
                    unified_analysis.set_iol_session(iol_session)
                    
                    # Realizar análisis unificado
                    analysis_result = await unified_analysis.analyze_portfolio(portfolio, threshold=0.005)
                    
                    # Mostrar resultados de manera consistente
                    summary_text = unified_analysis.format_analysis_summary(analysis_result)
                    print(summary_text)
                    
                    # Mostrar alertas detalladas si hay oportunidades
                    opportunities = analysis_result["arbitrage_opportunities"]
                    if opportunities:
                        print("\n" + "="*60)
                        for opp in opportunities:
                            alert_text = arbitrage_detector.format_alert(opp)
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
            await self.save_results(portfolio, converted if cedeares_count > 0 else None)
    
    async def save_results(self, original: Portfolio, converted: ConvertedPortfolio = None):
        """Guarda los resultados en archivos"""
        try:
            import pandas as pd
            from datetime import datetime
            
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
        cedeares = self.cedear_processor.get_all_cedeares()
        
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
            result = subprocess.run([
                "python", "scripts/download_byma_pdf.py"
            ], capture_output=True, text=True, cwd=".")
            
            if result.returncode == 0:
                print("✅ PDF procesado exitosamente")
                if "CEDEARs" in result.stdout:
                    # Extraer número de CEDEARs del output
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if "Total de CEDEARs:" in line:
                            print(f"✅ {line}")
                            break
                else:
                    print("✅ Archivo byma_cedeares_pdf.json actualizado")
            else:
                print(f"❌ Error procesando PDF: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error ejecutando download_byma_pdf.py: {e}")
    
    async def configure_ccl_source(self):
        """Configura la fuente de cotización CCL"""
        print("\n💱 Configuración de fuente CCL")
        print("=" * 40)
        
        current_source = settings.PREFERRED_CCL_SOURCE
        source_names = {
            "dolarapi_ccl": "DolarAPI CCL (contadoconliqui)",
            "ccl_al30": "CCL AL30 (AL30/AL30D desde IOL)"
        }
        
        print(f"🔍 Fuente actual: {source_names.get(current_source, current_source)}")
        
        # Mostrar opciones disponibles
        print("\nFuentes disponibles:")
        print("1. DolarAPI CCL (contadoconliqui) - Rápido y confiable")
        print("2. CCL AL30 (AL30/AL30D desde IOL) - Más preciso pero requiere autenticación IOL")
        
        choice = input("\nElige la fuente CCL (1-2, o Enter para mantener actual): ").strip()
        
        if choice == "1":
            new_source = "dolarapi_ccl"
        elif choice == "2":
            new_source = "ccl_al30"
        elif choice == "":
            print("✅ Manteniendo fuente actual")
            return
        else:
            print("❌ Opción inválida")
            return
        
        # Actualizar configuración
        settings.PREFERRED_CCL_SOURCE = new_source
        print(f"✅ Fuente CCL actualizada a: {source_names[new_source]}")
        
        # Probar la nueva fuente
        test = input("\n🧪 ¿Probar la nueva fuente? (s/n): ").strip().lower()
        if test == 's':
            await self._test_ccl_source(new_source)
    
    async def _test_ccl_source(self, source: str):
        """Prueba una fuente CCL específica"""
        print(f"\n🧪 Probando fuente: {source}")
        
        try:
            from app.services.dollar_rate import dollar_service
            result = await dollar_service.get_ccl_rate(source)
            
            if result:
                print(f"✅ Fuente funcionando correctamente:")
                print(f"   Cotización: ${result['rate']}")
                print(f"   Fuente: {result['source']}")
                print(f"   Última actualización: {result.get('last_update', 'N/A')}")
            else:
                print("❌ La fuente no está disponible")
                
        except Exception as e:
            print(f"❌ Error probando fuente: {e}")

    def _load_local_preferences(self):
        """Carga preferencias locales (como fuente CCL preferida) desde un archivo simple."""
        try:
            prefs_file = Path('.prefs.json')
            if prefs_file.exists():
                import json
                data = json.load(open(prefs_file, 'r', encoding='utf-8'))
                preferred = data.get('PREFERRED_CCL_SOURCE')
                if preferred:
                    from app.config import settings as cfg
                    cfg.PREFERRED_CCL_SOURCE = preferred
        except Exception:
            pass

    def _save_local_preferences(self):
        """Guarda preferencias locales (como fuente CCL preferida) en un archivo simple."""
        try:
            import json
            from app.config import settings as cfg
            # Merge con .prefs.json existente, no sobrescribir otras claves
            prefs_path = Path('.').joinpath('.prefs.json')
            existing = {}
            if prefs_path.exists():
                try:
                    existing = json.loads(prefs_path.read_text(encoding='utf-8'))
                except Exception:
                    existing = {}
            existing['PREFERRED_CCL_SOURCE'] = cfg.PREFERRED_CCL_SOURCE
            prefs_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
    
    async def test_variation_analysis(self):
        """Análisis unificado de arbitraje para CEDEARs individuales"""
        print("\n📊 Análisis de Arbitraje de CEDEARs")
        print("=" * 50)
        print("Esta función analiza oportunidades de arbitraje para CEDEARs específicos")
        print("usando el mismo sistema unificado que el análisis de portfolio.")
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
            unified_analysis.set_iol_session(iol_session)  # Siempre configurar
            if iol_session:
                print("🔴 Modo: COMPLETO (IOL + Finnhub)")
            else:
                print("🟡 Modo: LIMITADO (BYMA + Finnhub)")
            
            # Crear un portfolio temporal con los símbolos solicitados
            from app.models.portfolio import Portfolio, Position
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
            analysis_result = await unified_analysis.analyze_portfolio(temp_portfolio, threshold=0.005)
            
            # Mostrar resultados
            summary_text = unified_analysis.format_analysis_summary(analysis_result)
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
                    alert_text = arbitrage_detector.format_alert(opp)
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
            from app.services.dollar_rate import dollar_service
            # Limpiar entradas conocidas del cache
            for key in ["ccl:dolarapi_ccl", "ccl:ccl_al30"]:
                dollar_service._cache.pop(key, None)
            # Traer nuevamente usando la preferencia
            from app.config import settings
            result = await dollar_service.get_ccl_rate(settings.PREFERRED_CCL_SOURCE)
            if result:
                print(f"✅ CCL actualizado: ${result['rate']:.2f} (fuente: {result.get('source_name', result.get('source'))})")
            else:
                print("❌ No se pudo refrescar CCL")
        except Exception as e:
            print(f"❌ Error refrescando CCL: {e}")

    def _read_prefs(self) -> dict:
        try:
            p = Path('.prefs.json')
            if p.exists():
                return json.load(open(p, 'r', encoding='utf-8'))
        except Exception:
            pass
        return {}

    def _write_prefs(self, data: dict) -> None:
        try:
            Path('.').joinpath('.prefs.json').write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"❌ No se pudo guardar .prefs.json: {e}")

async def main():
    """Función principal"""
    replicator = PortfolioReplicator()
    await replicator.run()

if __name__ == "__main__":
    asyncio.run(main())