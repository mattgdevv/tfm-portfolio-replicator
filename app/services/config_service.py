"""
Servicio para manejo de configuración y preferencias
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from app.config import settings


class ConfigService:
    """Servicio para configuración y preferencias del sistema"""
    
    def __init__(self, services):
        self.services = services
    
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
            result = await self.services.dollar_service.get_ccl_rate(source)
            
            if result:
                print(f"✅ Fuente funcionando correctamente:")
                print(f"   Cotización: ${result['rate']}")
                print(f"   Fuente: {result['source']}")
                print(f"   Última actualización: {result.get('last_update', 'N/A')}")
            else:
                print("❌ La fuente no está disponible")
                
        except Exception as e:
            print(f"❌ Error probando fuente: {e}")

    def load_local_preferences(self):
        """Carga preferencias locales (como fuente CCL preferida) desde un archivo simple."""
        try:
            prefs_file = Path('.prefs.json')
            if prefs_file.exists():
                data = json.load(open(prefs_file, 'r', encoding='utf-8'))
                preferred = data.get('PREFERRED_CCL_SOURCE')
                if preferred:
                    settings.PREFERRED_CCL_SOURCE = preferred
        except Exception:
            pass

    def save_local_preferences(self):
        """Guarda preferencias locales (como fuente CCL preferida) en un archivo simple."""
        try:
            # Merge con .prefs.json existente, no sobrescribir otras claves
            prefs_path = Path('.').joinpath('.prefs.json')
            existing = {}
            if prefs_path.exists():
                try:
                    existing = json.loads(prefs_path.read_text(encoding='utf-8'))
                except Exception:
                    existing = {}
            existing['PREFERRED_CCL_SOURCE'] = settings.PREFERRED_CCL_SOURCE
            prefs_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
    
    def read_prefs(self) -> dict:
        """Lee archivo de preferencias"""
        try:
            prefs_path = Path('.prefs.json')
            if prefs_path.exists():
                return json.loads(prefs_path.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}

    def write_prefs(self, data: dict) -> None:
        """Escribe archivo de preferencias"""
        try:
            prefs_path = Path('.prefs.json')
            prefs_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
