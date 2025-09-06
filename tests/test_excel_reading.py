#!/usr/bin/env python3
"""
Script de prueba para la funcionalidad de lectura de Excel con Gemini
"""

import pandas as pd
from app.processors.file_processor import PortfolioProcessor

def test_excel_reading():
    print("🔍 Probando lectura de Excel con Gemini...")
    
    # Crear un DataFrame de ejemplo (simulando un Excel de portfolio)
    sample_data = {
        'Símbolo': ['AAPL', 'AMD', 'BRKB', 'NU'],
        'Cantidad': [45, 80, 205, 759],
        'Precio': [13900, 22425, 28550, 8215],
        'Moneda': ['ARS', 'ARS', 'ARS', 'ARS']
    }
    
    df = pd.DataFrame(sample_data)
    print(f"📊 DataFrame de ejemplo creado:")
    print(f"   Columnas: {list(df.columns)}")
    print(f"   Filas: {len(df)}")
    print(f"   Datos:\n{df}")
    
    # Probar el procesador
    try:
        processor = PortfolioProcessor()
        print("\n🤖 Procesando con Gemini...")
        
        # Usar asyncio para ejecutar la función async
        import asyncio
        portfolio = asyncio.run(processor.process_file(df, broker="Test"))
        
        print(f"✅ Portfolio procesado exitosamente:")
        print(f"   Posiciones: {len(portfolio.positions)}")
        print(f"   Broker: {portfolio.broker}")
        
        # Mostrar las posiciones
        print("\n📋 Posiciones procesadas:")
        for pos in portfolio.positions:
            print(f"   {pos.symbol}: {pos.quantity} @ ${pos.price} ({pos.currency})")
            if pos.is_cedear:
                print(f"     → CEDEAR: {pos.underlying_symbol} ({pos.underlying_quantity} acciones)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando Excel: {e}")
        return False

if __name__ == "__main__":
    test_excel_reading() 