#!/usr/bin/env python3
"""
Script de prueba para el servicio DollarRateService
"""

import asyncio
from app.services.dollar_rate import dollar_service

async def test_dollar_service():
    """Prueba el servicio de cotización del dólar"""
    
    print("🔍 Probando DollarRateService...")
    print("=" * 50)
    
    # Test 1: CCL desde dolarapi
    print("\n1️⃣ Probando CCL (dolarapi)...")
    ccl_result = await dollar_service.get_ccl_rate("dolarapi_ccl")
    
    if ccl_result:
        print(f"✅ CCL obtenido exitosamente:")
        print(f"   Cotización: ${ccl_result['rate']}")
        print(f"   Compra: ${ccl_result['buy']}")
        print(f"   Venta: ${ccl_result['sell']}")
        print(f"   Fuente: {ccl_result['source']}")
        print(f"   Última actualización: {ccl_result['last_update']}")
    else:
        print("❌ No se pudo obtener CCL")
    
    # Test 2: MEP
    print("\n2️⃣ Probando MEP...")
    mep_result = await dollar_service.get_mep_rate()
    
    if mep_result:
        print(f"✅ MEP obtenido exitosamente:")
        print(f"   Cotización: ${mep_result['rate']}")
        print(f"   Compra: ${mep_result['buy']}")
        print(f"   Venta: ${mep_result['sell']}")
        print(f"   Fuente: {mep_result['source']}")
    else:
        print("❌ No se pudo obtener MEP")
    
    # Test 3: Estado de fuentes
    print("\n3️⃣ Estado de fuentes:")
    sources = dollar_service.get_available_sources()
    for source, available in sources.items():
        status = "✅ Disponible" if available else "❌ No disponible"
        print(f"   {source}: {status}")
    
    print("\n" + "=" * 50)
    print("🎯 RESUMEN:")
    
    if ccl_result and mep_result:
        print(f"✅ Ambas cotizaciones obtenidas exitosamente")
        print(f"   CCL: ${ccl_result['rate']} | MEP: ${mep_result['rate']}")
        diff = abs(ccl_result['rate'] - mep_result['rate'])
        print(f"   Diferencia CCL-MEP: ${diff:.2f}")
    elif ccl_result or mep_result:
        print("⚠️  Solo una cotización disponible")
    else:
        print("❌ No se pudieron obtener cotizaciones")

if __name__ == "__main__":
    asyncio.run(test_dollar_service())