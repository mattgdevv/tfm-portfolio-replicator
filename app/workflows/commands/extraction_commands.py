"""
ETL Extraction Commands
Comandos para extracción de datos desde diferentes fuentes (IOL, Excel/CSV)
"""

import asyncio
from getpass import getpass
from app.core.services import Services
from app.models.portfolio import Portfolio


class ExtractionCommands:
    """Comandos de extracción de datos para el pipeline ETL"""
    
    def __init__(self, services: Services, iol_integration, portfolio_processor):
        """
        Constructor con dependency injection
        
        Args:
            services: Container de servicios DI
            iol_integration: Integración IOL ya configurada
            portfolio_processor: Procesador de portfolios
        """
        self.services = services
        self.iol_integration = iol_integration
        self.portfolio_processor = portfolio_processor
    
    async def extract_iol_portfolio(self) -> Portfolio:
        """
        Extrae portfolio desde IOL con autenticación
        
        Returns:
            Portfolio: Portfolio extraído desde IOL
        """
        print("\n📊 Obteniendo portfolio desde IOL...")
        print("Nota: Presiona ESPACIO + Enter para volver al menú principal")
        
        try:
            # Loop principal para credenciales
            while True:
                # Solicitar credenciales con validación obligatoria
                while True:
                    username_input = input("Usuario IOL: ")
                    username = username_input.strip()
                    
                    # Si presiona espacio, cancelar
                    if username_input == " " or (not username and username_input):
                        print("⬅️  Volviendo al menú principal...")
                        return None
                    
                    if username:
                        break
                    print("⚠️  Usuario requerido. Intente de nuevo.")
                
                while True:
                    password_input = getpass("Contraseña IOL: ")
                    password = password_input.strip()
                    
                    # Si presiona espacio, cancelar
                    if password_input == " " or (not password and password_input):
                        print("⬅️  Volviendo al menú principal...")
                        return None
                    
                    if password:
                        break
                    print("⚠️  Contraseña requerida. Intente de nuevo.")
                
                # Autenticar con IOL
                print("🔐 Autenticando con IOL...")
                try:
                    await self.iol_integration.authenticate(username, password)
                    break  # Si llega aquí, la autenticación fue exitosa
                except Exception as e:
                    if "401" in str(e) or "Unauthorized" in str(e):
                        print(f"❌ Credenciales incorrectas para usuario: {username}")
                        print("🔄 Intente de nuevo...")
                    else:
                        print(f"❌ Error de autenticación: {e}")
                        return None
            
            # Obtener portfolio
            print("📈 Obteniendo portfolio...")
            portfolio = await self.iol_integration.get_portfolio()
            print(f"✅ Portfolio extraído exitosamente con {len(portfolio.positions)} posiciones")
            
            return portfolio
            
        except Exception as e:
            print(f"❌ Error extrayendo portfolio IOL: {e}")
            return None
    
    async def extract_file_portfolio(self) -> Portfolio:
        """
        Extrae portfolio desde archivo Excel/CSV
        
        Returns:
            Portfolio: Portfolio extraído desde archivo
        """
        try:
            print("\n📄 Cargando portfolio desde archivo...")
            
            # Usar el FileProcessingService existente
            portfolio = await self.services.file_processing_service.handle_excel_portfolio()
            
            if portfolio and len(portfolio.positions) > 0:
                print(f"✅ Portfolio extraído exitosamente con {len(portfolio.positions)} posiciones")
                return portfolio
            else:
                print("❌ No se pudo procesar el archivo o está vacío")
                return None
                
        except Exception as e:
            print(f"❌ Error extrayendo portfolio desde archivo: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def process_extracted_portfolio(self, portfolio: Portfolio, source: str) -> tuple:
        """
        Procesa un portfolio extraído (display + conversión)
        
        Args:
            portfolio: Portfolio a procesar
            source: Fuente del portfolio ("IOL" o "Excel/CSV")
            
        Returns:
            tuple: (cedeares_count, converted_portfolio)
        """
        if not portfolio:
            return 0, None
        
        try:
            # Procesar y mostrar resultados usando servicio existente
            cedeares_count = await self.services.portfolio_display_service.process_and_show_portfolio(
                portfolio, source
            )
            
            # Convertir CEDEARs si los hay
            converted = None
            if cedeares_count > 0:
                print(f"\n🔄 Convirtiendo {cedeares_count} CEDEARs a subyacentes...")
                converted = self.portfolio_processor.convert_portfolio_to_underlying(portfolio)
                print("✅ Conversión completada: {} CEDEARs convertidos".format(
                    len(converted.converted_positions) if converted else 0
                ))
            
            print(f"\n📊 Portfolio procesado exitosamente con {len(portfolio.positions)} posiciones")
            return cedeares_count, converted
            
        except Exception as e:
            print(f"❌ Error procesando portfolio: {e}")
            return 0, None
