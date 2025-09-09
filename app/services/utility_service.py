"""
Servicio para utilidades y operaciones auxiliares
"""
import subprocess
from typing import List, Dict, Any

from app.processors.cedeares import CEDEARProcessor


class UtilityService:
    """Servicio para utilidades y operaciones auxiliares"""
    
    def __init__(self, cedear_processor: CEDEARProcessor):
        self.cedear_processor = cedear_processor
    
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
            result = subprocess.run([
                "python", "scripts/download_byma_pdf.py"
            ], capture_output=True, text=True, cwd=".")
            
            if result.returncode == 0:
                print("✅ PDF procesado exitosamente")
                # Recargar datos en el processor
                self.cedear_processor.reload_data()
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
