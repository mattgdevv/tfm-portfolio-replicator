#!/usr/bin/env python3
"""
Script de prueba para CCL AL30 con autenticación IOL
Prueba el cálculo de CCL usando bonos AL30/AL30D desde IOL
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dollar_rate import dollar_service
from app.integrations.iol import IOLIntegration

async def test_ccl_al30_with_iol():
    """Prueba específica del CCL AL30 con autenticación IOL"""
    print("🧪 Probando CCL AL30 con autenticación IOL")
    print("=" * 50)
    
    # Simular autenticación IOL (sin credenciales reales)
    print("1️⃣ Simulando autenticación IOL...")
    
    # Crear una sesión mock para pruebas
    import requests
    mock_session = requests.Session()
    mock_session.headers.update({
        "Authorization": "Bearer mock_token",
        "Content-Type": "application/json"
    })
    
    # Establecer la sesión en el servicio de dólar
    dollar_service.set_iol_session(mock_session)
    
    print("✅ Sesión IOL simulada establecida")
    
    # Verificar estado de fuentes
    print("\n2️⃣ Estado de fuentes después de autenticación:")
    sources = dollar_service.get_available_sources()
    for source, available in sources.items():
        status = "✅ Disponible" if available else "❌ No disponible"
        print(f"   {source}: {status}")
    
    # Probar CCL AL30 (debería fallar por credenciales inválidas)
    print("\n3️⃣ Probando CCL AL30 (esperando error 401)...")
    try:
        result = await dollar_service._get_ccl_al30()
        if result:
            print("✅ CCL AL30 calculado exitosamente:")
            print(f"   Cotización: ${result['rate']:,.2f}")
            print(f"   AL30 (ARS): ${result['al30_price']:,.2f}")
            print(f"   AL30D (USD): ${result['al30d_price']:,.2f}")
        else:
            print("❌ No se pudo calcular CCL AL30")
    except Exception as e:
        if "401" in str(e):
            print("✅ Error 401 esperado - endpoints correctos, requiere autenticación válida")
        else:
            print(f"❌ Error inesperado: {e}")
    
    # Probar fallback automático
    print("\n4️⃣ Probando fallback automático (preferencia: ccl_al30)...")
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
            
    except Exception as e:
        print(f"❌ Error con fallback: {e}")
    
    # Limpiar sesión
    dollar_service.set_iol_session(None)
    print("\n5️⃣ Sesión IOL limpiada")
    
    print("\n" + "=" * 50)
    print("🎯 Prueba CCL AL30 con IOL completada")
    print("💡 Para usar CCL AL30 real, necesitas autenticarte con credenciales válidas de IOL")
    return True

if __name__ == "__main__":
    asyncio.run(test_ccl_al30_with_iol()) 