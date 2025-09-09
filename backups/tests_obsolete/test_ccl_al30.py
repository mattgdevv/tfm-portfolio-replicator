#!/usr/bin/env python3
"""
Script de prueba para CCL AL30
Prueba el cálculo de CCL usando bonos AL30/AL30D desde IOL
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dollar_rate import dollar_service

async def test_ccl_al30():
    """Prueba específica del CCL AL30"""
    print("🧪 Probando CCL AL30 (AL30/AL30D desde IOL)")
    print("=" * 50)
    
    try:
        # Probar CCL AL30 directamente
        print("1️⃣ Probando cálculo CCL AL30...")
        result = await dollar_service._get_ccl_al30()
        
        if result:
            print("✅ CCL AL30 calculado exitosamente:")
            print(f"   Cotización: ${result['rate']:,.2f}")
            print(f"   AL30 (ARS): ${result['al30_price']:,.2f}")
            print(f"   AL30D (USD): ${result['al30d_price']:,.2f}")
            print(f"   Método: {result['calculation_method']}")
            print(f"   Última actualización: {result['last_update']}")
        else:
            print("❌ No se pudo calcular CCL AL30")
            return False
            
    except Exception as e:
        print(f"❌ Error calculando CCL AL30: {e}")
        return False
    
    # Probar con fallback
    print("\n2️⃣ Probando CCL con fallback (preferencia: ccl_al30)...")
    try:
        result = await dollar_service.get_ccl_rate("ccl_al30")
        
        if result:
            print("✅ CCL con fallback exitoso:")
            print(f"   Cotización: ${result['rate']:,.2f}")
            print(f"   Fuente usada: {result['source']}")
            print(f"   Fuente preferida: {result['preferred_source']}")
            print(f"   Fallback usado: {result['fallback_used']}")
            print(f"   Fuentes intentadas: {result['attempted_sources']}")
        else:
            print("❌ No se pudo obtener CCL con fallback")
            return False
            
    except Exception as e:
        print(f"❌ Error con fallback: {e}")
        return False
    
    # Probar health check
    print("\n3️⃣ Probando health check de CCL AL30...")
    try:
        health = await dollar_service.check_source_health("ccl_al30")
        
        if health["status"]:
            print("✅ Health check CCL AL30 exitoso:")
            print(f"   Estado: {health['status']}")
            print(f"   Cotización: ${health['rate']:,.2f}")
            print(f"   Último check: {health['last_check']}")
        else:
            print(f"❌ Health check falló: {health.get('error', 'Error desconocido')}")
            
    except Exception as e:
        print(f"❌ Error en health check: {e}")
    
    # Probar health check de todas las fuentes
    print("\n4️⃣ Probando health check de todas las fuentes...")
    try:
        all_health = await dollar_service.check_all_sources_health()
        
        print("📊 Estado de todas las fuentes:")
        for source, status in all_health.items():
            if status["status"]:
                print(f"   ✅ {source}: ${status['rate']:,.2f}")
            else:
                print(f"   ❌ {source}: {status.get('error', 'Error')}")
                
    except Exception as e:
        print(f"❌ Error en health check general: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Prueba CCL AL30 completada")
    return True

if __name__ == "__main__":
    asyncio.run(test_ccl_al30()) 