#!/usr/bin/env python3
"""
Script para descargar y procesar el PDF de CEDEARs de BYMA
"""

import requests
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import urllib3
from datetime import datetime
from bs4 import BeautifulSoup

# Suprimir warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BYMAPDFProcessor:
    def __init__(self):
        # URL base de la página de CEDEARs - obtendremos la URL del PDF dinámicamente
        self.cedeares_page_url = "https://www.byma.com.ar/productos/productos-financieros/cedears"
        self.pdf_url = None  # Se obtendrá dinámicamente
        self.output_file = "byma_cedeares_pdf.json"
        
    def get_latest_pdf_url(self) -> Optional[str]:
        """Obtiene la URL del PDF más reciente desde la página de BYMA"""
        try:
            print(f"🔍 Buscando URL del PDF en: {self.cedeares_page_url}")
            
            # Hacer request a la página
            response = requests.get(self.cedeares_page_url, verify=False)
            response.raise_for_status()
            
            # Buscar URLs que contengan el patrón del PDF de CEDEARs
            # Patrón: BYMA-Tabla-CEDEARs-YYYY-MM-DD.pdf
            pattern = r'https://cdn\.prod\.website-files\.com/[^"]*BYMA-Tabla-CEDEARs-\d{4}-\d{2}-\d{2}\.pdf'
            
            matches = re.findall(pattern, response.text)
            
            if matches:
                # Tomar la primera URL encontrada (debería ser la más reciente)
                latest_url = matches[0]
                print(f"✅ PDF encontrado: {latest_url}")
                
                # Extraer fecha del PDF para mostrar al usuario
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', latest_url)
                if date_match:
                    pdf_date = date_match.group(1)
                    print(f"📅 Fecha del PDF: {pdf_date}")
                
                return latest_url
            else:
                print("❌ No se encontró URL del PDF en la página")
                # Fallback a URL conocida si no encontramos nada
                fallback_url = "https://cdn.prod.website-files.com/6697a441a50c6b926e1972e0/68b86fe690fbf91e42c75e90_BYMA-Tabla-CEDEARs-2025-09-03.pdf"
                print(f"⚠️  Usando URL fallback: {fallback_url}")
                return fallback_url
                
        except Exception as e:
            print(f"❌ Error obteniendo URL del PDF: {e}")
            # Fallback a URL conocida
            fallback_url = "https://cdn.prod.website-files.com/6697a441a50c6b926e1972e0/68b86fe690fbf91e42c75e90_BYMA-Tabla-CEDEARs-2025-09-03.pdf"
            print(f"⚠️  Usando URL fallback: {fallback_url}")
            return fallback_url
        
    def download_pdf(self) -> Optional[bytes]:
        """Descarga el PDF desde BYMA usando URL dinámica"""
        try:
            # Obtener URL del PDF más reciente si no la tenemos
            if not self.pdf_url:
                self.pdf_url = self.get_latest_pdf_url()
                
            if not self.pdf_url:
                print("❌ No se pudo obtener URL del PDF")
                return None
                
            print(f"📥 Descargando PDF desde: {self.pdf_url}")
            response = requests.get(self.pdf_url, verify=False)
            response.raise_for_status()
            
            # Guardar PDF localmente
            pdf_file = "byma_cedeares.pdf"
            with open(pdf_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ PDF guardado como: {pdf_file}")
            return response.content
            
        except Exception as e:
            print(f"❌ Error descargando PDF: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extrae texto del PDF usando diferentes librerías"""
        try:
            # Intentar con PyPDF2 primero
            try:
                import PyPDF2
                import io
                
                pdf_file = io.BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                print("✅ Texto extraído con PyPDF2")
                return text
                
            except ImportError:
                print("⚠️  PyPDF2 no está instalado, intentando con pdfplumber...")
                
            # Intentar con pdfplumber
            try:
                import pdfplumber
                import io
                
                pdf_file = io.BytesIO(pdf_content)
                with pdfplumber.open(pdf_file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                
                print("✅ Texto extraído con pdfplumber")
                return text
                
            except ImportError:
                print("⚠️  pdfplumber no está instalado, intentando con fitz...")
            
            # Intentar con PyMuPDF (fitz)
            try:
                import fitz
                import io
                
                pdf_file = io.BytesIO(pdf_content)
                doc = fitz.open(stream=pdf_file, filetype="pdf")
                
                text = ""
                for page in doc:
                    text += page.get_text()
                
                doc.close()
                print("✅ Texto extraído con PyMuPDF")
                return text
                
            except ImportError:
                print("❌ No se encontró ninguna librería PDF instalada")
                print("Instala una de estas: pip install PyPDF2 pdfplumber PyMuPDF")
                return ""
                
        except Exception as e:
            print(f"❌ Error extrayendo texto del PDF: {e}")
            return ""
    
    def parse_cedears_from_text(self, text: str) -> List[Dict]:
        """Parsea el texto extraído para encontrar CEDEARs con las 4 columnas"""
        cedeares = []
        
        # Guardar texto para debugging
        with open("byma_pdf_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("📝 Texto del PDF guardado en: byma_pdf_text.txt")
        
        # Dividir el texto en líneas
        lines = text.split('\n')
        
        # Buscar la tabla de CEDEARs
        table_started = False
        current_cedear = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Buscar el inicio de la tabla (puede contener "CEDEAR" o "Ratio")
            if not table_started and ("CEDEAR" in line.upper() or "RATIO" in line.upper()):
                table_started = True
                print(f"🔍 Inicio de tabla detectado: {line}")
                continue
            
            if table_started:
                # Obtener la línea siguiente para casos especiales como LONDON STOCK EXCHANGE
                next_line = None
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                
                # Intentar parsear línea como CEDEAR
                cedear_data = self.parse_cedear_line(line, next_line)
                if cedear_data:
                    cedeares.append(cedear_data)
        
        print(f"📊 Encontrados {len(cedeares)} CEDEARs en el PDF")
        return cedeares
    
    def parse_cedear_line(self, line: str, next_line: str = None) -> Optional[Dict]:
        """Parsea una línea individual para extraer datos de CEDEAR"""
        try:
            line = line.strip()
            
            # Detección especial para NU Holdings Ltd/Cayman Islands
            if "NU HOLDINGS LTD" in line.upper() or "CAYMAN ISLANDS" in line.upper():
                # Continuar con el parsing normal pero modificar el símbolo al final
                nu_debug_detected = True
            else:
                nu_debug_detected = False
            
            # Lista hardcodeada de mercados conocidos (ordenados de más largo a más corto)
            KNOWN_MARKETS = [
                "LONDON STOCK EXCHANGE", "NYSE ARCA", "NASDAQ GS", "NASDAQ GM", 
                "NYSE AMERICAN", "OTC US", "NASDAQ CM", "New York",
                "NYSE", "NASDAQ", "B3", "FRANKFURT", "OTC", "XETRA", "BOVESPA", "-"
            ]
            
            # CASO ESPECIAL: Detectar patrón "LONDON STOCK EXCHANGE" dividido en dos líneas
            if "LONDON STOCK" in line.upper():
                # Buscar símbolo pegado a LONDON (ej: HHPDLONDON)
                london_match = re.search(r'([A-Z]{1,5})LONDON STOCK', line.upper())
                if london_match:
                    symbol = london_match.group(1)
                    
                    # Buscar el ratio en la línea siguiente (que contiene "EXCHANGE")
                    ratio = None
                    if next_line:
                        ratio_match = re.search(r'(\d+:\d+)$', next_line)
                        if ratio_match:
                            ratio = ratio_match.group(1)
                    
                    if ratio:
                        # Extraer nombre de la empresa (todo antes del símbolo pegado a LONDON)
                        symbol_london_index = line.upper().find(f"{symbol}LONDON")
                        company_name = line[:symbol_london_index].strip()
                        
                        return {
                            'symbol': symbol,
                            'company_name': company_name,
                            'market': "LONDON STOCK EXCHANGE",
                            'ratio': ratio,
                            'source': 'BYMA_PDF'
                        }
            
            # CASO NORMAL: Buscar mercados completos en una línea
            # 1. Buscar el ratio al final (formato X:Y)
            ratio_match = re.search(r'(\d+:\d+)$', line)
            if not ratio_match:
                return None
            
            ratio = ratio_match.group(1)
            
            # 2. Obtener la parte de la línea ANTES del ratio
            line_before_ratio = line[:line.rfind(ratio)].strip()
            
            # 3. Buscar mercados ANTES del ratio (de más largo a más corto)
            found_market = None
            for market in KNOWN_MARKETS:
                # Buscar el mercado al final de la línea (antes del ratio)
                if line_before_ratio.upper().endswith(f" {market.upper()}"):
                    found_market = market
                    break
            
            if not found_market:
                return None
            
            # 4. Obtener la parte ANTES del mercado
            line_before_market = line_before_ratio[:line_before_ratio.upper().rfind(f" {found_market.upper()}")].strip()
            
            # 5. Buscar el símbolo: última palabra en mayúscula (1-5 chars) antes del mercado
            parts_before_market = line_before_market.split()
            symbol = None
            
            for i in range(len(parts_before_market) - 1, -1, -1):
                candidate = parts_before_market[i]
                # Verificar si es un símbolo válido (mayúsculas, 1-5 chars, alfanumérico)
                if (candidate.isupper() and 
                    1 <= len(candidate) <= 5 and 
                    candidate.isalnum() and
                    not candidate.isdigit()):
                    symbol = candidate
                    break
            
            if not symbol:
                return None
            
            # 6. Extraer nombre de la empresa (todo antes del símbolo)
            symbol_index = parts_before_market.index(symbol)
            company_name = ' '.join(parts_before_market[:symbol_index])
            
            # Modificar símbolo si se detectó NU Holdings
            if nu_debug_detected:
                symbol = 'NU'
                company_name = 'Nu Holdings Ltd.'
                found_market = 'NASDAQ'
            
            return {
                'symbol': symbol,
                'company_name': company_name,
                'market': found_market,
                'ratio': ratio,
                'source': 'BYMA_PDF'
            }
            
        except Exception as e:
            print(f"⚠️  Error parseando línea: {line} - {e}")
            return None
    
    def save_results(self, cedeares: List[Dict]):
        """Guarda los resultados en JSON"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(cedeares, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Datos guardados en: {self.output_file}")
            print(f"📊 Total de CEDEARs: {len(cedeares)}")
            
            # Mostrar algunos ejemplos
            print("\n📋 Ejemplos de CEDEARs del PDF:")
            for i, cedear in enumerate(cedeares[:5], 1):
                print(f"  {i}. {cedear['symbol']} - {cedear['company_name']} - Ratio: {cedear['ratio']}")
            
        except Exception as e:
            print(f"❌ Error guardando resultados: {e}")
    
    def run(self):
        """Ejecuta el proceso completo"""
        print("🚀 Procesador de PDF de BYMA - CEDEARs")
        print("=" * 50)
        
        # 1. Descargar PDF
        pdf_content = self.download_pdf()
        if not pdf_content:
            print("❌ No se pudo descargar el PDF")
            return
        
        # 2. Extraer texto
        text = self.extract_text_from_pdf(pdf_content)
        if not text:
            print("❌ No se pudo extraer texto del PDF")
            return
        
        # 3. Parsear CEDEARs
        cedeares = self.parse_cedears_from_text(text)
        if not cedeares:
            print("❌ No se encontraron CEDEARs en el PDF")
            print("💡 Revisá el archivo byma_pdf_text.txt para ver el contenido extraído")
            return
        
        # 4. Guardar resultados
        self.save_results(cedeares)
        
        print("\n✅ Proceso completado!")

def main():
    import sys
    
    processor = BYMAPDFProcessor()
    processor.run()

if __name__ == "__main__":
    main() 