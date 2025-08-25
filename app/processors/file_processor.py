import pandas as pd
import json
import asyncio
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from ..config import settings
from ..models.portfolio import Portfolio, Position, ConvertedPortfolio
from .cedeares import CEDEARProcessor
from ..services.dollar_rate import dollar_service
from ..services.arbitrage_detector import arbitrage_detector, ArbitrageOpportunity
from ..services.variation_analyzer import variation_analyzer, CEDEARVariationAnalysis

class PortfolioProcessor:
    def __init__(self):
        # Configurar Gemini
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
        self.cedear_processor = CEDEARProcessor()
    
    async def process_file(self, file_path: str, broker: str = "Unknown") -> Portfolio:
        """Procesa un archivo Excel/CSV y devuelve un Portfolio"""
        print("📊 Leyendo archivo")
        
        try:
            # Leer archivo
            file = pd.read_csv(file_path, delimiter=';')
            print(f"✅ Archivo leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")
            print(f"📋 Columnas encontradas: {list(file.columns)}")
            
        except Exception as e:
            print(f"❌ Error leyendo archivo: {e}")
            print("🔄 Intentando con otros delimitadores...")
            
            # Intentar otros delimitadores
            for delimiter in [',', '\t', '|']:
                try:
                    file = pd.read_csv(file_path, delimiter=delimiter)
                    print(f"✅ Archivo leído con delimitador '{delimiter}'. Filas: {len(file)}, Columnas: {len(file.columns)}")
                    print(f"📋 Columnas encontradas: {list(file.columns)}")
                    break
                except Exception as inner_e:
                    print(f"❌ Falló con delimitador '{delimiter}': {inner_e}")
                    continue
            else:
                raise Exception("No se pudo leer el archivo con ningún delimitador")

        # Mostrar las primeras filas para debugging
        print("\n📋 Primeras 3 filas del archivo:")
        print(file.head(3).to_string())
        print()

        try:
            # Obtener mapeo de columnas usando Gemini
            print("🤖 Consultando Gemini para mapear columnas...")
            column_mapping = self._get_column_mapping(file.columns.tolist(), broker)
            print(f"📊 Mapeo de columnas: {column_mapping}")
        except Exception as e:
            print(f"⚠️ Error con Gemini: {e}")
            print("🔄 Usando mapeo manual de respaldo...")
            # Mapeo manual de respaldo para Cocos
            column_mapping = {
                "symbol": "instrumento",
                "quantity": "cantidad",
                "price": "precio",
                "currency": "moneda"
            }
            print(f"📊 Mapeo manual: {column_mapping}")

        # Verificar que las columnas mapeadas existen
        missing_columns = []
        for key, col_name in column_mapping.items():
            if col_name not in file.columns:
                missing_columns.append(col_name)
        
        if missing_columns:
            print(f"❌ Columnas faltantes: {missing_columns}")
            print(f"📋 Columnas disponibles: {list(file.columns)}")
            raise Exception(f"No se encontraron las columnas: {missing_columns}")

        print("🔄 Procesando filas...")
        
        # Crear lista de posiciones
        positions = []
        processed_rows = 0
        
        for index, row in file.iterrows():
            try:
                processed_rows += 1
                print(f"🔄 Procesando fila {processed_rows}/{len(file)}")
                
                # Preprocesamiento automático de datos
                raw_symbol = str(row[column_mapping["symbol"]]).strip()
                raw_quantity = str(row[column_mapping["quantity"]])
                raw_price = str(row[column_mapping["price"]])
                raw_currency = str(row[column_mapping["currency"]]).strip()
                
                print(f"📊 Datos raw: symbol='{raw_symbol}', quantity='{raw_quantity}', price='{raw_price}', currency='{raw_currency}'")
                
                symbol = self._clean_symbol(raw_symbol)
                quantity = self._clean_number(raw_quantity)
                price = self._clean_number(raw_price)
                currency = raw_currency
                
                print(f"📊 Datos limpios: symbol='{symbol}', quantity={quantity}, price={price}, currency='{currency}'")
                
                # Saltar filas inválidas (solo verificamos symbol y quantity)
                if not self._is_valid_row(symbol, quantity, price, currency):
                    print(f"⚠️  Saltando fila inválida: {symbol}")
                    continue
                
                # Verificar si es un CEDEAR
                is_cedear = self.cedear_processor.is_cedear(symbol)
                print(f"📊 ¿Es CEDEAR? {is_cedear}")
                
                # Crear Position sin price del archivo - será obtenido desde fuentes estandarizadas
                position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    price=None,  # Ignoramos price del archivo para estandarizar fuentes
                    currency=currency,
                    is_cedear=is_cedear
                )
                
                # Si es CEDEAR, agregar información de conversión
                if is_cedear:
                    try:
                        print(f"🔄 Convirtiendo CEDEAR {symbol}...")
                        underlying_symbol, underlying_quantity = self.cedear_processor.convert_cedear_to_underlying(
                            symbol, position.quantity
                        )
                        underlying_info = self.cedear_processor.get_underlying_asset(symbol)
                        
                        position.underlying_symbol = underlying_symbol
                        position.underlying_quantity = underlying_quantity
                        position.conversion_ratio = self.cedear_processor.parse_ratio(underlying_info["ratio"])
                        print(f"✅ CEDEAR convertido: {underlying_symbol} x{underlying_quantity}")
                    except Exception as e:
                        # Si hay error en la conversión, mantener la posición original
                        print(f"⚠️ Error convirtiendo CEDEAR {symbol}: {e}")
                
                positions.append(position)
                print(f"✅ Posición agregada: {symbol}")
                
            except Exception as e:
                print(f"❌ Error procesando fila {processed_rows}: {e}")
                print(f"📊 Datos de la fila: {row.to_dict()}")
                # Continuar con la siguiente fila en lugar de fallar completamente
                continue

        print(f"✅ Procesamiento completado. {len(positions)} posiciones válidas de {len(file)} filas")
        
        # Obtener cotización del dólar para posiciones USD
        usd_positions = [p for p in positions if p.currency.upper() == 'USD']
        if usd_positions:
            print(f"\n💱 Obteniendo cotización CCL para {len(usd_positions)} posiciones en USD...")
            dollar_rate = await self._get_dollar_rate()
            
            if dollar_rate:
                print(f"✅ Cotización CCL obtenida: ${dollar_rate['rate']} (fuente: {dollar_rate['source']})")
                
                # Agregar información del dólar a las posiciones USD
                for position in usd_positions:
                    position.dollar_rate = dollar_rate['rate']
                    position.dollar_source = dollar_rate['source']
                    position.total_value_ars = position.total_value * dollar_rate['rate']
                    print(f"📊 {position.symbol}: USD ${position.total_value} = ARS ${position.total_value_ars:,.0f}")
            else:
                print("⚠️  No se pudo obtener cotización del dólar - valores en ARS no disponibles")
        
        return Portfolio(
            broker=broker,
            positions=positions
        )
    
    def convert_portfolio_to_underlying(self, portfolio: Portfolio) -> ConvertedPortfolio:
        """Convierte un portfolio a sus activos subyacentes."""
        converted_positions = []
        conversion_summary = {
            "total_cedeares": 0,
            "converted_assets": 0,
            "errors": []
        }
        
        for position in portfolio.positions:
            if position.is_cedear and position.underlying_symbol:
                # Crear posición convertida
                converted_position = Position(
                    symbol=position.underlying_symbol,
                    quantity=position.underlying_quantity,
                    price=position.price,  # Mantener precio original por ahora
                    currency=position.currency,
                    is_cedear=False
                )
                converted_positions.append(converted_position)
                conversion_summary["total_cedeares"] += 1
                conversion_summary["converted_assets"] += 1
            else:
                # Mantener posición original si no es CEDEAR
                converted_positions.append(position)
                if not position.is_cedear:
                    conversion_summary["converted_assets"] += 1
        
        return ConvertedPortfolio(
            original_positions=portfolio.positions,
            converted_positions=converted_positions,
            broker=portfolio.broker,
            conversion_summary=conversion_summary
        )
    
    async def detect_arbitrage_opportunities(self, portfolio: Portfolio, iol_session=None, threshold_percentage: float = 0.005) -> List[ArbitrageOpportunity]:
        """
        Detecta oportunidades de arbitraje en un portfolio
        
        Args:
            portfolio: Portfolio a analizar
            iol_session: Sesión de IOL para modo completo (opcional)
            threshold_percentage: Umbral mínimo para considerar arbitraje (default: 0.5%)
            
        Returns:
            Lista de oportunidades de arbitraje detectadas
        """
        
        print(f"\n🔍 Analizando oportunidades de arbitraje (threshold: {threshold_percentage:.1%})...")
        
        # Configurar detector con sesión IOL si está disponible
        if iol_session:
            arbitrage_detector.set_iol_session(iol_session)
            print("🔴 Modo COMPLETO: Usando precios en tiempo real desde IOL")
        else:
            arbitrage_detector.set_iol_session(None)
            print("🟡 Modo LIMITADO: Usando precios BYMA + fallback Yahoo Finance .BA")
        
        # Obtener símbolos de CEDEARs del portfolio
        cedear_symbols = []
        for position in portfolio.positions:
            if position.is_cedear and position.underlying_symbol:
                cedear_symbols.append(position.underlying_symbol)
        
        if not cedear_symbols:
            print("ℹ️  No se encontraron CEDEARs en el portfolio para analizar")
            return []
        
        print(f"📊 Analizando {len(cedear_symbols)} CEDEARs: {cedear_symbols}")
        
        # Detectar arbitrajes
        opportunities = await arbitrage_detector.detect_portfolio_arbitrages(
            cedear_symbols, 
            threshold_percentage
        )
        
        # Mostrar resultados
        if opportunities:
            print(f"\n🚨 {len(opportunities)} OPORTUNIDADES DE ARBITRAJE DETECTADAS:")
            print("=" * 60)
            
            for opp in opportunities:
                print(arbitrage_detector.format_alert(opp))
                print()
        else:
            print(f"\n✅ No se detectaron oportunidades de arbitraje superiores al {threshold_percentage:.1%}")
        
        return opportunities
    
    async def analyze_portfolio_variations(self, portfolio: Portfolio, iol_session=None) -> List[CEDEARVariationAnalysis]:
        """
        Analiza las variaciones diarias de los CEDEARs en el portfolio
        
        Args:
            portfolio: Portfolio convertido con CEDEARs
            iol_session: Sesión IOL para modo completo (opcional)
            
        Returns:
            Lista de análisis de variaciones
        """
        
        print("\n📊 Iniciando análisis de variaciones diarias...")
        
        try:
            # Configurar el analizador con la sesión IOL si está disponible
            if iol_session:
                variation_analyzer.set_iol_session(iol_session)
                print("🔴 Modo: TIEMPO REAL (con IOL)")
            else:
                print("🟡 Modo: TEÓRICO/BYMA (sin IOL)")
            
            # Extraer símbolos de CEDEARs únicos del portfolio
            cedear_symbols = set()
            
            for position in portfolio.positions:
                if self.cedear_processor.is_cedear(position.symbol):
                    cedear_symbols.add(position.symbol)
            
            cedear_list = list(cedear_symbols)
            
            if not cedear_list:
                print("⚠️  No se encontraron CEDEARs en el portfolio")
                return []
            
            print(f"🔍 Analizando variaciones para {len(cedear_list)} CEDEARs únicos: {cedear_list}")
            
            # Realizar análisis de variaciones
            analyses = await variation_analyzer.analyze_portfolio_variations(cedear_list)
            
            if analyses:
                print(f"\n📈 RESUMEN DE VARIACIONES:")
                print(variation_analyzer.format_variation_report(analyses))
                
                # Identificar casos interesantes
                significant_variations = [
                    a for a in analyses 
                    if abs(a.var_extra) >= 0.02  # 2% threshold
                ]
                
                if significant_variations:
                    print(f"\n🚨 {len(significant_variations)} CEDEARs con variaciones significativas:")
                    for analysis in significant_variations:
                        print(f"   • {analysis.symbol}: {analysis.var_extra:+.1%} ({analysis.interpret_variation()})")
                else:
                    print(f"\n✅ Todos los CEDEARs muestran variaciones normales")
            else:
                print("❌ No se pudieron completar los análisis de variaciones")
            
            return analyses
            
        except Exception as e:
            print(f"❌ Error en análisis de variaciones: {str(e)}")
            return []
    
    def _get_column_mapping(self, columns: list, broker: str) -> dict:
        """Usa Gemini para mapear las columnas del archivo"""
        prompt = f"""
        Este es un Excel/CSV de tenencias de {broker if broker else 'un broker'}.
        Por favor, identifica las columnas que contienen:
        - Símbolo del activo
        - Cantidad
        - Precio
        - Moneda

        El archivo tiene estas columnas:
        {columns}

        Devuelve un JSON con el mapeo de columnas en este formato:
        {{
            "symbol": "nombre_columna_simbolo",
            "quantity": "nombre_columna_cantidad", 
            "price": "nombre_columna_precio",
            "currency": "nombre_columna_moneda"
        }}
        """
        
        if self.model:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Limpiar respuesta de markdown si es necesario
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            return json.loads(response_text)
        else:
            raise Exception("Modelo Gemini no disponible")

    def _clean_symbol(self, symbol: str) -> str:
        """Limpia y extrae el código del símbolo de manera genérica."""
        if not symbol or symbol.lower() in ['ars', 'usd', 'moneda', 'currency']:
            return ""
        
        import re
        
        # Intentar extraer códigos de diferentes formatos
        # 1. Códigos entre paréntesis: 'CEDEAR TESLA, INC. (TSLA)' -> 'TSLA'
        match = re.search(r'\(([A-Z0-9]+)\)', symbol)
        if match:
            return match.group(1)
        
        # 2. Códigos al final: 'TESLA TSLA' -> 'TSLA'
        words = symbol.split()
        if len(words) >= 2:
            last_word = words[-1]
            if re.match(r'^[A-Z0-9]{2,6}$', last_word):
                return last_word
        
        # 3. Códigos al principio: 'TSLA TESLA INC' -> 'TSLA'
        if len(words) >= 1:
            first_word = words[0]
            if re.match(r'^[A-Z0-9]{2,6}$', first_word):
                return first_word
        
        # 4. Extraer solo letras/números: 'AAPL' -> 'AAPL'
        clean_symbol = re.sub(r'[^A-Z0-9]', '', symbol.upper())
        if len(clean_symbol) >= 2 and len(clean_symbol) <= 6:
            return clean_symbol
        
        # 5. Si nada funciona, devolver el símbolo original limpio
        return re.sub(r'[^A-Z0-9]', '', symbol.upper())
    
    def _clean_number(self, value: str) -> float:
        """Convierte números en formato europeo a estándar."""
        if not value or value.strip() == '':
            return 0.0
        
        # Limpiar espacios y caracteres extra
        clean_value = value.strip().replace(' ', '')
        
        # Manejar formato europeo (comas como separador decimal)
        if ',' in clean_value and '.' in clean_value:
            # Si tiene ambos, la coma es separador de miles
            clean_value = clean_value.replace(',', '')
        elif ',' in clean_value and clean_value.count(',') == 1:
            # Si tiene una coma, puede ser separador decimal
            # Verificar si es formato europeo
            parts = clean_value.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Probablemente formato europeo (ej: 1234,56)
                clean_value = clean_value.replace(',', '.')
        
        # Convertir a float
        try:
            return float(clean_value)
        except ValueError:
            print(f"⚠️  No se pudo convertir a número: {value}")
            return 0.0
    
    def _is_valid_row(self, symbol: str, quantity: float, price: float, currency: str) -> bool:
        """Verifica si una fila es válida para procesar."""
        # Símbolo debe existir y no ser vacío
        if not symbol or symbol.strip() == '':
            return False
        
        # Cantidad debe ser positiva
        if quantity <= 0:
            return False
        
        # Precio debe ser positivo
        if price <= 0:
            return False
        
        # Moneda debe ser válida
        valid_currencies = ['ARS', 'USD', 'ars', 'usd']
        if currency.upper() not in [c.upper() for c in valid_currencies]:
            return False
        
        return True
    
    async def _get_dollar_rate(self) -> Optional[Dict[str, Any]]:
        """Obtiene la cotización del dólar CCL usando la fuente configurada"""
        try:
            preferred_source = settings.PREFERRED_CCL_SOURCE
            print(f"💱 Usando fuente CCL configurada: {preferred_source}")
            return await dollar_service.get_ccl_rate(preferred_source)
        except Exception as e:
            print(f"❌ Error obteniendo cotización del dólar: {e}")
            return None 