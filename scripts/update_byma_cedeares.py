#!/usr/bin/env python3
"""
Descarga el JSON de CEDEARs de BYMA y lo guarda como byma_cedeares.json
"""
import requests
import json
import urllib3

# Suprimir warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BYMA_URL = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/cedears"
OUTPUT_FILE = "byma_cedeares.json"

payload = {
    "excludeZeroPxAndQty": True,
    "T1": True,
    "T0": False,
    "Content-Type": "application/json, text/plain"
}
headers = {"Content-Type": "application/json"}

def main():
    print("Descargando datos de CEDEARs desde BYMA...")
    try:
        response = requests.post(BYMA_URL, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Archivo guardado como {OUTPUT_FILE} ({len(data)} CEDEARs)")
    except Exception as e:
        print(f"❌ Error al descargar o guardar datos: {e}")

if __name__ == "__main__":
    main() 