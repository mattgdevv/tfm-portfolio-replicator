#!/usr/bin/env python3
"""
Valida que todos los símbolos de un portfolio estén en byma_cedeares.json
"""
import json

BYMA_FILE = "byma_cedeares.json"

# Simulación: lista de símbolos del portfolio (puede reemplazarse por lectura de IOL)
portfolio_symbols = [
    "AAPL", "AMD", "BRKB", "TSLA", "PBR", "DNC5O", "IOLDOLD", "VIST"
]

def main():
    print(f"Leyendo {BYMA_FILE}...")
    with open(BYMA_FILE, "r", encoding="utf-8") as f:
        byma_data = json.load(f)
    byma_symbols = set(cedear.get("symbol", "") for cedear in byma_data)

    print("\nValidando símbolos del portfolio...")
    all_ok = True
    for symbol in portfolio_symbols:
        if symbol not in byma_symbols:
            print(f"❌ Símbolo '{symbol}' NO encontrado en {BYMA_FILE}")
            all_ok = False
        else:
            print(f"✅ Símbolo '{symbol}' encontrado en BYMA")
    if all_ok:
        print("\n✅ Todos los símbolos del portfolio están en BYMA.")
    else:
        print("\n⚠️  Hay símbolos que no están en BYMA. Revisá el archivo o tu portfolio.")

if __name__ == "__main__":
    main() 