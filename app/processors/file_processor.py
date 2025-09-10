import pandas as pd
import json
import asyncio
import os
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from ..models.portfolio import Portfolio, Position, ConvertedPortfolio
from .cedeares import CEDEARProcessor
# ❌ ELIMINADO: imports de servicios globales - migrar a DI cuando sea necesario
# from ..services.dollar_rate import dollar_service
# from ..services.arbitrage_detector import arbitrage_detector, ArbitrageOpportunity
# from ..services.variation_analyzer import variation_analyzer, CEDEARVariationAnalysis

from ..services.arbitrage_detector import ArbitrageOpportunity
from ..services.variation_analyzer import CEDEARVariationAnalysis

class PortfolioProcessor:
    def __init__(self, cedear_processor, dollar_service=None, arbitrage_detector=None, variation_analyzer=None, config=None, verbose=False, debug=False):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
            dollar_service: Servicio de cotización dólar (OPCIONAL)
            arbitrage_detector: Detector de arbitraje (OPCIONAL)
            variation_analyzer: Analizador de variaciones (OPCIONAL)
            config: Configuración del sistema (OPCIONAL - usa settings por defecto)
            verbose: Logging verbose para mapeo de columnas
            debug: Logging debug detallado
        """
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
            
        # Configurar Gemini (leer desde config o variables de entorno)
        gemini_api_key = None
        if config and hasattr(config, 'gemini_api_key'):
            gemini_api_key = config.gemini_api_key
        else:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            
        self.cedear_processor = cedear_processor
        self.dollar_service = dollar_service
        self.arbitrage_detector = arbitrage_detector
        self.variation_analyzer = variation_analyzer
        self.config = config
        self.verbose = verbose
        self.debug = debug
        
    
    async def process_file(self, file_path: str, broker: str = "Unknown") -> Portfolio:
        """Procesa un archivo Excel/CSV y devuelve un Portfolio"""
        print("📊 Leyendo archivo")
        
        # Detectar tipo de archivo por extensión
        file_extension = file_path.lower().split('.')[-1]
        
        try:
            if file_extension in ['xlsx', 'xls']:
                # Leer archivo Excel
                print("📋 Detectado archivo Excel - leyendo...")
                file = pd.read_excel(file_path)
                print(f"✅ Excel leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")
            else:
                # Leer archivo CSV con delimitador principal (cambio: , en lugar de ;)
                file = pd.read_csv(file_path, delimiter=',')
                print(f"✅ CSV leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")
            
            print(f"📋 Columnas encontradas: {list(file.columns)}")
            
        except Exception as e:
            if file_extension in ['xlsx', 'xls']:
                print(f"❌ Error leyendo Excel: {e}")
                raise Exception(f"No se pudo leer el archivo Excel: {e}")
            else:
                print(f"❌ Error leyendo CSV: {e}")
                print("🔄 Intentando con otros delimitadores...")
                
                # Intentar otros delimitadores para CSV (incluyendo ; como fallback)
                for delimiter in [';', '\t', '|']:
                    try:
                        file = pd.read_csv(file_path, delimiter=delimiter)
                        print(f"✅ CSV leído con delimitador '{delimiter}'. Filas: {len(file)}, Columnas: {len(file.columns)}")
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

        # Usar scanner directo de CEDEARs (sin headers) para TODOS los brokers
        print(f"🔍 Escaneando CEDEARs directamente en el archivo...")
        found_positions = self._find_cedeares_and_quantities(file, broker)
        
        if not found_positions:
            raise Exception(f"❌ No se encontraron CEDEARs con cantidades válidas en el archivo")
        
        print(f"🎯 Encontrados {len(found_positions)} CEDEARs con cantidades")

        print("🔄 Procesando CEDEARs encontrados...")
        
        # Crear lista de posiciones desde CEDEARs encontrados
        positions = []
        
        for cedear_data in found_positions:
            try:
                symbol = cedear_data['symbol']
                quantity = cedear_data['quantity']
                
                print(f"🔄 Procesando CEDEAR {symbol} (cantidad: {quantity})")
                
                # Verificar que sea CEDEAR (debería serlo siempre)
                is_cedear = self.cedear_processor.is_cedear(symbol)
                if not is_cedear:
                    print(f"⚠️  {symbol} - No es CEDEAR, saltando")
                    continue
                
                # Crear Position - solo symbol y quantity, price=None (se obtiene via API)
                position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    price=None,  # Precios via API
                    currency=getattr(self.config, 'DEFAULT_CURRENCY', 'ARS'),
                    is_cedear=is_cedear
                )
                
                # Agregar información de conversión
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
                print(f"❌ Error procesando CEDEAR {cedear_data}: {e}")
                continue

        print(f"✅ Procesamiento completado. {len(positions)} CEDEARs procesados")
        
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
        
        # Verificar disponibilidad de servicios
        if not self.arbitrage_detector:
            raise ValueError("arbitrage_detector no disponible - use build_services() para crear instancias completas")
        
        # Configurar detector con sesión IOL si está disponible
        if iol_session:
            self.arbitrage_detector.set_iol_session(iol_session)
            print("🔴 Modo COMPLETO: Usando precios en tiempo real desde IOL")
        else:
            self.arbitrage_detector.set_iol_session(None)
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
        opportunities = await self.arbitrage_detector.detect_portfolio_arbitrages(
            cedear_symbols, 
            threshold_percentage
        )
        
        # Mostrar resultados
        if opportunities:
            print(f"\n🚨 {len(opportunities)} OPORTUNIDADES DE ARBITRAJE DETECTADAS:")
            print("=" * 60)
            
            for opp in opportunities:
                print(self.arbitrage_detector.format_alert(opp))
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
        
        # Verificar disponibilidad de servicios
        if not self.variation_analyzer:
            raise ValueError("variation_analyzer no disponible - use build_services() para crear instancias completas")
        
        try:
            # Configurar el analizador con la sesión IOL si está disponible
            if iol_session:
                self.variation_analyzer.set_iol_session(iol_session)
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
            analyses = await self.variation_analyzer.analyze_portfolio_variations(cedear_list)
            
            if analyses:
                print(f"\n📈 RESUMEN DE VARIACIONES:")
                print(self.variation_analyzer.format_variation_report(analyses))
                
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
        """Convierte números en cualquier formato a estándar, eliminando texto/monedas."""
        if not value or value.strip() == '':
            return 0.0
        
        import re
        
        # Eliminar CUALQUIER texto, monedas, símbolos: USD, ARS, $, %, etc.
        # Mantener solo dígitos, comas, puntos y signos negativos
        clean_value = re.sub(r'[^\d,.-]', '', str(value).strip())
        
        if not clean_value:
            if self.debug:
                print(f"⚠️  Valor sin números detectables: '{value}'")
            return 0.0
        
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
            result = float(clean_value)
            if self.debug and str(value) != str(result):
                print(f"🔄 Número limpiado: '{value}' → {result}")
            return result
        except ValueError:
            if self.debug:
                print(f"⚠️  No se pudo convertir a número: '{value}' → '{clean_value}'")
            return 0.0
    
    
    async def _get_dollar_rate(self) -> Optional[Dict[str, Any]]:
        """Obtiene la cotización del dólar CCL usando la fuente configurada"""
        if not self.dollar_service:
            print("⚠️  Dollar service no disponible - usando tasa por defecto")
            return {"rate": 1000.0, "source": "default", "fallback_used": True}
            
        try:
            preferred_source = self.config.preferred_ccl_source if self.config else "dolarapi_ccl"
            print(f"💱 Usando fuente CCL configurada: {preferred_source}")
            return await self.dollar_service.get_ccl_rate(preferred_source)
        except Exception as e:
            print(f"❌ Error obteniendo cotización del dólar: {e}")
            return {"rate": 1000.0, "source": "fallback", "fallback_used": True}
    
    def _get_broker_column_mapping(self, dataframe, broker: str) -> Dict[str, str]:
        """
        Mapeo de columnas basado en broker conocido
        """
        available_columns = list(dataframe.columns)
        broker_lower = broker.lower()
        
        # Mapeos conocidos por broker
        if "cocos" in broker_lower:
            return self._map_cocos_format(available_columns)
        elif "bull" in broker_lower or "market" in broker_lower:
            return self._map_bullmarket_format(available_columns)
        else:
            # Formato estándar para brokers desconocidos
            return self._map_standard_format(available_columns)
    
    def _map_cocos_format(self, columns: List[str]) -> Dict[str, str]:
        """Mapeo para formato Cocos Capital"""
        mapping = {}
        
        # Formato conocido: instrumento,cantidad,precio,moneda,total
        if "instrumento" in columns:
            mapping["symbol"] = "instrumento"
            print("✅ Cocos: symbol → 'instrumento'")
        
        if "cantidad" in columns:
            mapping["quantity"] = "cantidad"
            print("✅ Cocos: quantity → 'cantidad'")
        
        # Opcionales
        if "precio" in columns:
            mapping["price"] = "precio"
        if "moneda" in columns:
            mapping["currency"] = "moneda"
        
        # Validar campos requeridos
        if "symbol" not in mapping or "quantity" not in mapping:
            raise Exception(f"❌ Formato Cocos incompleto. Se esperaba 'instrumento' y 'cantidad'. Disponible: {columns}")
        
        return mapping
    
    def _map_bullmarket_format(self, columns: List[str]) -> Dict[str, str]:
        """
        Mapeo para Bull Market.
        Formato: Producto | Cantidad | Ultimo Precio | Var % Diaria | Var $ Diaria | PPC | Gan-Per % | Gan.-Per $ | Total
        - Producto: contiene ticker como primera palabra (ej: "AAPL\nCEDEAR APPLE INC")
        - Cantidad: cantidad nominal
        """
        mapping = {}
        
        # Buscar columnas (case-insensitive)
        columns_lower = [col.lower() for col in columns]
        
        if "producto" in columns_lower:
            mapping["symbol"] = columns[columns_lower.index("producto")]
        
        if "cantidad" in columns_lower:
            mapping["quantity"] = columns[columns_lower.index("cantidad")]
            
        # Solo symbol y quantity requeridos - NO parseamos precios
        
        # Validar campos requeridos
        if "symbol" not in mapping or "quantity" not in mapping:
            raise Exception(f"❌ Formato Bull Market incompleto. Se esperaba 'producto' y 'cantidad'. Disponible: {columns}")
            
        print(f"✅ Bull Market: symbol → '{mapping['symbol']}'")
        print(f"✅ Bull Market: quantity → '{mapping['quantity']}'")
        print("💡 Bull Market: solo symbol+quantity (precios via API)")
            
        return mapping
    
    def _find_cedeares_and_quantities(self, dataframe, broker: str) -> List[Dict]:
        """
        Escanea TODO el archivo buscando CEDEARs y sus cantidades adyacentes.
        NO busca headers - va directo a los datos.
        """
        known_cedeares = {cedear["symbol"].upper() for cedear in self.cedear_processor.get_all_cedeares()}
        
        if self.debug:
            print(f"🔍 Escaneando {len(known_cedeares)} CEDEARs conocidos...")
        
        found_positions = []
        
        for row_idx in range(len(dataframe)):
            for col_idx in range(len(dataframe.columns)):
                try:
                    cell_value = dataframe.iloc[row_idx, col_idx]
                    
                    if pd.notna(cell_value) and str(cell_value).strip():
                        # Extraer ticker según formato
                        ticker = self._extract_ticker(str(cell_value), broker)
                        
                        if ticker and ticker in known_cedeares:
                            # Buscar cantidad en celdas adyacentes
                            quantity = self._find_quantity_nearby(dataframe, row_idx, col_idx)
                            
                            if quantity > 0:
                                # Verificar si ya existe este CEDEAR (evitar duplicados)
                                if not any(pos['symbol'] == ticker for pos in found_positions):
                                    found_positions.append({
                                        'symbol': ticker,
                                        'quantity': quantity
                                    })
                                    if self.debug:
                                        print(f"🎯 {ticker} encontrado en ({row_idx+1}, {col_idx+1}) con cantidad {quantity}")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️  Error en celda ({row_idx+1}, {col_idx+1}): {e}")
                    continue
        
        return found_positions
    
    def _extract_ticker(self, cell_value: str, broker: str) -> str:
        """Extrae ticker de una celda según el formato del broker."""
        cell_str = str(cell_value).strip()
        
        if "bull" in broker.lower() or "market" in broker.lower():
            # Para Bull Market: "AAPL\nCEDEAR APPLE INC" → "AAPL"
            lines = cell_str.split('\n')
            if lines:
                first_line = lines[0].strip()
                ticker = first_line.split()[0] if first_line.split() else ""
                return ticker.upper()
        else:
            # Para otros formatos, extraer ticker directamente
            return self._clean_symbol(cell_str)
        
        return ""
    
    def _find_quantity_nearby(self, dataframe, row_idx: int, col_idx: int) -> float:
        """Busca cantidad en celdas adyacentes (misma fila, columnas cercanas)."""
        # Buscar en misma fila, columnas a la derecha (máximo 5 columnas)
        for offset in range(1, min(6, len(dataframe.columns) - col_idx)):
            try:
                cell_value = dataframe.iloc[row_idx, col_idx + offset]
                if pd.notna(cell_value) and str(cell_value).strip():
                    quantity = self._clean_number(str(cell_value))
                    if quantity > 0:
                        if self.debug:
                            print(f"🔢 Cantidad {quantity} encontrada en offset +{offset}")
                        return quantity
            except Exception:
                continue
        
        # Si no encuentra a la derecha, buscar en columnas a la izquierda
        for offset in range(1, min(4, col_idx + 1)):
            try:
                cell_value = dataframe.iloc[row_idx, col_idx - offset]
                if pd.notna(cell_value) and str(cell_value).strip():
                    quantity = self._clean_number(str(cell_value))
                    if quantity > 0:
                        if self.debug:
                            print(f"🔢 Cantidad {quantity} encontrada en offset -{offset}")
                        return quantity
            except Exception:
                continue
        
        return 0.0
    
    def _find_cedear_range(self, dataframe, broker: str) -> tuple:
        """
        Encuentra el rango completo de CEDEARs y determina headers dinámicamente.
        Usa DI: self.cedear_processor para obtener CEDEARs conocidos.
        
        Returns:
            tuple: (header_row_idx, data_start_row_idx, data_end_row_idx)
        """
        # Obtener todos los símbolos CEDEAR conocidos via DI
        known_cedeares = {cedear["symbol"].upper() for cedear in self.cedear_processor.get_all_cedeares()}
        
        if self.debug:
            print(f"🔍 Escaneando rango completo de CEDEARs en {len(known_cedeares)} símbolos conocidos...")
        
        # Buscar todas las filas que contienen CEDEARs
        cedear_rows = []
        for row_idx in range(len(dataframe)):
            if self._row_contains_cedear(dataframe.iloc[row_idx], known_cedeares, broker):
                cedear_rows.append(row_idx)
                if self.debug:
                    print(f"🎯 CEDEAR en fila {row_idx + 1}")
        
        if not cedear_rows:
            raise Exception(f"❌ No se detectaron CEDEARs conocidos en el archivo {broker}")
        
        # Determinar rango de datos
        data_start_row = min(cedear_rows)
        data_end_row = max(cedear_rows)
        
        print(f"📍 Rango de CEDEARs: filas {data_start_row + 1} a {data_end_row + 1} ({len(cedear_rows)} CEDEARs)")
        
        # Buscar headers hacia arriba desde el primer CEDEAR
        header_row = self._find_header_above(dataframe, data_start_row, broker)
        
        return header_row, data_start_row, data_end_row
    
    def _row_contains_cedear(self, row, known_cedeares: set, broker: str) -> bool:
        """Verifica si una fila contiene algún CEDEAR conocido."""
        for cell_value in row:
            if pd.notna(cell_value) and str(cell_value).strip():
                cell_str = str(cell_value).strip()
                
                # Para Bull Market: extraer primer token de "AAPL\nCEDEAR APPLE"
                if "bull" in broker.lower() or "market" in broker.lower():
                    potential_ticker = cell_str.split('\n')[0].split()[0].upper() if cell_str else ""
                else:
                    # Para otros formatos, tomar el valor directo
                    potential_ticker = cell_str.upper()
                
                if potential_ticker in known_cedeares:
                    return True
        return False
    
    def _find_header_above(self, dataframe, data_start_row: int, broker: str) -> int:
        """Busca headers hacia arriba desde la primera fila de datos."""
        # Términos de búsqueda según broker
        if "bull" in broker.lower() or "market" in broker.lower():
            search_terms = ["producto", "cantidad"]
        elif "cocos" in broker.lower():
            search_terms = ["instrumento", "cantidad"]
        else:
            search_terms = ["symbol", "quantity"]
        
        # Buscar hacia arriba hasta 5 filas
        for offset in range(1, min(6, data_start_row + 1)):
            header_row_idx = data_start_row - offset
            header_candidates = dataframe.iloc[header_row_idx].astype(str).str.lower()
            
            # Verificar si contiene los términos esperados
            terms_found = sum(1 for term in search_terms if any(term in str(val) for val in header_candidates))
            
            if terms_found >= len(search_terms):  # Debe tener todos los términos
                print(f"📍 Headers encontrados en fila {header_row_idx + 1} (términos: {search_terms})")
                return header_row_idx
        
        # Fallback: usar fila inmediatamente anterior
        fallback_row = max(0, data_start_row - 1)
        print(f"⚠️  Headers no encontrados, usando fila {fallback_row + 1} como fallback")
        return fallback_row
    
    def _extract_bullmarket_ticker(self, raw_product: str) -> str:
        """
        Extrae el ticker de la columna 'Producto' de Bull Market.
        Formato esperado: 
        'AAPL\nCEDEAR APPLE INC' -> 'AAPL'
        'AMZN\nCEDEAR AMAZON.COM, INC' -> 'AMZN'
        """
        if not raw_product:
            return ""
            
        # Dividir por salto de línea y tomar la primera palabra
        lines = raw_product.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # Tomar la primera palabra (el ticker)
            ticker = first_line.split()[0] if first_line.split() else ""
            
            if self.debug:
                print(f"🔄 Bull Market ticker extraído: '{raw_product}' -> '{ticker}'")
            
            return ticker
        
        return ""
    
    def _map_standard_format(self, columns: List[str]) -> Dict[str, str]:
        """Mapeo para formato estándar: symbol,quantity"""
        mapping = {}
        
        if "symbol" in columns:
            mapping["symbol"] = "symbol"
            print("✅ Estándar: symbol → 'symbol'")
        
        if "quantity" in columns:
            mapping["quantity"] = "quantity"
            print("✅ Estándar: quantity → 'quantity'")
        
        # Validar campos requeridos
        if "symbol" not in mapping or "quantity" not in mapping:
            print("❌ Formato estándar requerido:")
            print("📋 Columnas esperadas: 'symbol', 'quantity'")
            print(f"📋 Columnas disponibles: {columns}")
            raise Exception("Use formato estándar: CSV con columnas 'symbol,quantity'")
        
        return mapping
    