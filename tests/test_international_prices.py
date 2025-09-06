#!/usr/bin/env python3
"""
Script de prueba para InternationalPriceService
Prueba Yahoo Finance y Finnhub con símbolos reales
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.international_prices import InternationalPriceService

async def test_international_prices():
    """Prueba el servicio de precios internacionales"""
    print("🧪 Probando InternationalPriceService")
    print("=" * 50)
    
    # Crear instancia directa (compatible con DI)
    international_price_service = InternationalPriceService()
    
    # Símbolos de prueba (los que tienes en tu portfolio)
    test_symbols = ["TSLA", "PLTR", "AMD", "AAPL"]
    
    # 1. Probar Finnhub (única fuente disponible)
    print("1️⃣ Probando Finnhub...")
    try:
        result = await international_price_service.get_stock_price("TSLA", "finnhub")
        
        if result:
            print("✅ Finnhub funcionando:")
            print(f"   Símbolo: {result['symbol']}")
            print(f"   Precio: ${result['price']:.2f} USD")
            print(f"   Fuente: {result['source']}")
            print(f"   Timestamp: {result['timestamp']}")
        else:
            print("❌ Finnhub falló")
            
    except Exception as e:
        print(f"❌ Error con Finnhub: {e}")
    
    # 2. Probar Finnhub (si está configurado)
    print("\n2️⃣ Probando Finnhub...")
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    if finnhub_key:
        try:
            result = await international_price_service.get_stock_price("TSLA", "finnhub")
            
            if result:
                print("✅ Finnhub funcionando:")
                print(f"   Símbolo: {result['symbol']}")
                print(f"   Precio: ${result['price']:.2f} USD")
                print(f"   Fuente: {result['source']}")
                print(f"   Máximo día: ${result.get('day_high', 'N/A')}")
                print(f"   Mínimo día: ${result.get('day_low', 'N/A')}")
            else:
                print("❌ Finnhub falló")
                
        except Exception as e:
            print(f"❌ Error con Finnhub: {e}")
    else:
        print("⚠️  FINNHUB_API_KEY no configurada - saltando prueba")
        print("💡 Para probar Finnhub:")
        print("   1. Regístrate en https://finnhub.io")
        print("   2. export FINNHUB_API_KEY=tu_api_key")
    
    # 3. Probar múltiples símbolos
    print("\n3️⃣ Probando múltiples símbolos...")
    try:
        prices = await international_price_service.get_multiple_prices(test_symbols[:3])  # Solo 3 para no agotar límites
        
        print("📊 Resultados múltiples:")
        for symbol, data in prices.items():
            if data:
                print(f"   ✅ {symbol}: ${data['price']:.2f} USD ({data['source']})")
            else:
                print(f"   ❌ {symbol}: Error obteniendo precio")
                
    except Exception as e:
        print(f"❌ Error con múltiples símbolos: {e}")
    
    # 4. Estado de fuentes
    print("\n4️⃣ Estado de fuentes:")
    sources = international_price_service.get_available_sources()
    for source, available in sources.items():
        status = "✅ Disponible" if available else "❌ No disponible"
        print(f"   {source}: {status}")
    
    print("\n" + "=" * 50)
    print("🎯 Prueba de precios internacionales completada")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_international_prices())