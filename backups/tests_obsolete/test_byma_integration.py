#!/usr/bin/env python3
"""
❌ DEPRECATED: Test roto por migración a DI estricto

Test de integración con BYMA para datos históricos
Prueba el análisis de variaciones usando datos BYMA

TODO: Migrar usando build_services() para DI estricto
"""

# ❌ ROTO POR MIGRACION DI: Este test usa imports legacy incompatibles
# 💡 Para migrar: usar build_services() en lugar de servicios globales
# 📍 Referencia histórica: muestra integración BYMA antes de DI estricto

import asyncio
import sys
import os

def main():
    """Test marcado como deprecated - requiere migración a DI"""
    raise RuntimeError("Test roto por migración DI - usar build_services() en lugar de servicios globales")

if __name__ == "__main__":
    main()

# ❌ CODIGO LEGACY COMENTADO:
# # Agregar el directorio raíz al path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# 
# from app.services.byma_historical import byma_historical_service  # ❌ YA NO EXISTE
# from app.services.variation_analyzer import variation_analyzer    # ❌ YA NO EXISTE

async def test_byma_integration():
    """Prueba la integración con BYMA para análisis de variaciones"""
    print("🧪 Probando integración BYMA para análisis de variaciones")
    print("=" * 60)
    
    # 1. Probar servicio BYMA básico
    print("1️⃣ Probando servicio BYMA básico...")
    
    # Verificar salud del servicio
    health = byma_historical_service.check_service_health()
    print(f"   Salud del servicio BYMA: {'✅ OK' if health else '❌ FAIL'}")
    
    if not health:
        print("⚠️  Servicio BYMA no disponible - saltando pruebas")
        return
    
    # 2. Probar precio individual de CEDEAR
    print("\n2️⃣ Probando precio individual de CEDEAR...")
    test_symbol = "TSLA"
    
    try:
        price = await byma_historical_service.get_cedear_price_eod(test_symbol)
        if price:
            print(f"   ✅ {test_symbol}: ${price:.2f} ARS")
        else:
            print(f"   ❌ No se pudo obtener precio para {test_symbol}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Probar CCL histórico
    print("\n3️⃣ Probando CCL histórico...")
    
    try:
        ccl_rate = await byma_historical_service.get_ccl_rate_historical()
        if ccl_rate:
            print(f"   ✅ CCL: ${ccl_rate:.2f} ARS/USD")
        else:
            print(f"   ❌ No se pudo obtener CCL histórico")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Probar múltiples CEDEARs
    print("\n4️⃣ Probando múltiples CEDEARs...")
    test_symbols = ["TSLA", "AAPL", "GOOGL", "MSFT"]
    
    try:
        prices = await byma_historical_service.get_multiple_cedear_prices_eod(test_symbols)
        
        for symbol, price in prices.items():
            if price:
                print(f"   ✅ {symbol}: ${price:.2f} ARS")
            else:
                print(f"   ❌ {symbol}: No disponible")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Probar análisis de variaciones completo
    print("\n5️⃣ Probando análisis de variaciones con BYMA...")
    
    try:
        # Usar solo símbolos que sabemos que existen
        analysis_symbols = ["TSLA", "AAPL"]
        
        print(f"   Analizando variaciones para: {analysis_symbols}")
        
        # Crear analizador en modo limitado (sin IOL)
        analyzer = variation_analyzer
        
        analyses = await analyzer.analyze_portfolio_variations(analysis_symbols)
        
        if analyses:
            print(f"   ✅ Análisis completado para {len(analyses)} símbolos")
            
            # Mostrar reporte formateado
            report = analyzer.format_variation_report(analyses)
            print("\n📊 REPORTE DE VARIACIONES:")
            print(report)
            
            # Mostrar análisis detallado del primero
            if len(analyses) > 0:
                detailed = analyzer.format_detailed_analysis(analyses[0])
                print("\n📈 ANÁLISIS DETALLADO:")
                print(detailed)
        else:
            print("   ❌ No se pudieron completar los análisis")
            
    except Exception as e:
        print(f"   ❌ Error en análisis de variaciones: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Probar diferentes escenarios
    print("\n6️⃣ Probando escenarios edge case...")
    
    # Símbolo inexistente
    try:
        fake_price = await byma_historical_service.get_cedear_price_eod("FAKESYMBOL")
        print(f"   Símbolo falso: {fake_price} (debería ser None)")
    except Exception as e:
        print(f"   ✅ Manejo correcto de símbolo falso: {type(e).__name__}")
    
    print("\n" + "=" * 60)
    print("🎯 Prueba de integración BYMA completada")
    print("💡 Los datos históricos BYMA están listos para el VariationAnalyzer")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_byma_integration())