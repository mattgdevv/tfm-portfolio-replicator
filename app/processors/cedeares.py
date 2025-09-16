import json
import subprocess
from typing import Dict, Optional, Tuple
from pathlib import Path

class CEDEARProcessor:
    def __init__(self):
        self.cedeares_data = self._load_cedeares_data()
        self.cedeares_map = self._build_cedeares_map()
    
    def _load_cedeares_data(self) -> list:
        """Carga los datos de CEDEARs desde el archivo con ratios del PDF de BYMA."""
        # Usar el archivo del PDF como fuente principal
        data_path = Path(__file__).parent.parent.parent / "byma_cedeares_pdf.json"
        
        if not data_path.exists():
            print("[ERROR] No se encontraron datos de CEDEARs")
            print("🔄 Descargando datos de CEDEARs desde BYMA por primera vez...")
            if self._download_cedeares_data():
                # Intentar cargar nuevamente después de la descarga
                data_path = Path(__file__).parent.parent.parent / "byma_cedeares_pdf.json"
                if not data_path.exists():
                    print("[ERROR] Error: No se pudo descargar los datos de CEDEARs")
                    return []
            else:
                print("[ERROR] Error descargando datos de CEDEARs")
                return []
        
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _download_cedeares_data(self) -> bool:
        """
        Descarga los datos de CEDEARs desde BYMA ejecutando el script download_byma_pdf.py
        
        Returns:
            bool: True si la descarga fue exitosa, False si falló
        """
        try:
            # Ejecutar con PYTHONPATH para que encuentre el módulo app
            import os
            script_path = Path(__file__).parent.parent.parent / "scripts/download_byma_pdf.py"
            current_dir = str(Path(__file__).parent.parent.parent)
            env = os.environ.copy()
            env['PYTHONPATH'] = current_dir
            
            result = subprocess.run([
                "python", str(script_path)
            ], capture_output=True, text=True, cwd=current_dir, env=env)
            
            if result.returncode == 0:
                print("[SUCCESS] Datos de CEDEARs descargados exitosamente")
                return True
            else:
                print(f"[ERROR] Error en descarga: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error ejecutando descarga: {e}")
            return False
    
    def _build_cedeares_map(self) -> Dict[str, Dict]:
        """Construye un mapa de CEDEARs para búsqueda rápida."""
        cedeares_map = {}
        for cedear in self.cedeares_data:
            code = cedear.get("symbol", "").upper().strip()
            cedeares_map[code] = cedear
        return cedeares_map
    
    def is_cedear(self, symbol: str) -> bool:
        """Verifica si un símbolo es un CEDEAR. Si no lo encuentra, lanza un error claro."""
        normalized_symbol = symbol.upper().strip()
        if normalized_symbol not in self.cedeares_map:
            print(f"[ERROR] Símbolo '{symbol}' NO encontrado en byma_cedeares.json. No se puede convertir/arbitrar este activo.")
            return False
        return True
    
    def get_underlying_asset(self, cedear_symbol: str) -> Optional[Dict]:
        """Obtiene la información del activo subyacente de un CEDEAR. Si no lo encuentra, lanza un error claro."""
        normalized_symbol = cedear_symbol.upper().strip()
        cedear = self.cedeares_map.get(normalized_symbol)
        if not cedear:
            print(f"[ERROR] Símbolo '{cedear_symbol}' NO encontrado en datos de CEDEARs. No se puede obtener información de subyacente.")
            return None
        return cedear
    
    def parse_ratio(self, ratio_str: str) -> float:
        """Convierte un ratio en formato string a float. Para ratio '2:1', devuelve 2 (cantidad de CEDEARs por acción)"""
        try:
            if ":" in ratio_str:
                parts = ratio_str.split(":")
                return float(parts[0])
            else:
                return float(ratio_str)
        except (ValueError, ZeroDivisionError):
            return 1.0
    
    def convert_cedear_to_underlying(self, cedear_symbol: str, quantity: float) -> Tuple[str, float]:
        """
        Convierte una cantidad de CEDEARs a su equivalente en activo subyacente.
        Returns:
            Tuple[str, float]: (símbolo_subyacente, cantidad_convertida)
        """
        underlying_info = self.get_underlying_asset(cedear_symbol)
        if not underlying_info:
            raise ValueError(f"No se encontró información para el CEDEAR: {cedear_symbol}")
        
        # Obtener ratio del CEDEAR
        ratio = underlying_info.get("ratio", "1:1")
        conversion_ratio = self.parse_ratio(ratio)
        
        # Convertir cantidad: dividir por el ratio
        converted_quantity = quantity / conversion_ratio
        
        return underlying_info["symbol"], converted_quantity
    
    def get_all_cedeares(self) -> list:
        """Retorna la lista completa de CEDEARs disponibles."""
        return self.cedeares_data
    
    def reload_data(self):
        """Recarga los datos de CEDEARs desde el archivo (útil después de actualizaciones)"""
        print("🔄 Recargando datos de CEDEARs...")
        self.cedeares_data = self._load_cedeares_data()
        self.cedeares_map = self._build_cedeares_map()
        print(f"[SUCCESS] Datos recargados: {len(self.cedeares_data)} CEDEARs disponibles")
    
    def get_cedear_info(self, symbol: str) -> Optional[Dict]:
        """Obtiene información completa de un CEDEAR"""
        normalized_symbol = symbol.upper().strip()
        return self.cedeares_map.get(normalized_symbol)
    
    def show_cedeares_list(self):
        """Muestra la lista de CEDEARs disponibles"""
        print("\n🏦 CEDEARs disponibles:")
        cedeares = self.get_all_cedeares()
        
        # Mostrar primeros 10 como ejemplo
        for i, cedear in enumerate(cedeares[:10], 1):
            # Manejar diferentes estructuras de datos
            code = cedear.get('code') or cedear.get('symbol', 'N/A')
            company = cedear.get('company') or cedear.get('name', 'N/A')
            ratio = cedear.get('ratio', 'N/A')
            print(f"  {i}. {code} - {company} (Ratio: {ratio})")
        
        if len(cedeares) > 10:
            print(f"  ... y {len(cedeares) - 10} más")
        
        print(f"\n[DATA] Total de CEDEARs: {len(cedeares)}")

    def update_byma_cedeares(self):
        """Descarga y parsea el PDF de BYMA para obtener ratios de CEDEARs."""
        print("\n🔄 Descargando y procesando PDF de CEDEARs desde BYMA...")
        try:
            # Ejecutar con PYTHONPATH para que encuentre el módulo app
            import os
            current_dir = os.getcwd()
            env = os.environ.copy()
            env['PYTHONPATH'] = current_dir
            
            result = subprocess.run([
                "python", "scripts/download_byma_pdf.py"
            ], capture_output=True, text=True, cwd=".", env=env)
            
            if result.returncode == 0:
                print("[SUCCESS] PDF procesado exitosamente")
                # Recargar datos en el processor
                self.reload_data()
                if "CEDEARs" in result.stdout:
                    # Extraer número de CEDEARs del output
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if "Total de CEDEARs:" in line:
                            print(f"[SUCCESS] {line}")
                            break
                else:
                    print("[SUCCESS] Archivo byma_cedeares_pdf.json actualizado")
            else:
                print(f"[ERROR] Error procesando PDF: {result.stderr}")
                
        except Exception as e:
            print(f"[ERROR] Error ejecutando download_byma_pdf.py: {e}")
