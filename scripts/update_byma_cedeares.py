#!/usr/bin/env python3
"""
Descarga el JSON de CEDEARs de BYMA y lo guarda como byma_cedeares.json
"""

import requests
import json
from pathlib import Path
from datetime import datetime

# Configuración BYMA API
BYMA_URL = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/cedears"
OUTPUT_FILE = "byma_market_data.json"

def update_byma_cedeares():
    """Descarga datos de CEDEARs desde BYMA API"""
    
    payload = {
        "excludeZeroPxAndQty": True,
        "T1": True,
        "T0": False
    }
    headers = {"Content-Type": "application/json"}
    
    print("Descargando datos de CEDEARs desde BYMA...")
    
    try:
        response = requests.post(BYMA_URL, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Archivo guardado como {OUTPUT_FILE} ({len(data)} CEDEARs)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    update_byma_cedeares()